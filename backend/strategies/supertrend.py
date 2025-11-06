import backtrader as bt
from .indicators import SuperTrend

class SuperTrendStrategy(bt.Strategy):
    """
    A simple strategy based on the SuperTrend indicator.
    """
    params = (
        ('st_period', 10),
        ('st_multiplier', 3),
    )

    def __init__(self):
        self.supertrend = SuperTrend(self.data, period=self.p.st_period, multiplier=self.p.st_multiplier)
        self.order = None

        # Crossover signals
        self.crossover_up = bt.indicators.CrossUp(self.data.close, self.supertrend.lines.supertrend)
        self.crossover_down = bt.indicators.CrossDown(self.data.close, self.supertrend.lines.supertrend)

    def log(self, txt, dt=None):
        ''' Logging function for this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
            else:  # Sell
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def next(self):
        # Check if we are in the market
        if not self.position:
            if self.crossover_up > 0:
                self.log('BUY CREATE, %.2f' % self.data.close[0])
                self.order = self.buy()
            elif self.crossover_down > 0:
                self.log('SELL CREATE, %.2f' % self.data.close[0])
                self.order = self.sell()
        else:
            # Logic to close position
            if self.position.size > 0 and self.crossover_down > 0:
                self.log('CLOSE LONG, %.2f' % self.data.close[0])
                self.order = self.close()
            elif self.position.size < 0 and self.crossover_up > 0:
                self.log('CLOSE SHORT, %.2f' % self.data.close[0])
                self.order = self.close()
