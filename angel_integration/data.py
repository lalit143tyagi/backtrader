import backtrader as bt
import pandas as pd
from angel_integration.store import AngelStore
from database.manager import get_instrument_token
from datetime import datetime, timedelta
import logging

class AngelData(bt.feeds.PandasData):
    """
    Backtrader Data Feed for Angel Broking (for Backtesting).

    This class fetches historical price data from the Angel Broking API
    and provides it to the Backtrader engine as a pandas DataFrame.
    """

    params = (
        ('instrument_type', 'EQUITY'), # e.g., 'EQUITY', 'FUTIDX', 'OPTIDX'
    )

    def __init__(self, **kwargs):
        super(AngelData, self).__init__(**kwargs)
        self.store = AngelStore()

    def _get_timeframe_string(self):
        """Maps Backtrader timeframe to Angel Broking API string."""
        tf_map = {
            (bt.TimeFrame.Minutes, 1): "ONE_MINUTE",
            (bt.TimeFrame.Minutes, 3): "THREE_MINUTE",
            (bt.TimeFrame.Minutes, 5): "FIVE_MINUTE",
            (bt.TimeFrame.Minutes, 10): "TEN_MINUTE",
            (bt.TimeFrame.Minutes, 15): "FIFTEEN_MINUTE",
            (bt.TimeFrame.Minutes, 30): "THIRTY_MINUTE",
            (bt.TimeFrame.Minutes, 60): "ONE_HOUR",
            (bt.TimeFrame.Days, 1): "ONE_DAY",
        }
        interval = tf_map.get((self.p.timeframe, self.p.compression))
        if not interval:
            raise ValueError(f"Unsupported timeframe/compression combination: "
                             f"{self.p.timeframe} / {self.p.compression}")
        return interval

    def _get_exchange_segment(self, symbol):
        """Determines the exchange segment based on the instrument type."""
        if self.p.instrument_type in ['FUTIDX', 'OPTIDX', 'FUTSTK', 'OPTSTK']:
            return 'NFO'
        elif symbol.endswith('-EQ'):
            return 'NSE'
        return 'BSE'

    def _load(self):
        """
        Called by Backtrader to load data. It fetches data from the API,
        formats it into a pandas DataFrame, and assigns it to self.p.dataname.
        """
        if self.p.dataname is not None and not isinstance(self.p.dataname, str):
            # Data is already loaded
            return True

        if self.fromdate is None or self.todate is None:
            logging.warning("No date range specified for data loading.")
            return False

        symbol = self.p.dataname
        exchange = self._get_exchange_segment(symbol)

        print(f"Looking up token for symbol '{symbol}' in exchange '{exchange}'...")
        token = get_instrument_token(symbol, exch_seg=exchange)

        if not token:
            raise ValueError(f"Could not find a token for the symbol: {symbol} in exchange {exchange}")

        print(f"Found token: {token}. Fetching historical data...")

        historic_data_request = {
            "exchange": exchange,
            "symboltoken": token,
            "interval": self._get_timeframe_string(),
            "fromdate": self.fromdate.strftime("%Y-%m-%d 09:15"),
            "todate": self.todate.strftime("%Y-%m-%d 15:30")
        }

        try:
            session = self.store.get_session()
            response = session.get_candle_data(historic_data_request)

            if response and response.get('status') and response.get('data'):
                print(f"Successfully fetched {len(response['data'])} candles for {symbol}.")
                df = pd.DataFrame(response['data'])

                # --- Data Processing ---
                df.rename(columns={0: 'timestamp', 1: 'open', 2: 'high', 3: 'low', 4: 'close', 5: 'volume'}, inplace=True)
                df['datetime'] = pd.to_datetime(df['timestamp'])
                df.set_index('datetime', inplace=True)
                df.drop('timestamp', axis=1, inplace=True)
                df.sort_index(inplace=True)

                # Assign the DataFrame to self.p.dataname
                self.p.dataname = df
                return True
            else:
                message = response.get('message', 'No data returned.')
                logging.error(f"Could not fetch data for {symbol}: {message}")
                return False

        except Exception as e:
            logging.error(f"An error occurred while fetching data for {symbol}: {e}", exc_info=True)
            return False

# Example of how this might be used in a main script (for testing)
if __name__ == '__main__':
    cerebro = bt.Cerebro()

    # Add the store (it will prompt for credentials if needed)
    try:
        cerebro.addstore(AngelStore())

        # Define the data feed
        data = AngelData(
            dataname='SBIN-EQ',
            fromdate=datetime(2023, 1, 1),
            todate=datetime(2023, 1, 31),
            timeframe=bt.TimeFrame.Days,
            compression=1,
        )

        cerebro.adddata(data)

        # A simple strategy to print the closing prices
        class PrintClose(bt.Strategy):
            def next(self):
                print(f"{self.data.datetime.date(0)} - Close: {self.data.close[0]}")

        cerebro.addstrategy(PrintClose)

        print("Running backtest...")
        cerebro.run()
        print("Backtest finished.")

    except (ValueError, ConnectionError) as e:
        print(f"Test failed: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during the test: {e}")
