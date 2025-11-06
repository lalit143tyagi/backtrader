from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import backtrader as bt
from backtrader.stores import AngelStore
from backtrader.position import Position
from SmartWebsocketv2 import SmartWebSocketV2
import threading

class AngelBroker(bt.BrokerBase):
    """
    Angel Broking Broker with corrected, real-time order management.
    """
    params = (('producttype', 'INTRADAY'), ('validity', 'DAY'),)

    def __init__(self, **kwargs):
        super(AngelBroker, self).__init__(**kwargs)
        self.store = AngelStore(**kwargs)
        self.smartapi = self.store.get_session()

        self.positions = {}
        self._bt_order_map = {}  # Maps bt order.ref to broker order ID
        self._broker_order_map = {} # Maps broker order ID to bt order
        self.cash = self.startingcash
        self.value = self.startingcash
        self._order_ws = None

    def start(self):
        super(AngelBroker, self).start()
        self.cash = self.startingcash
        self.value = self.startingcash
        self._start_order_feed()

    def stop(self):
        if self._order_ws:
            self._order_ws.close_connection()
        super(AngelBroker, self).stop()

    def _start_order_feed(self):
        auth_token = self.smartapi.access_token
        api_key = self.store.api_key
        client_code = self.smartapi.client_code
        feed_token = self.store.get_feed_token()

        self._order_ws = SmartWebSocketV2(auth_token, api_key, client_code, feed_token)
        self._order_ws.on_order_update = self._handle_order_update

        t = threading.Thread(target=self._order_ws.connect)
        t.daemon = True
        t.start()

    def _handle_order_update(self, data):
        broker_id = data.get('orderid')
        order = self._broker_order_map.get(broker_id)
        if not order:
            return

        status = data.get('status')
        if status == 'complete':
            fill_price = float(data['averageprice'])
            fill_size = int(data['filledshares'])
            self._update_fill(order, fill_size, fill_price)

        elif status in ['rejected', 'cancelled']:
            if status == 'rejected':
                order.reject(self)
            else:
                order.cancel()
            self.notify(order)
            self._cleanup_order(order.ref, broker_id)

    def _update_fill(self, order, size, price):
        pos = self.positions.get(order.data, Position(0, 0.0))
        if order.isbuy():
            pos.size += size
            pos.price = (pos.price * (pos.size - size) + price * size) / pos.size if pos.size else price
            self.cash -= size * price
        else:
            pos.size -= size
            self.cash += size * price

        self.positions[order.data] = pos

        order.execute(dt=self.env.get_dt(), size=size, price=price)
        self.notify(order)

        if order.status == bt.Order.Completed:
            self._cleanup_order(order.ref, self._bt_order_map.get(order.ref))

    def _cleanup_order(self, bt_ref, broker_id):
        if bt_ref in self._bt_order_map:
            del self._bt_order_map[bt_ref]
        if broker_id in self._broker_order_map:
            del self._broker_order_map[broker_id]

    def getcash(self): return self.cash
    def getvalue(self, datas=None):
        val = self.cash
        for data, pos in self.positions.items():
            if pos.size != 0: val += pos.size * data.close[0]
        self.value = val
        return val

    def buy(self, owner, data, size, price=None, plimit=None, exctype=None, **kwargs):
        order = bt.BuyOrder(owner, data, size, price, exctype=exctype, **kwargs)
        self._place_order(order)
        return order

    def sell(self, owner, data, size, price=None, plimit=None, exctype=None, **kwargs):
        order = bt.SellOrder(owner, data, size, price, exctype=exctype, **kwargs)
        self._place_order(order)
        return order

    def _place_order(self, order):
        params = self._prepare_order_params(order)
        if not params:
            order.reject(self); self.notify(order); return

        try:
            order_response = self.smartapi.placeOrder(params)
            if order_response['status']:
                broker_id = order_response['data']['orderid']
                order.submit(self)
                self.notify(order)
                self._bt_order_map[order.ref] = broker_id
                self._broker_order_map[broker_id] = order
            else:
                order.reject(self); self.notify(order)
        except Exception as e:
            order.reject(self); self.notify(order)

    def cancel(self, order):
        broker_id = self._bt_order_map.get(order.ref)
        if not broker_id:
            return

        try:
            cancel_response = self.smartapi.cancelOrder(broker_id, 'NORMAL')
            if not cancel_response['status']:
                print(f"Failed to cancel order: {cancel_response['message']}")
        except Exception as e:
            print(f"Exception canceling order: {e}")

    def _prepare_order_params(self, order):
        params = {"variety": "NORMAL", "tradingsymbol": order.data._name, "symboltoken": order.data.p.dataname, "transactiontype": "BUY" if order.isbuy() else "SELL", "exchange": "NSE", "ordertype": "", "producttype": self.p.producttype, "duration": self.p.validity, "quantity": order.created.size}
        if order.exectype == order.Market: params["ordertype"] = "MARKET"
        elif order.exectype == order.Limit: params["ordertype"] = "LIMIT"; params["price"] = order.created.price
        else: return None
        return params
