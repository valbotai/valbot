#!/usr/bin/env python3
import time, csv
from pathlib import Path
from datetime import datetime, timezone

import config
import markets_config as mc
from asianodds_api import AsianOddsSession

LOGS = config.PATHS

def _csv_init(path, headers):
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(headers)

def _now_iso():
    return datetime.now(timezone.utc).isoformat()

def log_attempt(row):
    _csv_init(LOGS["attempt_log"], ["timestamp","market","mode","match","selection","odds_detect","ev_pct","decision","reason","latency_ms"])
    with open(LOGS["attempt_log"], "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(row)

def log_bet(row):
    _csv_init(LOGS["bet_log"], ["timestamp","market","mode","match","selection","odds_detect","odds_exec","ev_pct","stake_eur","result","pnl_eur","tx_id"])
    with open(LOGS["bet_log"], "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(row)

def log_near_miss(row):
    p = Path(config.NEAR_MISS["log_path"])
    p.parent.mkdir(parents=True, exist_ok=True)
    new = not p.exists() or p.stat().st_size == 0
    with open(p, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["timestamp","market","mode","match","selection","ev_floor","ev_seen","odds_seen","stake_needed","liquidity_seen","reason","distance"])
        w.writerow(row)

def base_stake():
    b = config.BANKROLL["starting_bankroll_eur"]
    ex = config.EXECUTION
    return ex.get("fixed_stake_eur") or round(b * (ex["stake_percent"]/100), 2)

def apply_multiplier(market, stake):
    mult = mc.STAKE_MULTIPLIERS.get(market, 1.0)
    capped = min(stake * mult, stake * config.SAFETY.get("max_stake_multiplier", 1.5))
    return round(capped, 2)

def effective_ev_floor(market):
    return mc.EV_FLOORS.get(market) or config.EXECUTION["ev_floor_percent"]

def main():
    # API session
    sess = AsianOddsSession(
        base_url=config.BROKER["api_url"],
        username=config.BROKER["username"],
        password=config.BROKER["password"],
        is_md5=config.BROKER.get("use_md5", True),
        log_path=LOGS["api_health_log"]
    )
    sess.login()

    print("VALBOT v25 started. Scanning for value bets... (Ctrl+C to stop)")

    # TODO: replace this demo loop with your real scanner that yields candidates
    while True:
        # ----- DEMO CANDIDATE (replace with real market feed) -----
        # As a placeholder, we simulate a candidate periodically so logs show structure.
        time.sleep(10)

        candidate = {
            "market": "1X2", # e.g., "1X2", "O/U_2.5", "BTTS", "DNB"
            "match": "Demo FC vs Test United",
            "selection": "Demo FC",
            "odds_detect": 2.10,
            "ev_pct": 5.2, # computed EV percent from your logic
            "latency_ms": 50
        }
        # ----------------------------------------------------------

        m = candidate["market"]
        mode = mc.MARKET_MODES.get(m, "off")
        if mode == "off":
            log_attempt([_now_iso(), m, mode, candidate["match"], candidate["selection"], candidate["odds_detect"], candidate["ev_pct"], "SKIPPED", "market OFF", candidate["latency_ms"]])
            continue

        ev_floor = effective_ev_floor(m)
        if candidate["ev_pct"] < ev_floor:
            # near-miss?
            if config.NEAR_MISS["enabled"] and (ev_floor - candidate["ev_pct"]) <= config.NEAR_MISS["ev_window_pct"]:
                log_near_miss([_now_iso(), m, mode, candidate["match"], candidate["selection"], ev_floor, candidate["ev_pct"], candidate["odds_detect"], "", "", "ev", round(ev_floor - candidate["ev_pct"], 3)])
            log_attempt([_now_iso(), m, mode, candidate["match"], candidate["selection"], candidate["odds_detect"], candidate["ev_pct"], "SKIPPED", "EV below floor", candidate["latency_ms"]])
            continue

        stake = apply_multiplier(m, base_stake())

        if mode == "demo" or config.EXECUTION["mode"] == "demo":
            # DEMO bet
            log_bet([_now_iso(), m, "demo", candidate["match"], candidate["selection"], candidate["odds_detect"], candidate["odds_detect"], candidate["ev_pct"], stake, "", "", ""])
            print(f"[DEMO] {candidate['match']} | {candidate['selection']} @ {candidate['odds_detect']} | EV {candidate['ev_pct']}% | Stake €{stake}")
            continue

        # LIVE bet (placeholder — integrate your real execution here)
        # Example: call your broker place_bet() and capture tx_id, exec odds, result
        tx_id = "" # fill from broker response
        odds_exec = candidate["odds_detect"] # replace with filled odds
        log_bet([_now_iso(), m, "live", candidate["match"], candidate["selection"], candidate["odds_detect"], odds_exec, candidate["ev_pct"], stake, "", "", tx_id])
        print(f"[LIVE] {candidate['match']} | {candidate['selection']} @ {odds_exec} | EV {candidate['ev_pct']}% | Stake €{stake}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
