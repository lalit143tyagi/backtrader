import backtrader as bt
from ..core.broker_service import angel_broking_service
import logging

log = logging.getLogger(__name__)

class AngelStore(bt.stores.Store):
    """
    The Store is the direct interface to the broker's API.
    It handles the connection and provides methods to interact with the broker.
    """

    params = (
        ('api_key', None),
        ('secret_key', None),
        ('client_id', None),
        ('password', None),
        ('totp_secret', None),
    )

    def __init__(self):
        super(AngelStore, self).__init__()
        self.smart_connect = None
        self._orders = {} # A dictionary to keep track of live orders

    def start(self):
        """Called right before the backtesting/live trading starts."""
        super(AngelStore, self).start()
        try:
            # We use the singleton service to login and get the connection object
            self.smart_connect = angel_broking_service.login()
            log.info("AngelStore started and logged in successfully.")
        except Exception as e:
            log.error(f"Failed to start AngelStore: {e}")
            raise

    def stop(self):
        """Called right after the backtesting/live trading ends."""
        super(AngelStore, self).stop()
        try:
            angel_broking_service.logout()
            log.info("AngelStore stopped and logged out.")
        except Exception as e:
            log.error(f"Error stopping AngelStore: {e}")

    # --- Order Management Methods ---

    def place_order(self, order_params):
        """Places an order with the broker."""
        try:
            order_id = self.smart_connect.placeOrder(order_params)
            log.info(f"Order placed successfully. Order ID: {order_id}")
            return order_id
        except Exception as e:
            log.error(f"Failed to place order: {e}")
            return None

    def get_order_status(self, order_id):
        """Gets the status of a specific order."""
        # This will be implemented more fully later
        return self._orders.get(order_id, {})

    # --- Account Information Methods ---

    def get_cash(self):
        """Gets the available cash from the broker."""
        try:
            # The smartapi python sdk does not have a direct get_cash method
            # We need to get the user profile and extract funds info
            profile = self.smart_connect.getProfile(self.smart_connect.get_access_token())
            if profile and profile['status']:
                 # This path might need adjustment based on the actual API response
                return float(profile['data']['networth'])
            return 0.0
        except Exception as e:
            log.error(f"Failed to get cash balance: {e}")
            return 0.0

    def get_positions(self):
        """Gets the current positions from the broker."""
        try:
            positions = self.smart_connect.position()
            if positions and positions['status']:
                return positions['data']
            return []
        except Exception as e:
            log.error(f"Failed to get positions: {e}")
            return []
