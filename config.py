# =========================
# VALBOT v25 Configuration
# =========================

# --- Broker / API (preloaded) ---
BROKER = {
    "name": "Asianodds88",
    "username": "valsystem",
    "password": "3d3f4bcc4f1f855fa5e5a6dcf159eb52", # MD5 of your Asianodds API password
    "use_md5": True,
    "api_url": "https://webapi.asianodds88.com/AsianOddsService"
}

# --- Execution (global defaults; per-market overrides live in markets_config.py) ---
EXECUTION = {
    "mode": "live", # "live" or "demo"
    "stake_percent": 2.5, # used if fixed_stake_eur is None
    "fixed_stake_eur": 1.00, # keep €1 while testing
    "ev_floor_percent": 5.0, # global fallback EV floor; per-market values override this
    "bet_limit_per_day": 20, # v25 supports higher volume
    "audit_mode": True
}

# --- Safety caps ---
SAFETY = {
    "max_stake_multiplier": 1.50, # hard cap relative to base stake
    "daily_exposure_cap": 0.15 # 15% of bankroll per day (set 0 to disable)
}

# --- Bankroll ---
BANKROLL = {
    "starting_bankroll_eur": 100.45
}

# --- Near-Miss tracking (for almost-qualified bets) ---
NEAR_MISS = {
    "enabled": True,
    "ev_window_pct": 0.5, # within 0.5% of EV floor
    "odds_tolerance": 0.02, # within 0.02 of target odds
    "min_liquidity_pct": 0.85, # reached ≥85% of required stake
    "max_records_per_day": 200,
    "log_path": "logs/near_miss_log.csv",
    "alert_on_live": False
}

# --- Scheduled restarts (panel: hotkey T) ---
SCHEDULE = {
    "auto_restart": False, # enable/disable scheduler
    "daily_time_24h": "", # e.g. "03:00" or blank to disable
    "weekly_day": "", # e.g. "Sat"
    "weekly_time_24h": "03:00",
    "grace_seconds": 10
}

# --- Paths / Logs ---
PATHS = {
    "logs_dir": "logs",
    "bet_log": "logs/bet_log.csv", # placed bets
    "attempt_log": "logs/attempt_log.csv", # all attempts + skip reason
    "execution_log": "logs/execution_log.csv", # process + control panel actions
    "balance_log": "logs/balance_log.csv",
    "match_results_log": "logs/match_results_log.csv",
    "echo_test_log": "logs/echo_test_log.csv",
    "preflight_report": "logs/preflight_report.txt",
    "weekly_summary": "logs/weekly_summary.txt",
    "api_health_log": "logs/api_health.log",
    "exports_dir": "logs/exports",
    "archive_dir": "logs/archive"
}

VALBOT_VERSION = "v25"
