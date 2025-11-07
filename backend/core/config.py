import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # ANGEL BROKING API
    ANGEL_API_KEY = os.getenv("ANGEL_API_KEY")
    ANGEL_CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
    ANGEL_PASSWORD = os.getenv("ANGEL_PASSWORD")
    ANGEL_TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")

    # DATABASE
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
    DB_HOST = os.getenv("DB_HOST", "db")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "algotrader")
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    # BACKTESTING
    INSTRUMENT_NAME = "BANKNIFTY"
    TIMEFRAME = "FIVE_MINUTE"

settings = Settings()
