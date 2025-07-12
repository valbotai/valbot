# config.py

# User settings
BETFAIR_USERNAME = "your_username"
BETFAIR_PASSWORD = "your_password"
BETFAIR_APP_KEY = "your_app_key"
BETFAIR_CERT_FILE = "/path/to/client-2048.crt"
BETFAIR_KEY_FILE = "/path/to/client-2048.key"

# Strategy settings
BANKROLL_START = 400
STAKE_PERCENT = 0.025
DAILY_BET_CAP = 7
MIN_EV_THRESHOLD = 0.05
MAX_STAKE = 500

# Logging
CSV_LOG_PATH = "/opt/valbot/logs/"
LOGGING_ENABLED = True

# Execution controls
DEMO_MODE = True # Set to False to go live
EXCHANGE = "Betfair"
MARKET_TYPES = ["MATCH_ODDS"]

# Notifications
TELEGRAM_ENABLED = True
TELEGRAM_BOT_TOKEN = "your_bot_token"
TELEGRAM_CHAT_ID = "your_chat_id"
