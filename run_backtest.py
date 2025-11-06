import backtrader as bt
from datetime import datetime
from backend.strategies.supertrend import SuperTrendStrategy
from backend.trading.angelbroker import AngelBroker
from backend.data.data_feed import PostgresDataFeed
from backend.data.instrument_manager import update_instrument_list
from backend.data.historical_data_manager import download_historical_data

def run_backtest():
    """
    Sets up and runs a backtest of the SuperTrendStrategy.
    """
    # --- 1. Initial Setup: Define Backtest Parameters ---
    print("Step 1: Defining backtest parameters...")
    INSTRUMENT_TOKEN = '26009'
    INSTRUMENT_SYMBOL = 'BANKNIFTY' # Must match the symbol in the seeder
    FROM_DATE = '2024-01-30 09:15'
    TO_DATE = '2024-01-30 09:50'
    INTERVAL = 'FIVE_MINUTE'

    # --- 2. Cerebro Engine Setup ---
    print("Step 2: Setting up Cerebro backtesting engine...")
    cerebro = bt.Cerebro()

    # --- 3. Add Data Feed ---
    data_feed = PostgresDataFeed(
        instrument_token=INSTRUMENT_TOKEN,
        fromdate=datetime.strptime(FROM_DATE, '%Y-%m-%d %H:%M'),
        todate=datetime.strptime(TO_DATE, '%Y-%m-%d %H:%M'),
        interval=INTERVAL
    )
    cerebro.adddata(data_feed, name=INSTRUMENT_SYMBOL) # Give a name to the data feed for the broker to find it

    # --- 4. Add Broker ---
    # The broker requires a live login for some operations, but we can backtest without it.
    # For backtesting, it will use the cash and position info we provide.
    broker = AngelBroker()
    cerebro.setbroker(broker)
    cerebro.broker.setcash(100000.00)

    # --- 5. Add Strategy ---
    cerebro.addstrategy(SuperTrendStrategy)

    # --- 6. Add Analyzers ---
    cerebro.addanalyzer(bt.analyzers.Sharpe, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='tradeanalyzer')


    # --- 7. Run the Backtest ---
    print("Step 4: Running backtest...")
    initial_portfolio_value = cerebro.broker.getvalue()
    print(f'Starting Portfolio Value: {initial_portfolio_value:.2f}')

    results = cerebro.run()

    final_portfolio_value = cerebro.broker.getvalue()
    print(f'Final Portfolio Value:   {final_portfolio_value:.2f}')
    print(f'Total PnL: {(final_portfolio_value - initial_portfolio_value):.2f}')

    # --- 8. Print Results ---
    print("\n--- Backtest Results ---")
    strat = results[0]
    print('Sharpe Ratio:', strat.analyzers.sharpe.get_analysis().get('sharperatio', 'N/A'))
    print('Max Drawdown:', f"{strat.analyzers.drawdown.get_analysis().max.drawdown:.2f}%")
    trade_analysis = strat.analyzers.tradeanalyzer.get_analysis()
    if trade_analysis.total.total > 0:
        print("Total Trades:", trade_analysis.total.total)
        print("Winning Trades:", trade_analysis.won.total)
        print("Losing Trades:", trade_analysis.lost.total)
        print("Win Rate:", f"{(trade_analysis.won.total / trade_analysis.total.total) * 100:.2f}%")

if __name__ == '__main__':
    run_backtest()
