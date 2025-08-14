#!/usr/bin/env python3
import os, sys, csv, signal, subprocess
from pathlib import Path
from datetime import datetime, timedelta
import pytz

import config
import markets_config as mc
from asianodds_api import AsianOddsSession, AOAuthError

LOGS = config.PATHS
TZ = pytz.timezone("Europe/London")

def ensure_dirs():
    Path(LOGS["logs_dir"]).mkdir(parents=True, exist_ok=True)
    Path(LOGS["exports_dir"]).mkdir(parents=True, exist_ok=True)
    Path(LOGS["archive_dir"]).mkdir(parents=True, exist_ok=True)
    _csv_init(LOGS["bet_log"], ["timestamp","market","mode","match","selection","odds_detect","odds_exec","ev_pct","stake_eur","result","pnl_eur","tx_id"])
    _csv_init(LOGS["attempt_log"], ["timestamp","market","mode","match","selection","odds_detect","ev_pct","decision","reason","latency_ms"])
    Path(LOGS["api_health_log"]).touch(exist_ok=True)

def _csv_init(path, headers):
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(headers)

def safe_input(prompt: str) -> str:
    try: return input(prompt)
    except (KeyboardInterrupt, EOFError):
        print("\n(back to menu)")
        return ""

def header(session):
    b = config.BANKROLL["starting_bankroll_eur"]
    ex = config.EXECUTION
    base_stake = ex.get("fixed_stake_eur") or round(b * (ex["stake_percent"]/100), 2)
    live = "Real-Money ✅" if ex["mode"] == "live" else "Demo 🧪"
    api = "🔴 Disconnected"
    if session and session.is_authenticated():
        age = session.health_probe().get("token_age_s")
        api = f"🟢 Connected (token {age or 0}s)"
    status = "RUNNING" if screen_running("valbot") else "STOPPED"
    print("=== VALBOT v25 Control Panel ===")
    print(f"Bankroll: €{b:.2f} | Base Stake: €{base_stake:.2f} ({ex['stake_percent']}%) | Global EV≥{ex['ev_floor_percent']}% | Bet limit: {ex['bet_limit_per_day']}/day")
    print(f"Execution: {live} | Broker: {config.BROKER['name']} ({config.BROKER['username']}) | API: {api} | Process: {status}")
    print("Hotkeys: [S]tart [P]Stop [R]estart [T]Restart schedule [Q]uit\n")

def menu():
    print("[1] Pre-Flight Safety Check")
    print("[2] API Health Probe")
    print("[3] Markets Panel (Live/Demo/Off, EV floors, multipliers)")
    print("[4] Bet Log Viewer (last 50, filter/search)")
    print("[5] Attempt/Skip Viewer")
    print("[6] Weekly Stats")
    print("[7] Near-Misses")
    print("[8] View Logs / Export")
    print("[9] Process Control (Start/Stop/Restart)")
    print("[0] Exit")

def screen_running(name="valbot") -> bool:
    try:
        out = subprocess.check_output(["bash","-lc", f"screen -ls | grep -E '\\.{name}\\b' || true"], text=True)
        return bool(out.strip())
    except Exception:
        return False

def process_control(choice=None):
    while True:
        print("\nProcess Control:")
        print(" [S] Start [P] Stop [R] Restart [B] Back")
        c = (choice or safe_input("> ")).strip().lower()
        if c == "s":
            subprocess.call(["bash","-lc","source venv/bin/activate && screen -dmS valbot python3 valbot.py"])
            print("Started VALBOT in screen session 'valbot'.")
        elif c == "p":
            subprocess.call(["bash","-lc","screen -X -S valbot quit || true"])
            print("Stopped VALBOT.")
        elif c == "r":
            subprocess.call(["bash","-lc","screen -X -S valbot quit || true"])
            subprocess.call(["bash","-lc","sleep 2 && source venv/bin/activate && screen -dmS valbot python3 valbot.py"])
            print("Restarted VALBOT.")
        elif c == "b": break
        else: print("Unknown option.")
        if choice: break

