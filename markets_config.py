# =========================
# VALBOT v25 Markets Config
# =========================

# Per-market mode: "live", "demo", or "off"
MARKET_MODES = {
    "1X2": "live",
    "O/U_2.5": "demo",
    "BTTS": "off",
    "DNB": "live",
}

# Per-market EV floors (percent). If None, use global EXECUTION.ev_floor_percent
EV_FLOORS = {
    "1X2": 5.0,
    "O/U_2.5": 5.0,
    "BTTS": 5.0,
    "DNB": 5.0,
}

# Per-market stake multipliers relative to base stake (1.0 = no change)
STAKE_MULTIPLIERS = {
    "1X2": 1.00,
    "O/U_2.5": 1.00,
    "BTTS": 1.00,
    "DNB": 1.00,
}
