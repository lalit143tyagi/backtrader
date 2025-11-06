from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import backtrader as bt
import pandas as pd
from datetime import datetime, timedelta
from backtrader.stores import AngelStore
from SmartWebsocketv2 import SmartWebSocketV2
import threading
import time

class AngelData(bt.feeds.PandasData):
    """
    Angel Broking Data Feed with tick-to-bar aggregation for live data.
    """
    params = (
        ('fromdate', None),
        ('todate', None),
        ('timeframe', bt.TimeFrame.Minutes),
        ('compression', 1),
        ('live', False),
    )

    def __init__(self, **kwargs):
        super(AngelData, self).__init__(**kwargs)
        self.store = AngelStore()
        self.smartapi = self.store.get_session()
        self.sws = None
        self._current_bar = None
        self._last_tick_time = None

    def start(self):
        super(AngelData, self).start()
        if self.p.live:
            self._start_live_feed()
        else:
            df = self._load_historical_data()
            if df is not None:
                self.load_df(df)

    def stop(self):
        if self.p.live and self.sws:
            self.sws.close_connection()
        super(AngelData, self).stop()

    def _start_live_feed(self):
        auth_token = self.smartapi.access_token
        api_key = self.store.api_key
        client_code = self.smartapi.client_code
        feed_token = self.store.get_feed_token()

        self.sws = SmartWebSocketV2(auth_token, api_key, client_code, feed_token)

        def on_ticks(ws, ticks):
            self._aggregate_tick(ticks)

        def on_open(ws):
            token = f"nse_cm|{self.p.dataname}"
            self.sws.subscribe(token)

        self.sws.on_ticks = on_ticks
        self.sws.on_open = on_open

        t = threading.Thread(target=self.sws.connect)
        t.daemon = True
        t.start()

    def _aggregate_tick(self, tick):
        if not tick or 'last_traded_price' not in tick:
            return

        price = tick['last_traded_price']
        volume = tick.get('last_traded_quantity', 0)
        dt = datetime.fromtimestamp(tick['exchange_timestamp'] / 1000)

        if self._current_bar is None:
            self._start_new_bar(dt, price, volume)
            return

        bar_end_time = self._get_bar_end_time(self._current_bar['datetime'])

        if dt >= bar_end_time:
            self._push_bar()
            self._start_new_bar(dt, price, volume)
        else:
            self._current_bar['high'] = max(self._current_bar['high'], price)
            self._current_bar['low'] = min(self._current_bar['low'], price)
            self._current_bar['close'] = price
            self._current_bar['volume'] += volume

    def _start_new_bar(self, dt, price, volume):
        self._current_bar = {
            'datetime': dt,
            'open': price,
            'high': price,
            'low': price,
            'close': price,
            'volume': volume
        }

    def _get_bar_end_time(self, dt):
        if self.p.timeframe == bt.TimeFrame.Minutes:
            return dt.replace(second=0, microsecond=0) + timedelta(minutes=self.p.compression)
        # Add other timeframes as needed
        return dt

    def _push_bar(self):
        if self._current_bar:
            self.lines.datetime[0] = bt.date2num(self._current_bar['datetime'])
            self.lines.open[0] = self._current_bar['open']
            self.lines.high[0] = self._current_bar['high']
            self.lines.low[0] = self._current_bar['low']
            self.lines.close[0] = self._current_bar['close']
            self.lines.volume[0] = self._current_bar['volume']
            self.put_notification(self.LIVE)

    def _load_historical_data(self):
        # ... (rest of the historical data loading logic remains the same)
        if self.p.fromdate is None or self.p.todate is None:
            raise ValueError("fromdate and todate must be specified for historical data")

        params = {
            "exchange": "NSE",
            "symboltoken": self.p.dataname,
            "interval": "ONE_MINUTE",
            "fromdate": self.p.fromdate.strftime("%Y-%m-%d %H:%M"),
            "todate": self.p.todate.strftime("%Y-%m-%d %H:%M")
        }

        try:
            hist_data = self.smartapi.getCandleData(params)
            if not hist_data['status'] or hist_data['data'] is None:
                raise Exception(f"Error fetching historical data: {hist_data['message']}")

            df = pd.DataFrame(hist_data['data'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['datetime'] = pd.to_datetime(df['timestamp'])
            df.set_index('datetime', inplace=True)
            df.drop('timestamp', axis=1, inplace=True)
            return df

        except Exception as e:
            print(f"Error fetching data for {self.p.dataname}: {e}")
            return None

    def _load(self):
        return False