def preflight(session):
    ensure_dirs()
    issues, cautions = [], []
    b = config.BANKROLL.get("starting_bankroll_eur", 0.0)
    ex = config.EXECUTION
    base_stake = ex.get("fixed_stake_eur") or (b * (ex.get("stake_percent",2.5)/100))
    if b <= 0: issues.append("Bankroll must be > 0")
    if not base_stake or base_stake <= 0: issues.append("Base stake must be > 0")
    exposure = base_stake * ex.get("bet_limit_per_day", 1)
    if b > 0 and (exposure / b) > config.SAFETY.get("daily_exposure_cap", 0.15):
        cautions.append(f"Daily exposure {exposure:.2f} ({(exposure/b)*100:.1f}% of bankroll)")
    if not (session and session.is_authenticated()):
        issues.append("API not authenticated")
    verdict = "GO" if not issues else "NO-GO"
    print(f"\nPre-Flight Result: {verdict}")
    print(f"Bankroll/Stake: {'OK' if base_stake>0 and b>0 else 'Issue'} (Stake €{base_stake:.2f})")
    print(f"Exposure: {exposure:.2f} ({(exposure/b)*100:.1f}% of bankroll)" if b>0 else "Exposure: n/a")
    print(f"EV Floor: {ex.get('ev_floor_percent',1.0)}%")
    print(f"API: {'OK' if (session and session.is_authenticated()) else 'Fail'}")
    if cautions: print("\nCautions:"); [print(f" – {c}") for c in cautions]
    if issues: print("\nIssues:"); [print(f" – {i}") for i in issues]

def api_probe(session):
    info = session.health_probe()
    print(f"Authenticated: {info['authenticated']} | Token age: {info.get('token_age_s') or 0}s | Session URL: {info.get('session_url')}")

def markets_panel():
    print("\nMarkets Panel (Live/Demo/Off, EV floors, multipliers)")
    for m in mc.MARKET_MODES:
        mode = mc.MARKET_MODES[m]
        ev = mc.EV_FLOORS.get(m)
        mult = mc.STAKE_MULTIPLIERS.get(m, 1.0)
        print(f" - {m:8s} | Mode: {mode.upper():5s} | EV≥ {ev}% | Mult x{mult:.2f}")
    print("\nType: edit <MARKET> <live|demo|off> OR ev <MARKET> <value> OR mult <MARKET> <value> OR save OR back")
    while True:
        cmd = safe_input("> ").strip()
        if cmd in ("", "back"): break
        if cmd == "save":
            _save_markets()
            print("Saved.")
            break
        try:
            parts = cmd.split()
            if parts[0] == "edit" and len(parts)==3:
                m, val = parts[1], parts[2].lower()
                if m in mc.MARKET_MODES and val in ("live","demo","off"):
                    mc.MARKET_MODES[m] = val
                else: print("Invalid market or mode.")
            elif parts[0] == "ev" and len(parts)==3:
                m, val = parts[1], float(parts[2])
                if m in mc.EV_FLOORS: mc.EV_FLOORS[m] = val
            elif parts[0] == "mult" and len(parts)==3:
                m, val = parts[1], float(parts[2])
                if m in mc.STAKE_MULTIPLIERS: mc.STAKE_MULTIPLIERS[m] = val
            else:
                print("Unrecognised command.")
        except Exception as e:
            print(f"Error: {e}")

def _save_markets():
    text = (
f"""# AUTO-SAVED by valbotctl v25
MARKET_MODES = {repr(mc.MARKET_MODES)}
EV_FLOORS = {repr(mc.EV_FLOORS)}
STAKE_MULTIPLIERS = {repr(mc.STAKE_MULTIPLIERS)}
""")
    Path("markets_config.py").write_text(text, encoding="utf-8")

