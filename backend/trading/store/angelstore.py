import json
import pyotp
from SmartApi import SmartConnect
from backend.core.config import settings
from backend.core.models import SessionLocal, Instrument, OHLCV, init_db
import os
import pandas as pd
from datetime import datetime

class AngelStore:
    def __init__(self):
        init_db()
        self.smart_api = SmartConnect(api_key=settings.ANGEL_API_KEY)
        self.session = self._create_session()
        self.db_session = SessionLocal()
        self.instrument_list = self._fetch_instrument_list()

    def _create_session(self):
        try:
            totp = pyotp.TOTP(settings.ANGEL_TOTP_SECRET).now()
            data = self.smart_api.generateSession(settings.ANGEL_CLIENT_ID, settings.ANGEL_PASSWORD, totp)
            if data["status"] and data["data"]["jwtToken"]:
                print("Session created successfully.")
                return data["data"]
            else:
                raise Exception(f"Failed to create session: {data['message']}")
        except Exception as e:
            print(f"Error creating session: {e}")
            return None

    def _fetch_instrument_list(self):
        if self.db_session.query(Instrument).first():
            return self.db_session.query(Instrument).all()
        try:
            print("Fetching instrument list from API...")
            instrument_list_json = self.smart_api.getInstrumentList()
            if instrument_list_json["status"]:
                instruments = [
                    Instrument(
                        token=i['token'],
                        symbol=i['symbol'],
                        name=i['name'],
                        exchange=i['exch_seg'],
                        instrument_type=i['instrumenttype']
                    ) for i in instrument_list_json["data"]
                ]
                self.db_session.add_all(instruments)
                self.db_session.commit()
                return instruments
            else:
                raise Exception("Could not fetch instrument list.")
        except Exception as e:
            print(f"Error fetching instrument list: {e}")
            return []

    def get_instrument_token(self, name, segment='NSE', symbol_type='INDICES'):
        instrument = self.db_session.query(Instrument).filter(
            Instrument.name == name,
            Instrument.exchange == segment
        ).first()
        return instrument.token if instrument else None

    def get_historical_data(self, token, from_date, to_date, interval):
        from_datetime = datetime.strptime(from_date, "%Y-%m-%d %H:%M")
        to_datetime = datetime.strptime(to_date, "%Y-%m-%d %H:%M")

        db_data = self.db_session.query(OHLCV).filter(
            OHLCV.instrument_token == token,
            OHLCV.timestamp >= from_datetime,
            OHLCV.timestamp <= to_datetime
        ).all()

        if db_data:
            df = pd.DataFrame([{'timestamp': d.timestamp, 'open': d.open, 'high': d.high, 'low': d.low, 'close': d.close, 'volume': d.volume} for d in db_data])
            df.set_index('timestamp', inplace=True)
            return df

        params = {"exchange": "NSE", "symboltoken": token, "interval": interval, "fromdate": from_date, "todate": to_date}
        try:
            print(f"Fetching historical data for token {token} from API...")
            data = self.smart_api.getCandleData(params)
            if data["status"]:
                ohlcv_records = [
                    OHLCV(
                        instrument_token=token,
                        timestamp=datetime.strptime(row[0], "%Y-%m-%dT%H:%M:%S%z"),
                        open=row[1], high=row[2], low=row[3], close=row[4], volume=row[5]
                    ) for row in data["data"]
                ]
                self.db_session.add_all(ohlcv_records)
                self.db_session.commit()

                df = pd.DataFrame(data["data"], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
                return df
            else:
                return pd.DataFrame()
        except Exception as e:
            print(f"Error fetching historical data: {e}")
            return pd.DataFrame()

_store_instance = None

def get_store():
    """Singleton factory for AngelStore"""
    global _store_instance
    if _store_instance is None:
        _store_instance = AngelStore()
    return _store_instance
