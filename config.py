# =========================
# VALBOT v20.1 Configuration
# =========================

BROKER = {
    "name": "Asianodds88",
    "username": "valsystem", # API username (confirmed)
    "password": "3d3f4bcc4f1f855fa5e5a6dcf159eb52", # MD5 of your Asianodds API password
    "use_md5": True, # keep True for Asianodds login
    "api_url": "https://webapi.asianodds88.com/AsianOddsService"
}

EXECUTION = {
    "mode": "live", # "live" or "dryrun" (you asked for Live to be allowed immediately)
    "stake_percent": 2.5, # used if fixed_stake_eur is None
    "fixed_stake_eur": 1.00, # safe default stake
    "ev_floor_percent": 1.0,
    "bet_limit_per_day": 1,
    "audit_mode": True
}

BANKROLL = {
    "starting_bankroll_eur": 100.45
}

PATHS = {
    "logs_dir": "logs",
    "bet_log": "logs/bet_log.csv",
    "execution_log": "logs/execution_log.csv",
    "balance_log": "logs/balance_log.csv",
    "match_results_log": "logs/match_results_log.csv",
    "echo_test_log": "logs/echo_test_log.csv",
    "preflight_report": "logs/preflight_report.txt",
    "edge_report": "logs/daily_edge_report.txt",
    "turnover_plan": "logs/turnover_plan.txt",
    "execution_qa_report": "logs/execution_qa_report.txt",
    "api_health_log": "logs/api_health.log"
}