def _read_csv(path):
    if not Path(path).exists() or Path(path).stat().st_size == 0: return []
    rows=[]
    with open(path,"r",encoding="utf-8") as f:
        r=csv.reader(f)
        headers=next(r,[])
        for row in r: rows.append(dict(zip(headers,row)))
    return rows

def bet_log_viewer():
    rows=_read_csv(LOGS["bet_log"])
    if not rows: print("No placed bets yet."); return
    print("(Filter: /<text> search | minEV <v> | market <name> | mode <live|demo> | clear | back)")
    filt={"text":"","minEV":None,"market":None,"mode":None}
    while True:
        _print_bets(rows,filt,limit=50)
        cmd=safe_input("> ").strip()
        if cmd in ("","back"): break
        if cmd.startswith("/"): filt["text"]=cmd[1:].lower()
        elif cmd.startswith("minEV"): filt["minEV"]=float(cmd.split()[1])
        elif cmd.startswith("market"): filt["market"]=cmd.split()[1]
        elif cmd.startswith("mode"): filt["mode"]=cmd.split()[1]
        elif cmd=="clear": filt={"text":"","minEV":None,"market":None,"mode":None}
        elif cmd=="export":
            ts=datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            out=Path(LOGS["exports_dir"])/f"bets_{ts}.csv"
            _export(rows,filt,out); print(f"Exported → {out}")
        else: print("Unknown. Try: /, minEV, market, mode, export, back")

def _export(rows,filt,outpath):
    if not rows: return
    keys=list(rows[0].keys())
    with open(outpath,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=keys); w.writeheader()
        for r in _apply_filters(rows,filt): w.writerow(r)

def _apply_filters(rows,filt):
    for r in rows:
        if filt["text"] and filt["text"] not in (r.get("match","")+r.get("selection","")+r.get("market","")).lower(): continue
        if filt["market"] and filt["market"] != r.get("market"): continue
        if filt["mode"] and filt["mode"] != r.get("mode"): continue
        if filt["minEV"] is not None:
            try:
                if float(r.get("ev_pct","0")) < float(filt["minEV"]): continue
            except: pass
        yield r

def _print_bets(rows,filt,limit=50):
    print("\nLast bets (filtered):")
    count=0
    for r in list(_apply_filters(rows,filt))[-limit:]:
        print(f"{r.get('timestamp','')} | {r.get('market','')} [{r.get('mode','')}] | {r.get('match','')} | {r.get('selection','')} | EV {r.get('ev_pct','')}% | Stake €{r.get('stake_eur','')} | Odds {r.get('odds_detect','')}→{r.get('odds_exec','')}")
        count+=1
    if count==0: print("(no matching rows)")
    print("Commands: /text minEV X market NAME mode live|demo export back")

def attempt_viewer():
    rows=_read_csv(LOGS["attempt_log"])
    if not rows: print("No attempts logged yet."); return
    print("(Filter: /<text> search | reason <txt> | market <name> | mode <live|demo> | clear | back)")
    filt={"text":"","reason":"","market":None,"mode":None}
    while True:
        _print_attempts(rows,filt,limit=50)
        cmd=safe_input("> ").strip()
        if cmd in ("","back"): break
        if cmd.startswith("/"): filt["text"]=cmd[1:].lower()
        elif cmd.startswith("reason"): filt["reason"]=cmd.split(maxsplit=1)[1].lower()
        elif cmd.startswith("market"): filt["market"]=cmd.split()[1]
        elif cmd.startswith("mode"): filt["mode"]=cmd.split()[1]
        elif cmd=="clear": filt={"text":"","reason":"","market":None,"mode":None}
        elif cmd=="export":
            ts=datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            out=Path(LOGS["exports_dir"])/f"attempts_{ts}.csv"
            _export(rows,{"text":filt["text"],"minEV":None,"market":filt["market"],"mode":filt["mode"]},out); print(f"Exported → {out}")
        else: print("Unknown.")

