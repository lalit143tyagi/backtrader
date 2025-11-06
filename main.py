import backtrader as bt
from datetime import datetime
from angel_integration.store import AngelStore
from angel_integration.data import AngelData
from angel_integration.broker import AngelBroker
import json

# --- 1. Define a Simple Trading Strategy ---
class MovingAverageCross(bt.Strategy):
    """
    A simple moving average crossover strategy to demonstrate the system.
    - Buys when the fast moving average crosses above the slow moving average.
    - Sells when the fast moving average crosses below the slow moving average.
    """
    params = (
        ('fast_length', 10),
        ('slow_length', 30),
    )

    def __init__(self):
        self.fast_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.p.fast_length
        )
        self.slow_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.p.slow_length
        )
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)

    def next(self):
        # If we are already in the market, don't do anything
        if self.position:
            # Sell signal
            if self.crossover < 0:
                print(f"SELL SIGNAL: Fast MA ({self.fast_ma[0]:.2f}) crossed below Slow MA ({self.slow_ma[0]:.2f})")
                self.sell(size=1)
        # Not in the market, look for a buy signal
        else:
            # Buy signal
            if self.crossover > 0:
                print(f"BUY SIGNAL: Fast MA ({self.fast_ma[0]:.2f}) crossed above Slow MA ({self.slow_ma[0]:.2f})")
                self.buy(size=1)

# --- 2. Main Execution Block ---
def run_backtest():
    """
    This function sets up and runs the Backtrader engine with our custom
    Angel Broking integration components.
    """
    cerebro = bt.Cerebro()

    # --- Add the Store and Broker ---
    # The store will handle the login and session management.
    # It will prompt for credentials if they are not found in config.json
    try:
        # Create a dummy config file if it doesn't exist
        try:
            with open('config.json', 'r') as f:
                pass
        except FileNotFoundError:
            with open('config.json', 'w') as f:
                json.dump({"api_key": "YOUR_API_KEY"}, f)
            print("Created a dummy 'config.json'. Please replace 'YOUR_API_KEY' with your actual key.")

        # The AngelStore is a singleton and will be instantiated automatically
        # by the Broker and Data feed, so we don't need to add it to Cerebro.
        broker = AngelBroker()
        cerebro.setbroker(broker)

    except (ValueError, ConnectionError) as e:
        print(f"Could not initialize the system: {e}")
        return

    # --- Add the Data Feed ---
    # This will fetch historical data for the specified instrument and timeframe.
    data = AngelData(
        dataname='SBIN-EQ', # The symbol you want to trade
        fromdate=datetime(2023, 1, 1),
        todate=datetime(2023, 12, 31),
        timeframe=bt.TimeFrame.Days,
        compression=1,
    )
    cerebro.adddata(data)

    # --- Add the Strategy ---
    cerebro.addstrategy(MovingAverageCross)

    # --- Set Initial Capital ---
    cerebro.broker.setcash(100000.0)

    # --- Run the Backtest ---
    print("Starting Portfolio Value: %.2f" % cerebro.broker.getvalue())
    cerebro.run()
    print("Final Portfolio Value: %.2f" % cerebro.broker.getvalue())

    # --- Plot the Results (optional) ---
    cerebro.plot(style='candlestick', barup='green', bardown='red')


if __name__ == '__main__':
    # Before running, make sure your database is set up and populated.
    # You can run `database/manager.py` to do this.
    print("--- Angel Broking Backtrader Integration ---")
    print("This script will run a simple backtest using the components we built.")
    print("Please ensure you have run 'database/manager.py' at least once to populate your instrument list.")

    run_backtest()
