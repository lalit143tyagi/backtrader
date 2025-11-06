import backtrader as bt
import pandas as pd
from sqlalchemy import create_engine
from ..core.config import settings

class PostgresDataFeed(bt.feeds.PandasData):
    """
    A Backtrader data feed that reads historical OHLCV data from a PostgreSQL database.
    """
    params = (
        ('instrument_token', None),
        ('fromdate', None),
        ('todate', None),
        ('interval', 'FIVE_MINUTE'),
    )

    def __init__(self):
        df = self._load_data()
        super(PostgresDataFeed, self).__init__(dataname=df)

    def _load_data(self):
        """Loads data from the database into a pandas DataFrame."""
        if not self.p.instrument_token:
            raise ValueError("instrument_token must be provided.")
        if not self.p.fromdate or not self.p.todate:
            raise ValueError("fromdate and todate must be provided.")

        engine = create_engine(settings.DATABASE_URL)

        query = f"""
            SELECT
                timestamp AS datetime,
                open,
                high,
                low,
                close,
                volume
            FROM historical_ohlcv
            WHERE
                instrument_token = '{self.p.instrument_token}' AND
                timestamp BETWEEN '{self.p.fromdate.isoformat()}' AND '{self.p.todate.isoformat()}' AND
                interval = '{self.p.interval}'
            ORDER BY timestamp ASC
        """

        df = pd.read_sql(query, engine, index_col='datetime', parse_dates=['datetime'])

        # Backtrader expects the datetime index to be timezone-naive
        df.index = df.index.tz_localize(None)

        return df