def _print_attempts(rows,filt,limit=50):
    print("\nLast attempts (filtered):")
    count=0
    for r in list(_filter_attempts(rows,filt))[-limit:]:
        print(f"{r.get('timestamp','')} | {r.get('market','')} [{r.get('mode','')}] | {r.get('match','')} | {r.get('selection','')} | EV {r.get('ev_pct','')}% | {r.get('decision','')} | {r.get('reason','')}")
        count+=1
    if count==0: print("(no matching rows)")
    print("Commands: /text reason TXT market NAME mode live|demo export back")

def _filter_attempts(rows,filt):
    for r in rows:
        if filt["text"] and filt["text"] not in (r.get("match","")+r.get("selection","")+r.get("market","")).lower(): continue
        if filt["market"] and filt["market"] != r.get("market"): continue
        if filt["mode"] and filt["mode"] != r.get("mode"): continue
        if filt["reason"] and filt["reason"] not in (r.get("reason","").lower()): continue
        yield r

def weekly_stats():
    rows=_read_csv(LOGS["bet_log"])
    if not rows: print("No placed bets yet."); return
    now = datetime.now(TZ)
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0,minute=0,second=0,microsecond=0)
    total = {"Live":0,"Demo":0}
    by_market = {}
    for r in rows:
        try:
            ts = datetime.fromisoformat(r["timestamp"])
        except:
            continue
        if ts.tzinfo is None: ts = TZ.localize(ts)
        if ts >= week_start:
            mode = r.get("mode","").capitalize()
            total[mode] = total.get(mode,0)+1
            m = r.get("market","")
            by_market[m] = by_market.get(m,0)+1
    print(f"This week (Mon–Sun): total {total.get('Live',0)+total.get('Demo',0)} | Live {total.get('Live',0)} | Demo {total.get('Demo',0)}")
    for m, n in by_market.items():
        print(f" - {m}: {n}")

def near_misses():
    p = Path(config.NEAR_MISS["log_path"])
    if not p.exists() or p.stat().st_size==0:
        print("No near-misses logged yet."); return
    rows=[]
    with open(p,"r",encoding="utf-8") as f:
        r=csv.reader(f); headers=next(r,[])
        for row in r: rows.append(dict(zip(headers,row)))
    print(f"Near-misses today: {len(rows)} (showing last 50)")
    for r in rows[-50:]:
        print(f"{r.get('timestamp','')} | {r.get('market','')} [{r.get('mode','')}] | {r.get('match','')} | reason={r.get('reason','')} | distance={r.get('distance','')}")

def view_logs():
    print("Log paths:")
    for k in ["bet_log","attempt_log","execution_log","api_health_log","weekly_summary"]:
        print(f" - {k}: {LOGS[k]}")
    print("Exports:", LOGS["exports_dir"])

def main():
    ensure_dirs()
    session = AsianOddsSession(
        base_url=config.BROKER["api_url"],
        username=config.BROKER["username"],
        password=config.BROKER["password"],
        is_md5=config.BROKER.get("use_md5", True),
        log_path=LOGS["api_health_log"]
    )
    try:
        session.login()
    except AOAuthError as e:
        print(f"API Login failed: {e}")

    signal.signal(signal.SIGINT, lambda *_: None)

    while True:
        header(session); menu()
        c = safe_input("Choose: ").strip().lower()
        if c == "1": preflight(session)
        elif c == "2": api_probe(session)
        elif c == "3": markets_panel()
        elif c == "4": bet_log_viewer()
        elif c == "5": attempt_viewer()
        elif c == "6": weekly_stats()
        elif c == "7": near_misses()
        elif c == "8": view_logs()
        elif c == "9": process_control()
        elif c == "s": process_control("s")
        elif c == "p": process_control("p")
        elif c == "r": process_control("r")
        elif c == "t": print("Set restart schedule in config.SCHEDULE (UI editor arrives in a minor update).")
        elif c in ("0","q","quit","exit"):
            print("Bye."); break
        else:
            print("Invalid choice.")
        safe_input("\nPress Enter to return to menu...")

if __name__ == "__main__":
    main()
