from smartapi import SmartConnect
import pyotp
import logging
from .config import settings

log = logging.getLogger(__name__)

class AngelBrokingService:
    def __init__(self):
        self.smart_connect = SmartConnect(api_key=settings.ANGEL_API_KEY)
        self.session = None

    def _generate_totp(self):
        """Generates the Time-based One-Time Password."""
        try:
            totp = pyotp.TOTP(settings.ANGEL_TOTP_SECRET).now()
            log.info("Generated TOTP.")
            return totp
        except Exception as e:
            log.error(f"Error generating TOTP: {e}")
            raise

    def login(self):
        """Logs into the Angel Broking SmartAPI."""
        try:
            totp = self._generate_totp()
            data = self.smart_connect.generateSession(
                settings.ANGEL_CLIENT_ID,
                settings.ANGEL_PASSWORD,
                totp
            )

            if data['status'] and data['data']['jwtToken']:
                self.smart_connect.set_access_token(data['data']['jwtToken'])
                log.info("Login successful. Session generated.")
                return self.smart_connect
            else:
                log.error(f"Login failed: {data['message']}")
                raise ConnectionError(f"Angel Broking login failed: {data['message']}")

        except Exception as e:
            log.error(f"An exception occurred during login: {e}")
            raise

    def logout(self):
        """Logs out from the Angel Broking SmartAPI."""
        try:
            if self.session:
                response = self.smart_connect.terminateSession(settings.ANGEL_CLIENT_ID)
                log.info(f"Logout successful: {response}")
                self.session = None
        except Exception as e:
            log.error(f"Error during logout: {e}")


# Singleton instance
angel_broking_service = AngelBrokingService()
