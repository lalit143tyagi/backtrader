import backtrader as bt
from backtrader_angel.ABstore import AngelStore
from database.manager import get_instrument_token
import logging

class AngelBroker(bt.brokers.BackBroker):
    """
    Backtrader Broker for Angel Broking.

    This class is the core component for executing trades. It translates
    Backtrader order objects into the format required by the Angel Broking API,
    submits them, and handles the order lifecycle notifications.
    """

    def __init__(self, **kwargs):
        super(AngelBroker, self).__init__(**kwargs)
        self.store = AngelStore()
        self.orders = {} # To keep track of live orders

    def _get_exchange_segment(self, symbol):
        """Helper to determine the exchange from the symbol."""
        # This logic should be aligned with your instrument data
        if 'NFO' in symbol.upper(): # A simple heuristic
            return 'NFO'
        return 'NSE'

    def _submit(self, order):
        """
        The core method for submitting an order. This is called by Backtrader
        when a `buy()` or `sell()` command is issued in the strategy.
        """
        session = self.store.get_session()
        symbol = order.data.p.dataname
        exchange = self._get_exchange_segment(symbol)

        token = get_instrument_token(symbol, exch_seg=exchange)

        if not token:
            logging.error(f"Could not submit order for {symbol}: Token not found.")
            # Reject the order
            self.notify(bt.Order(status=bt.Order.Rejected, ref=order.ref))
            return None

        # --- Map Backtrader Order Type to API Format ---
        order_type_map = {
            bt.Order.Market: "MARKET",
            bt.Order.Limit: "LIMIT",
            bt.Order.Stop: "STOPLOSS_LIMIT", # Angel requires a limit price for stop orders
            bt.Order.StopLimit: "STOPLOSS_LIMIT",
        }
        api_order_type = order_type_map.get(order.ordtype)
        if not api_order_type:
            logging.error(f"Unsupported order type: {order.ordtype}")
            self.notify(bt.Order(status=bt.Order.Rejected, ref=order.ref))
            return None

        # --- Build the Order Payload ---
        payload = {
            "tradingsymbol": symbol,
            "symboltoken": token,
            "transactiontype": "BUY" if order.isbuy() else "SELL",
            "exchange": exchange,
            "ordertype": api_order_type,
            "quantity": order.size,
            # --- Default Parameters (as requested) ---
            "producttype": "DELIVERY",
            "duration": "DAY",
            "variety": "NORMAL",
        }

        # Add price details for Limit and Stop-Loss orders
        if api_order_type in ["LIMIT", "STOPLOSS_LIMIT"]:
            if not order.price:
                logging.error("Limit/Stop-Loss order must have a price.")
                self.notify(bt.Order(status=bt.Order.Rejected, ref=order.ref))
                return None
            payload["price"] = order.price
            # For a stop-loss order, Angel's API requires a trigger price
            if api_order_type == "STOPLOSS_LIMIT":
                 # In Backtrader, the `price` of a Stop order is the trigger price
                payload["triggerprice"] = order.price

        # --- Place the Order ---
        try:
            print(f"Submitting Order to Angel Broking: {payload}")
            order_response = session.place_order(payload)

            if order_response and order_response.get('status'):
                order_id = order_response.get('data', {}).get('orderid')
                if order_id:
                    print(f"Order submitted successfully. Angel Broking Order ID: {order_id}")
                    self.orders[order.ref] = order_id # Track the order
                    # Notify Backtrader that the order is submitted
                    self.notify(bt.Order(status=bt.Order.Submitted, ref=order.ref))
                    return order
                else:
                    raise KeyError("'orderid' not found in successful response.")
            else:
                message = order_response.get('message', 'Order submission failed.')
                logging.error(f"Order submission failed for {symbol}: {message}")
                self.notify(bt.Order(status=bt.Order.Rejected, ref=order.ref))
                return None

        except Exception as e:
            logging.error(f"An error occurred during order submission for {symbol}: {e}", exc_info=True)
            self.notify(bt.Order(status=bt.Order.Rejected, ref=order.ref))
            return None

    def _notify(self, order):
        """
        Handles order notifications. In a real-time system, you would update
        this method to be driven by a WebSocket feed from the broker to get
        live updates on order status (e.g., partial fills, execution).

        For now, it provides simple console feedback based on the status
        passed to it.
        """
        status_map = {
            bt.Order.Submitted: "Submitted",
            bt.Order.Accepted: "Accepted",
            bt.Order.Executed: "Executed",
            bt.Order.Canceled: "Canceled",
            bt.Order.Rejected: "Rejected",
            bt.Order.Margin: "Margin",
        }
        status_str = status_map.get(order.status, "Unknown")

        print(f"--- ORDER NOTIFICATION ---")
        print(f"  - Ref: {order.ref}")
        print(f"  - Status: {status_str}")
        if order.status == bt.Order.Executed:
            print(f"  - Executed at Price: {order.executed.price}")
            print(f"  - Executed Size: {order.executed.size}")
        print(f"--------------------------")

    # --- Other broker methods (optional to implement) ---
    def _cancel(self, order):
        """Cancels an order."""
        order_id = self.orders.get(order.ref)
        if order_id:
            try:
                session = self.store.get_session()
                # Assuming 'NORMAL' variety for cancellation
                cancel_response = session.cancel_order(order_id, "NORMAL")
                if cancel_response and cancel_response.get('status'):
                    print(f"Cancel request for order {order_id} sent successfully.")
                    self.notify(bt.Order(status=bt.Order.Canceled, ref=order.ref))
                else:
                    logging.error(f"Failed to cancel order {order_id}: {cancel_response.get('message')}")
            except Exception as e:
                logging.error(f"Error canceling order {order_id}: {e}")
        else:
            logging.warning(f"Cannot cancel order {order.ref}: Not found in tracked orders.")

    def get_cash(self):
        """Returns the current cash balance."""
        # In a live system, you would fetch this from the API
        # E.g., self.store.get_session().get_funds()['data']['availablecash']
        return self.cash

    def get_value(self, datas=None):
        """Returns the current portfolio value."""
        # In a live system, this would be a combination of cash and holdings value
        return self.value
