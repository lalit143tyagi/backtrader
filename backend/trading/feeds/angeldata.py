from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import backtrader as bt
from backend.trading.store.angelstore import get_store
from backend.core.config import settings
import pandas as pd
from datetime import datetime, timedelta

class AngelData(bt.feeds.PandasData):
    """
    Angel Broking Data Feed.
    """
    params = (
        ('fromdate', datetime.now() - timedelta(days=100)),
        ('todate', datetime.now()),
        ('timeframe', 'FIVE_MINUTE'),
    )

    def __init__(self):
        super(AngelData, self).__init__()
        self.get_data()

    def get_data(self):
        store = get_store()
        instrument_token = store.get_instrument_token(settings.INSTRUMENT_NAME)
        if not instrument_token:
            raise ValueError(f"Could not find instrument token for {settings.INSTRUMENT_NAME}")

        from_date = self.p.fromdate.strftime("%Y-%m-%d %H:%M")
        to_date = self.p.todate.strftime("%Y-%m-%d %H:%M")

        df = store.get_historical_data(
            instrument_token,
            from_date,
            to_date,
            self.p.timeframe
        )

        if not df.empty:
            self.p.dataname = df
