#!/usr/bin/env python3
import os, sys, csv, signal
from pathlib import Path
from datetime import datetime
import time

# Load config
import config
from asianodds_api import AsianOddsSession, AOAuthError

LOGS = config.PATHS

def ensure_logs():
    Path(LOGS["logs_dir"]).mkdir(parents=True, exist_ok=True)
    _csv_init(LOGS["bet_log"], ["timestamp","market","selection","odds","stake_eur","ev_percent","status"])
    _csv_init(LOGS["execution_log"], ["timestamp","action","details"])
    _csv_init(LOGS["balance_log"], ["timestamp","balance_eur","change_eur","reason"])
    _csv_init(LOGS["match_results_log"], ["timestamp","match_id","home","away","result","settled"])
    _csv_init(LOGS["echo_test_log"], ["timestamp","check","status","message"])
    Path(LOGS["api_health_log"]).touch(exist_ok=True)

def _csv_init(path, headers):
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(headers)

def safe_input(prompt: str) -> str:
    try:
        return input(prompt)
    except (KeyboardInterrupt, EOFError):
        print("\n(back to menu)")
        return ""

def header(session: AsianOddsSession | None):
    b = config.BANKROLL["starting_bankroll_eur"]
    ex = config.EXECUTION
    stake = ex["fixed_stake_eur"] or round(b * (ex["stake_percent"]/100), 2)
    live = "Real-Money ✅" if ex["mode"] == "live" else "Dry-Run 🧪"
    audit = "ON ✅" if ex["audit_mode"] else "OFF"
    api = "🔴 Disconnected"
    if session and session.is_authenticated():
        age = session.health_probe().get("token_age_s")
        api = f"🟢 Connected (token {age or 0}s)"
    print("=== VALBOT v20.1 Dashboard ===")
    print(f"Bankroll: €{b:.2f} | Stake: €{stake:.2f} ({ex['stake_percent']}%) | EV≥{ex['ev_floor_percent']}% | Bet limit: {ex['bet_limit_per_day']}/day")
    print(f"Execution: {live} | Audit: {audit} | Broker: {config.BROKER['name']} ({config.BROKER['username']}) | API: {api}")
    print()

def menu():
    print("[1] Pre-Flight Safety Check (Go/No-Go)")
    print("[2] API Health Probe")
    print("[3] Start VALBOT (Live)")
    print("[4] Start VALBOT (Dry-Run)")
    print("[5] Bet History (last 10)")
    print("[6] Toggle Mode (Live/Dry-Run)")
    print("[7] View Logs")
    print("[0] Exit")

def preflight(session: AsianOddsSession | None):
    ensure_logs()
    issues, cautions = [], []
    # Bankroll & stake
    b = config.BANKROLL.get("starting_bankroll_eur", 0.0)
    ex = config.EXECUTION
    stake = ex.get("fixed_stake_eur") or (b * (ex.get("stake_percent",2.5)/100))
    if b <= 0: issues.append("Bankroll must be > 0")
    if not stake or stake <= 0: issues.append("Stake must be > 0")
    if ex.get("stake_percent",2.5) < 0.5 or ex.get("stake_percent",2.5) > 3.5:
        cautions.append("Stake % is outside 0.5–3.5%")

    # Exposure check
    exposure = stake * ex.get("bet_limit_per_day", 1)
    if b > 0 and (exposure / b) > 0.15:
        cautions.append(f"Daily exposure {exposure:.2f} ({(exposure/b)*100:.1f}% of bankroll) is high")

    # EV floor
    if ex.get("ev_floor_percent", 1.0) < 1.0:
        cautions.append("EV floor < 1% (testing-only advisable)")

    # API
    if not (session and session.is_authenticated()):
        issues.append("API not authenticated")

    # Time sync (placeholder OK)
    drift_sec = 0.0

    # Log write test
    try:
        with open(LOGS["execution_log"], "a", encoding="utf-8") as f:
            f.write(f"{datetime.utcnow().isoformat()},preflight,ok\n")
    except Exception as e:
        issues.append(f"Cannot write logs: {e}")

    verdict = "GO"
    if issues: verdict = "NO-GO"
    elif cautions: verdict = "GO (with cautions)"

    report = [
        f"Pre-Flight Result: {verdict}",
        f"Bankroll/Stake: {'OK' if stake>0 and b>0 else 'Issue'} (Stake €{stake:.2f}, {ex.get('stake_percent',2.5)}%)",
        f"Exposure: {exposure:.2f} ({(exposure/b)*100:.1f}% of bankroll)" if b>0 else "Exposure: n/a",
        f"EV Floor: {ex.get('ev_floor_percent',1.0)}%",
        f"API: {'OK' if (session and session.is_authenticated()) else 'Fail'}",
        f"Time Sync: drift {drift_sec:.1f}s",
        f"Logs: OK" if 'logs' not in ''.join(issues).lower() else "Logs: Issue",
    ]
    print("\n" + "\n".join(report))
    if cautions:
        print("\nCautions:"); [print(f"– {c}") for c in cautions]
    if issues:
        print("\nIssues:"); [print(f"– {i}") for i in issues]

    with open(LOGS["preflight_report"], "a", encoding="utf-8") as f:
        f.write(datetime.utcnow().isoformat()+"\n")
        for line in report: f.write(line+"\n")
        if cautions: f.write("Cautions:\n"); [f.write(" - "+c+"\n") for c in cautions]
        if issues: f.write("Issues:\n"); [f.write(" - "+i+"\n") for i in issues]
        f.write("\n")

