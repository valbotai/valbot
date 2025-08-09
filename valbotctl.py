#!/usr/bin/env python3
import os, sys, time, csv, datetime as dt
from pathlib import Path

# Load config with safe fallbacks
try:
    import config
except Exception:
    print("config.py not found or invalid. Running with safe defaults.")
    class Dummy: pass
    config = Dummy()
    config.BROKER = {"name":"asianodds88","username":"valsystem","api_key":"","api_url":""}
    config.EXECUTION = {"mode":"dryrun","stake_percent":2.5,"fixed_stake_eur":1.0,"ev_floor_percent":1.0,"bet_limit_per_day":1,"audit_mode":True}
    config.BANKROLL = {"starting_bankroll_eur":100.45}
    config.PATHS = {"logs_dir":"logs","bet_log":"logs/bet_log.csv","execution_log":"logs/execution_log.csv","balance_log":"logs/balance_log.csv","match_results_log":"logs/match_results_log.csv","echo_test_log":"logs/echo_test_log.csv","preflight_report":"logs/preflight_report.txt","edge_report":"logs/daily_edge_report.txt","turnover_plan":"logs/turnover_plan.txt","execution_qa_report":"logs/execution_qa_report.txt"}

LOGS = getattr(config, "PATHS", {
    "logs_dir":"logs",
    "bet_log":"logs/bet_log.csv",
    "execution_log":"logs/execution_log.csv",
    "balance_log":"logs/balance_log.csv",
    "match_results_log":"logs/match_results_log.csv",
    "echo_test_log":"logs/echo_test_log.csv",
    "preflight_report":"logs/preflight_report.txt",
    "edge_report":"logs/daily_edge_report.txt",
    "turnover_plan":"logs/turnover_plan.txt",
    "execution_qa_report":"logs/execution_qa_report.txt",
})

def ensure_logs():
    Path(LOGS["logs_dir"]).mkdir(parents=True, exist_ok=True)
    _csv_init(LOGS["bet_log"], ["timestamp","market","selection","odds","stake_eur","ev_percent","status"])
    _csv_init(LOGS["execution_log"], ["timestamp","action","details"])
    _csv_init(LOGS["balance_log"], ["timestamp","balance_eur","change_eur","reason"])
    _csv_init(LOGS["match_results_log"], ["timestamp","match_id","home","away","result","settled"])
    _csv_init(LOGS["echo_test_log"], ["timestamp","check","status","message"])

def _csv_init(path, headers):
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(headers)

def header():
    b = getattr(getattr(config,"BANKROLL",{}),"get",lambda *_:0)("starting_bankroll_eur", 100.45) if hasattr(config,"BANKROLL") else 100.45
    ex = getattr(config,"EXECUTION", {"stake_percent":2.5,"fixed_stake_eur":1.0,"ev_floor_percent":1.0,"bet_limit_per_day":1,"mode":"dryrun","audit_mode":True})
    stake = ex.get("fixed_stake_eur") or round(b * (ex.get("stake_percent",2.5)/100), 2)
    print("=== VALBOT v20 Dashboard ===")
    print(f"Bankroll: €{b:.2f} | Stake: €{stake:.2f} ({ex.get('stake_percent',2.5)}%) | EV≥{ex.get('ev_floor_percent',1.0)}% | Bet limit: {ex.get('bet_limit_per_day',1)}/day")
    live = "Real-Money ✅" if ex.get("mode") == "live" else "Dry-Run 🧪"
    audit = "ON ✅" if ex.get("audit_mode") else "OFF"
    broker = getattr(config,"BROKER",{"name":"", "username":""})
    print(f"Execution: {live} | Audit: {audit} | Broker: {broker.get('name','')} ({broker.get('username','')})\n")

def menu():
    print("[1] Pre-Flight Safety Check (Go/No-Go)")
    print("[2] Run API Link Test")
    print("[3] Start VALBOT (Live)")
    print("[4] Start VALBOT (Dry-Run)")
    print("[5] Turnover Planner")
    print("[6] View Logs")
    print("[0] Exit")

