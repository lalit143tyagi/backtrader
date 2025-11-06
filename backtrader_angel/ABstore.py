import backtrader as bt
from SmartApi.smartConnect import SmartConnect
import getpass
import os
import json
import time
import logging

class AngelStore:
    """
    Singleton Session Manager for Angel Broking.

    This class handles the authentication and session management with the
    Angel Broking SmartAPI. It is designed as a singleton to ensure that
    only one connection is active at any given time.

    Key Features:
    - Securely loads credentials from a config file or environment variables.
    - Establishes a connection to the API only when it is first needed (lazy connection).
    - Automatically refreshes the session token to maintain a live connection.
    - Provides a single, shared session object for all other components (Broker, Data feeds).
    """

    _singleton = None
    _config = {}

    def __new__(cls, *args, **kwargs):
        if not cls._singleton:
            cls._singleton = super(AngelStore, cls).__new__(cls)
        return cls._singleton

    def __init__(self, config_path='config.json', **kwargs):
        super(AngelStore, self).__init__(**kwargs)

        self.smart_api = None
        self._connected = False
        self._session_expiry_time = 0

        if not self._config:
            self._load_config(config_path)

        # Prompt for credentials that are not in the config
        self._get_credentials()

    def _load_config(self, config_path):
        """Loads configuration from a JSON file."""
        print(f"Loading configuration from {config_path}...")
        try:
            with open(config_path, 'r') as f:
                self._config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load or parse {config_path}. "
                  f"Will rely on environment variables and user prompts. Error: {e}")
            self._config = {}

    def _get_credentials(self):
        """Gets credentials from config, environment variables, or user prompt."""
        self.api_key = self._config.get("api_key") or os.environ.get("ANGEL_API_KEY")

        if not self.api_key:
            raise ValueError("API Key for Angel Broking is required. "
                             "Please provide it in your config file or set the "
                             "ANGEL_API_KEY environment variable.")

        self.client_id = self._config.get("client_id") or os.environ.get("ANGEL_CLIENT_ID")
        self.password = self._config.get("password")
        self.totp = self._config.get("totp")

        if not self.client_id:
            self.client_id = input("Enter your Angel Broking Client ID (PIN): ")
        if not self.password:
            self.password = getpass.getpass("Enter your Angel Broking Password: ")
        if not self.totp:
            self.totp = input("Enter your TOTP: ")


    def _connect(self):
        """
        Connects to the Angel Broking API and establishes a session.
        This method is called internally when the session is needed.
        """
        if self._connected:
            return

        print("Attempting to connect to Angel Broking...")
        self.smart_api = SmartConnect(self.api_key)

        try:
            data = self.smart_api.generate_session(self.client_id, self.password, self.totp)

            if data['status'] and data.get('data', {}).get('jwtToken'):
                self._connected = True
                # Set the session expiry time (e.g., 8 hours from now)
                self._session_expiry_time = time.time() + (8 * 60 * 60)
                print("Angel Broking session established successfully.")
            else:
                message = data.get('message', 'Unknown error.')
                logging.error(f"Login Failed: {message}")
                raise ConnectionError(f"Login Failed: {message}")

        except Exception as e:
            logging.error(f"An error occurred during connection: {e}")
            self._connected = False
            raise

    def _refresh_token(self):
        """Refreshes the session token if it is about to expire."""
        # Refresh if less than 30 minutes to expiry
        if self._connected and (self._session_expiry_time - time.time()) < (30 * 60):
            print("Session token is about to expire. Refreshing...")
            try:
                self.smart_api.renew_access_token()
                self._session_expiry_time = time.time() + (8 * 60 * 60)
                print("Token refreshed successfully.")
            except Exception as e:
                logging.error(f"Could not refresh token: {e}")
                # If refresh fails, force a re-login on the next call
                self._connected = False

    def get_session(self):
        """
        Provides the authenticated SmartConnect session object.

        This is the main method that other components should use. It handles
        the initial connection and token refreshing automatically.
        """
        if not self.is_connected():
            self._connect()

        self._refresh_token()

        return self.smart_api

    def is_connected(self):
        """Returns the current connection status."""
        return self._connected

    def stop(self):
        """
        Logs out from the Angel Broking session.
        """
        if self.is_connected():
            print("Logging out from Angel Broking...")
            try:
                session = self.get_session()
                session.terminate_session(self.client_id)
                print("Logged out successfully.")
            except Exception as e:
                logging.error(f"An error occurred during logout: {e}")
            finally:
                self._connected = False
                AngelStore._singleton = None # Reset singleton on stop

# Example usage (for testing purposes)
if __name__ == '__main__':
    try:
        # Create a dummy config file for the test
        with open('config.json', 'w') as f:
            json.dump({
                "api_key": "YOUR_API_KEY",
                # Add other non-sensitive details if you want
            }, f)

        # First instance
        store = AngelStore(config_path='config.json')
        session = store.get_session()

        if store.is_connected():
            print("Successfully retrieved session object.")
            user_profile = session.get_profile()
            print(f"Welcome, {user_profile['data']['name']}")

            # Second instance (should be the same object)
            store2 = AngelStore()
            print(f"Is store instance same as store2? {store is store2}")

            store.stop()

        os.remove('config.json')

    except (ValueError, ConnectionError, Exception) as e:
        print(f"Test failed: {e}")
        if os.path.exists('config.json'):
            os.remove('config.json')
