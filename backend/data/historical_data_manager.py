import pandas as pd
from sqlalchemy.orm import Session
from datetime import datetime
from ..core.broker_service import angel_broking_service
from ..database.connection import get_db
from ..database.models import HistoricalOHLCV, Instrument
import logging

log = logging.getLogger(__name__)

def download_historical_data(instrument_token: str, from_date: str, to_date: str, interval: str, exchange: str):
    """
    Downloads historical OHLCV data for a given instrument and stores it in the database.

    :param instrument_token: The token of the instrument.
    :param from_date: The start date in 'YYYY-MM-DD HH:MM' format.
    :param to_date: The end date in 'YYYY-MM-DD HH:MM' format.
    :param interval: The candle interval (e.g., 'ONE_MINUTE', 'FIVE_MINUTE').
    :param exchange: The exchange segment (e.g., 'NSE', 'NFO').
    """
    db: Session = next(get_db())
    try:
        log.info(f"Checking for existing data for token {instrument_token} from {from_date} to {to_date}.")

        # Simple check to avoid re-downloading. A more robust solution might check for gaps.
        existing_data = db.query(HistoricalOHLCV).filter(
            HistoricalOHLCV.instrument_token == instrument_token,
            HistoricalOHLCV.timestamp >= datetime.strptime(from_date, '%Y-%m-%d %H:%M'),
            HistoricalOHLCV.timestamp <= datetime.strptime(to_date, '%Y-%m-%d %H:%M'),
            HistoricalOHLCV.interval == interval
        ).first()

        if existing_data:
            log.info("Data already exists for the specified period. Skipping download.")
            return

        log.info("No existing data found. Downloading from Angel Broking...")
        smart_connect = angel_broking_service.login()

        historic_params = {
            "exchange": exchange,
            "symboltoken": instrument_token,
            "interval": interval,
            "fromdate": from_date,
            "todate": to_date
        }

        data = smart_connect.getCandleData(historic_params)

        if data['status'] and isinstance(data['data'], list):
            df = pd.DataFrame(data['data'])
            if df.empty:
                log.warning(f"No data returned for token {instrument_token} for the specified period.")
                return

            df.rename(columns={0: 'timestamp', 1: 'open', 2: 'high', 3: 'low', 4: 'close', 5: 'volume'}, inplace=True)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['instrument_token'] = instrument_token
            df['interval'] = interval

            log.info(f"Downloaded {len(df)} records. Storing to database...")
            df.to_sql('historical_ohlcv', con=db.get_bind(), if_exists='append', index=False)
            db.commit()
            log.info("Historical data stored successfully.")
        else:
            log.error(f"Failed to download historical data: {data.get('message', 'Unknown error')}")

    except Exception as e:
        log.error(f"An error occurred during historical data download: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # Example of how to run the script directly
    # You would typically fetch the token and exchange from the instruments table
    # For NIFTY BANK index: token='26009', exch_seg='NFO'
    download_historical_data(
        instrument_token='26009',
        from_date='2024-01-01 09:15',
        to_date='2024-01-31 15:30',
        interval='FIVE_MINUTE',
        exchange='NFO'
    )