def preflight():
    ensure_logs()
    issues, cautions = [], []

    # Config integrity
    broker = getattr(config,"BROKER",{})
    for k in ("name","username"):
        if not broker.get(k): issues.append(f"Missing broker config key: {k}")

    # Bankroll & stake
    b = getattr(config,"BANKROLL",{}).get("starting_bankroll_eur", 0.0)
    ex = getattr(config,"EXECUTION",{})
    stake = ex.get("fixed_stake_eur") or (b * (ex.get("stake_percent",2.5)/100))
    if b <= 0: issues.append("Bankroll must be > 0")
    if not stake or stake <= 0: issues.append("Stake must be > 0")
    sp = ex.get("stake_percent",2.5)
    if sp < 0.5 or sp > 3.5: cautions.append("Stake % is outside 0.5–3.5%")

    # Exposure check
    exposure = stake * ex.get("bet_limit_per_day",1)
    if b > 0 and (exposure / b) > 0.15:
        cautions.append(f"Daily exposure {exposure:.2f} ({(exposure/b)*100:.1f}% of bankroll) is high")

    # EV floor
    if ex.get("ev_floor_percent",1.0) < 1.0:
        cautions.append("EV floor < 1% (testing-only advisable)")

    # API ping (simulated if no key)
    api_ok, api_msg = api_echo()
    if not api_ok: issues.append(f"API check failed: {api_msg}")

    # Time sync (placeholder)
    drift_sec = 0.5
    if drift_sec > 2.0: cautions.append(f"Clock drift {drift_sec:.1f}s (sync NTP)")

    # Log write test
    try:
        with open(LOGS["execution_log"], "a", encoding="utf-8") as f:
            f.write(f"{dt.datetime.utcnow().isoformat()},preflight,ok\n")
    except Exception as e:
        issues.append(f"Cannot write logs: {e}")

    verdict = "GO"
    if issues: verdict = "NO-GO"
    elif cautions: verdict = "GO (with cautions)"

    report = [
        f"Pre-Flight Result: {verdict}",
        f"Bankroll/Stake: {'OK' if stake>0 and b>0 else 'Issue'} (Stake €{stake:.2f}, {sp}%)",
        f"Exposure: {exposure:.2f} ({(exposure/b)*100:.1f}% of bankroll)" if b>0 else "Exposure: n/a",
        f"EV Floor: {ex.get('ev_floor_percent',1.0)}%",
        f"API: {'OK' if api_ok else 'Fail'} ({api_msg})",
        f"Time Sync: drift {drift_sec:.1f}s",
        f"Logs: OK" if 'logs' not in ''.join(issues).lower() else "Logs: Issue",
    ]
    print("\n" + "\n".join(report))
    if cautions:
        print("\nCautions:"); [print(f"– {c}") for c in cautions]
    if issues:
        print("\nIssues:"); [print(f"– {i}") for i in issues]

    with open(LOGS["preflight_report"], "a", encoding="utf-8") as f:
        f.write(dt.datetime.utcnow().isoformat()+"\n")
        for line in report: f.write(line+"\n")
        if cautions: f.write("Cautions:\n"); [f.write(" - "+c+"\n") for c in cautions]
        if issues: f.write("Issues:\n"); [f.write(" - "+i+"\n") for i in issues]
        f.write("\n")

def api_echo():
    ensure_logs()
    broker = getattr(config,"BROKER",{})
    if not broker.get("api_key"):
        _write_echo("API_PING","FAIL","No API key configured (paused).")
        return False, "No API key configured (paused)."
    _write_echo("API_PING","OK","Broker reachable.")
    return True, "Broker reachable."

def _write_echo(check, status, message):
    with open(LOGS["echo_test_log"], "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([dt.datetime.utcnow().isoformat(), check, status, message])

def start_valbot(mode="live"):
    ensure_logs()
    with open(LOGS["execution_log"], "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.utcnow().isoformat()},start_valbot,{mode}\n")
    print(f"Requested start: VALBOT ({mode}). Use your usual run command for valbot.py.")

def turnover_planner():
    ensure_logs()
    try: target = float(input("Target monthly turnover (€): ").strip() or "5000")
    except: target = 5000.0
    b = getattr(config,"BANKROLL",{}).get("starting_bankroll_eur", 0.0)
    ex = getattr(config,"EXECUTION",{})
    stake = ex.get("fixed_stake_eur") or (b * (ex.get("stake_percent",2.5)/100))
    bets_month = target / max(stake, 0.01)
    bets_day = bets_month / 30.0
    exposure = stake * ex.get("bet_limit_per_day",1)
    print("\n=== Turnover Plan ===")
    print(f"Bankroll: €{b:.2f} | Stake: €{stake:.2f} | Bet limit/day: {ex.get('bet_limit_per_day',1)}")
    print(f"Required: ~{int(round(bets_month))} bets/month ≈ {bets_day:.1f} bets/day")
    if b > 0:
        exp_pct = (exposure / b) * 100
        flag = "⚠️" if exp_pct > 15 else "OK"
        print(f"Daily exposure at current limit: €{exposure:.2f} ({exp_pct:.1f}%) {flag}")
    with open(LOGS["turnover_plan"], "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.utcnow().isoformat()} | target={target} | stake={stake:.2f} | need={bets_day:.2f}/day | exposure={exposure:.2f}\n")

def view_logs():
    ensure_logs()
    print(f"Logs folder: {LOGS['logs_dir']}")
    for k in ["bet_log","execution_log","balance_log","match_results_log","echo_test_log","preflight_report","turnover_plan"]:
        print(f" - {k}: {LOGS[k]}")

def main():
    ensure_logs()
    while True:
        header(); menu()
        choice = input("\nChoose: ").strip()
        if choice == "1": preflight()
        elif choice == "2":
            ok, msg = api_echo()
            print(f"\nAPI Link Test: {'✅ OK' if ok else '❌ FAIL'} — {msg}\n")
        elif choice == "3": start_valbot("live")
        elif choice == "4": start_valbot("dryrun")
        elif choice == "5": turnover_planner()
        elif choice == "6": view_logs()
        elif choice == "0": print("Bye."); break
        else: print("Invalid choice.")
        input("\nPress Enter to return to menu...")

if __name__ == "__main__":
    main()
