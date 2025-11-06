from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Instrument(Base):
    __tablename__ = 'instruments'
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    symbol = Column(String, unique=True, index=True, nullable=False)
    name = Column(String)
    expiry = Column(String)
    strike = Column(Float)
    lotsize = Column(Integer)
    instrumenttype = Column(String)
    exch_seg = Column(String)
    tick_size = Column(Float)

    historical_data = relationship("HistoricalOHLCV", back_populates="instrument")
    trades = relationship("Trade", back_populates="instrument")


class HistoricalOHLCV(Base):
    __tablename__ = 'historical_ohlcv'
    id = Column(Integer, primary_key=True, index=True)
    instrument_token = Column(String, ForeignKey('instruments.token'), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    interval = Column(String, nullable=False)

    instrument = relationship("Instrument", back_populates="historical_data")


class Trade(Base):
    __tablename__ = 'trades'
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, unique=True, index=True)
    instrument_token = Column(String, ForeignKey('instruments.token'), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    side = Column(String, nullable=False)  # 'BUY' or 'SELL'
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    pnl = Column(Float)
    strategy = Column(String)

    instrument = relationship("Instrument", back_populates="trades")
