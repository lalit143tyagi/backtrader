import backtrader as bt
from backend.trading.feeds.angeldata import AngelData
from backend.trading.strategy.ema_crossover import EMACrossover
from backend.core.models import engine
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
import time
import os

def check_db_ready():
    retries = 5
    while retries > 0:
        try:
            connection = engine.connect()
            connection.close()
            print("Database is ready.")
            return True
        except OperationalError:
            print("Database not ready, waiting...")
            time.sleep(5)
            retries -= 1
    print("Database connection failed.")
    return False

if __name__ == '__main__':
    if not check_db_ready():
        exit()

    # Create a cerebro entity
    cerebro = bt.Cerebro()

    # Add a strategy
    cerebro.addstrategy(EMACrossover)

    # Create a Data Feed
    data = AngelData()

    # Add the Data Feed to Cerebro
    cerebro.adddata(data)

    # Set our desired cash start
    cerebro.broker.setcash(100000.0)

    # Print out the starting conditions
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Run over everything
    cerebro.run()

    # Print out the final result
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Plot the result
    # cerebro.plot()