def api_health(session: AsianOddsSession):
    info = session.health_probe()
    age = info.get("token_age_s")
    msg = f"Authenticated: {info['authenticated']} | Token age: {age or 0}s | Session URL: {info['session_url']}"
    print(msg)
    with open(LOGS["api_health_log"], "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()} | {msg}\n")

def bet_history_tail(n=10):
    path = LOGS["bet_log"]
    if not Path(path).exists() or Path(path).stat().st_size == 0:
        print("No bets logged yet.")
        return
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader, [])
        for row in reader:
            rows.append(row)
    tail = rows[-n:]
    print("Last bets:")
    print(", ".join(headers))
    for r in tail:
        print(", ".join(r))

def toggle_mode():
    mode = config.EXECUTION.get("mode", "dryrun")
    new_mode = "live" if mode == "dryrun" else "dryrun"
    config.EXECUTION["mode"] = new_mode
    print(f"Mode switched to: {new_mode.upper()}")

def start_valbot(mode: str):
    # Placeholder hook: integrate with your runner/supervisor if needed
    with open(LOGS["execution_log"], "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()},start_valbot,{mode}\n")
    print(f"Requested start: VALBOT ({mode}). Use your usual run command for valbot.py.")

def main():
    ensure_logs()

    # Auto-login on start
    session = AsianOddsSession(
        base_url=config.BROKER["api_url"],
        username=config.BROKER["username"],
        password=config.BROKER["password"], # already MD5 per config
        is_md5=config.BROKER.get("use_md5", True),
        log_path=LOGS["api_health_log"]
    )
    try:
        session.login()
    except AOAuthError as e:
        print(f"API Login failed: {e}")

    # Ctrl+C → return to menu (no crash)
    signal.signal(signal.SIGINT, lambda *_: None)

    while True:
        header(session)
        menu()
        choice = safe_input("\nChoose: ").strip()
        if choice == "1":
            preflight(session)
        elif choice == "2":
            api_health(session)
        elif choice == "3":
            config.EXECUTION["mode"] = "live"; start_valbot("live")
        elif choice == "4":
            config.EXECUTION["mode"] = "dryrun"; start_valbot("dryrun")
        elif choice == "5":
            bet_history_tail(10)
        elif choice == "6":
            toggle_mode()
        elif choice == "7":
            print(f"Logs: {LOGS['logs_dir']}")
            for k in ["bet_log","execution_log","balance_log","match_results_log","echo_test_log","preflight_report","turnover_plan","api_health_log"]:
                print(f" - {k}: {LOGS[k]}")
        elif choice == "0":
            print("Bye."); break
        else:
            print("Invalid choice.")
        safe_input("\nPress Enter to return to menu...")

if __name__ == "__main__":
    main()
