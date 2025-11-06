import backtrader as bt
from .angelstore import AngelStore
from .oms import OMS
from ..database.models import Instrument
from ..database.connection import get_db
import logging

log = logging.getLogger(__name__)

class AngelBroker(bt.brokers.BrokerBase):
    """
    The Broker manages the portfolio state and translates Backtrader orders
    into API calls via the Store.
    """

    def __init__(self):
        super(AngelBroker, self).__init__()
        self.store = AngelStore()
        self.positions = {}
        self.db_session = next(get_db())
        self.oms = OMS(self, self.db_session)

    def start(self):
        super(AngelBroker, self).start()
        self.store.start()
        self.cash = self.store.get_cash()
        self.startingcash = self.cash
        # Sync initial positions from broker
        self._sync_positions()

    def stop(self):
        super(AngelBroker, self).stop()
        self.store.stop()
        self.db_session.close()

    def _sync_positions(self):
        """Fetches positions from the store and updates the internal state."""
        broker_positions = self.store.get_positions()
        for pos in broker_positions:
            # This logic will need to be made robust to map broker symbols to backtrader data feeds
            self.positions[pos['tradingsymbol']] = {'size': float(pos['netqty']), 'price': float(pos['netavgprice'])}
        log.info(f"Synced positions: {self.positions}")

    def getcash(self):
        return self.cash

    def getposition(self, data, clone=True):
        """Returns the position for a given data feed."""
        # A simple implementation; needs to be robust for multiple data feeds
        pos = self.positions.get(data._name, {'size': 0, 'price': 0.0})
        if clone:
            return pos.copy()
        return pos

    def _get_instrument_details(self, symbol):
        """Looks up instrument details from the local database."""
        return self.db_session.query(Instrument).filter(Instrument.symbol == symbol).first()

    def create_order_params(self, order, data, **kwargs):
        """Creates the dictionary of parameters for the SmartAPI placeOrder call."""
        instrument = self._get_instrument_details(data._name)
        if not instrument:
            raise ValueError(f"Instrument details not found for symbol: {data._name}")

        params = {
            "variety": "NORMAL", # NORMAL, STOPLOSS, AMO, ROBO
            "tradingsymbol": instrument.symbol,
            "symboltoken": instrument.token,
            "transactiontype": "BUY" if order.isbuy() else "SELL",
            "exchange": instrument.exch_seg,
            "ordertype": "", # MARKET, LIMIT, STOPLOSS_LIMIT, STOPLOSS_MARKET
            "producttype": "INTRADAY", # DELIVERY, CARRYFORWARD, MARGIN, INTRADAY
            "duration": "DAY",
            "quantity": int(order.size)
        }

        if order.exectype == bt.Order.Market:
            params["ordertype"] = "MARKET"
            params["price"] = 0
            params["triggerprice"] = 0

        elif order.exectype == bt.Order.Limit:
            params["ordertype"] = "LIMIT"
            params["price"] = order.price
            params["triggerprice"] = 0

        elif order.exectype == bt.Order.Stop:
             # This is a Stop-Market order in Angel's terminology
            params["ordertype"] = "STOPLOSS_MARKET"
            params["price"] = 0
            params["triggerprice"] = order.price

        elif order.exectype == bt.Order.StopLimit:
            params["ordertype"] = "STOPLOSS_LIMIT"
            params["price"] = order.price # The limit price
            params["triggerprice"] = order.auxvars.get('trigger_price', order.price) # The stop price

        # --- Advanced Order Types ---
        # Note: Backtrader does not have native Cover or Bracket orders.
        # We will identify them using auxiliary parameters (`exectype='oco'`).

        if order.exectype == bt.Order.OCO:
            # This will be our signal for a Bracket Order
            params["variety"] = "BO"
            params["squareoff"] = kwargs.get('squareoff', 0.0)
            params["stoploss"] = kwargs.get('stoploss', 0.0)
            params["trailingStoploss"] = kwargs.get('trailing_stoploss', 0.0)

        if kwargs.get('is_cover_order', False):
            params["variety"] = "CO"
            params["triggerprice"] = kwargs.get('trigger_price') # Stoploss trigger for the CO

        return params

    def buy(self, owner, data, size, price=None, plimit=None, exectype=None, **kwargs):
        order = self.orders.Buy(owner, data, size, price, plimit, exectype, **kwargs)
        self.execute_order(order, data, **kwargs)
        return order

    def sell(self, owner, data, size, price=None, plimit=None, exectype=None, **kwargs):
        order = self.orders.Sell(owner, data, size, price, plimit, exectype, **kwargs)
        self.execute_order(order, data, **kwargs)
        return order

    # --- Helper methods for advanced orders ---

    def cover_order(self, owner, data, size, price, stop_price, **kwargs):
        """Places a Cover Order."""
        kwargs['is_cover_order'] = True
        kwargs['trigger_price'] = stop_price

        if size > 0: # Buy CO
            return self.buy(owner, data, size, price=price, exectype=bt.Order.Limit, **kwargs)
        else: # Sell CO
            return self.sell(owner, data, size, price=price, exectype=bt.Order.Limit, **kwargs)

    def bracket_order(self, owner, data, size, price, squareoff, stoploss, **kwargs):
        """Places a Bracket Order."""
        kwargs['squareoff'] = squareoff
        kwargs['stoploss'] = stoploss

        # We use OCO as the signal for bracket orders as it's a one-cancels-other structure
        if size > 0: # Buy BO
            return self.buy(owner, data, size, price=price, exectype=bt.Order.OCO, **kwargs)
        else: # Sell BO
            return self.sell(owner, data, size, price=price, exectype=bt.Order.OCO, **kwargs)


    def execute_order(self, order, data, **kwargs):
        """
        Submits the order to the store after passing it through the OMS.
        """
        try:
            # 1. Run Pre-Trade Checks
            self.oms.pre_trade_checks(order, data)

            # 2. Create Order Parameters
            order_params = self.create_order_params(order, data, **kwargs)

            # 3. Apply Slippage Control
            order_params = self.oms.apply_slippage_control(order_params, data)

            # 4. Place the order via the store
            order_id = self.store.place_order(order_params)

            if order_id:
                order.submit(self)
                log.info(f"Order {order.ref} passed OMS and was submitted to broker. Order ID: {order_id}")
            else:
                order.reject(self)
                log.error(f"Order {order.ref} was rejected by the store.")

        except ValueError as ve:
            log.warning(f"Order {order.ref} rejected by OMS: {ve}")
            order.reject(self)
        except Exception as e:
            log.error(f"A critical error occurred while executing order {order.ref}: {e}")
            order.reject(self)
