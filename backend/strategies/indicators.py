import backtrader as bt

class SuperTrend(bt.Indicator):
    """
    SuperTrend Indicator
    """
    params = (('period', 10), ('multiplier', 3),)
    lines = ('supertrend',)
    plotinfo = dict(subplot=False)

    def __init__(self):
        self.atr = bt.indicators.ATR(self.data, period=self.p.period)
        self.basic_upperband = (self.data.high + self.data.low) / 2 + self.p.multiplier * self.atr
        self.basic_lowerband = (self.data.high + self.data.low) / 2 - self.p.multiplier * self.atr

        self.final_upperband = self.basic_upperband
        self.final_lowerband = self.basic_lowerband

        # The supertrend line will be calculated in next()
        self.lines.supertrend = bt.LinePlotter(plotname='SuperTrend')


    def next(self):
        # Final Upperband Calculation
        if self.basic_upperband[0] < self.final_upperband[-1] or self.data.close[-1] > self.final_upperband[-1]:
            self.final_upperband[0] = self.basic_upperband[0]
        else:
            self.final_upperband[0] = self.final_upperband[-1]

        # Final Lowerband Calculation
        if self.basic_lowerband[0] > self.final_lowerband[-1] or self.data.close[-1] < self.final_lowerband[-1]:
            self.final_lowerband[0] = self.basic_lowerband[0]
        else:
            self.final_lowerband[0] = self.final_lowerband[-1]

        # SuperTrend Calculation
        if self.data.close[0] > self.final_upperband[0]:
            self.lines.supertrend[0] = self.final_lowerband[0]
        else:
            self.lines.supertrend[0] = self.final_upperband[0]
