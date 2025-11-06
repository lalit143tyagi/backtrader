import logging
import backtrader as bt

log = logging.getLogger(__name__)

class OMS:
    """
    The Order Management System (OMS) is responsible for all pre-trade checks
    and risk management rules.
    """

    def __init__(self, broker, db_session):
        self.broker = broker
        self.db_session = db_session
        self.active_orders = {} # A simple way to track recently executed orders to prevent duplicates

    def pre_trade_checks(self, order, data):
        """
        Runs all pre-trade checks. If any check fails, it raises an exception.
        """
        log.info(f"Running pre-trade checks for order {order.ref} on {data._name}...")

        # 1. Margin Check
        self.check_margin(order)

        # 2. Position Limit Check
        self.check_position_limits(order, data)

        # 3. Duplicate Order Check
        self.check_duplicate_order(order, data)

        log.info("All pre-trade checks passed.")
        return True

    def check_margin(self, order):
        """Checks if there is sufficient cash to place the order."""
        required_margin = order.size * order.price
        if self.broker.getcash() < required_margin:
            raise ValueError(f"Insufficient margin. Required: {required_margin}, Available: {self.broker.getcash()}")
        log.info("Margin check passed.")

    def check_position_limits(self, order, data):
        """
        Checks if the new order would violate position limits.
        For Phase 1, we assume a simple limit of 1 lot per instrument.
        """
        instrument = self.broker._get_instrument_details(data._name)
        if not instrument or not instrument.lotsize:
            log.warning(f"Could not find lot size for {data._name}, skipping position limit check.")
            return

        current_position = self.broker.getposition(data).size
        new_position = current_position + order.size

        # This is a simplified check. A real implementation would handle buy/sell logic more carefully.
        if abs(new_position) > instrument.lotsize:
             raise ValueError(f"Position limit exceeded. Current: {current_position}, New: {new_position}, Limit: {instrument.lotsize}")
        log.info("Position limit check passed.")

    def check_duplicate_order(self, order, data):
        """
        Prevents placing the same order multiple times in quick succession.
        This is a simple implementation based on the last signal.
        """
        # A simple key to identify the signal source
        signal_key = (data._name, order.isbuy())

        if self.active_orders.get(signal_key) == 'FILLED':
             raise ValueError(f"Duplicate order detected for {data._name}. An order has already been filled for this signal.")
        log.info("Duplicate order check passed.")

    def apply_slippage_control(self, order_params, data):
        """
        Modifies the order parameters to implement smart limit orders.
        The logic here is inspired by the openalgo project.
        """
        if order_params['ordertype'] == 'MARKET':
            # For market orders, we can convert them to limit orders to control slippage
            last_price = data.close[0]
            tick_size = self.broker._get_instrument_details(data._name).tick_size or 0.05

            if order_params['transactiontype'] == 'BUY':
                # Set limit price slightly higher to increase chance of fill
                limit_price = last_price + (tick_size * 5)
            else: # SELL
                # Set limit price slightly lower
                limit_price = last_price - (tick_size * 5)

            order_params['ordertype'] = 'LIMIT'
            order_params['price'] = round(limit_price / tick_size) * tick_size # Round to nearest tick size
            log.info(f"Converted MARKET order to smart LIMIT order at price: {order_params['price']}")

        return order_params
