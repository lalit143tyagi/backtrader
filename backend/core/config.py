import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Angel Broking API Credentials
    ANGEL_API_KEY: str = os.getenv("ANGEL_API_KEY", "YOUR_API_KEY")
    ANGEL_SECRET_KEY: str = os.getenv("ANGEL_SECRET_KEY", "YOUR_SECRET_KEY")
    ANGEL_CLIENT_ID: str = os.getenv("ANGEL_CLIENT_ID", "YOUR_CLIENT_ID")
    ANGEL_PASSWORD: str = os.getenv("ANGEL_PASSWORD", "YOUR_PASSWORD")
    ANGEL_TOTP_SECRET: str = os.getenv("ANGEL_TOTP_SECRET", "YOUR_TOTP_SECRET")

    # Database URL
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/trading")

settings = Settings()
