import pandas as pd
from sqlalchemy.orm import Session
from backend.database.connection import get_db, engine
from backend.database.models import Base, Instrument, HistoricalOHLCV
import logging

log = logging.getLogger(__name__)

def seed_database():
    """
    Populates the database with sample data for offline testing.
    """
    db: Session = next(get_db())
    try:
        # Create tables
        Base.metadata.create_all(bind=engine)

        # --- 1. Seed Instruments Table ---
        log.info("Seeding instruments table...")

        # Clear existing data to prevent duplicates
        db.query(Instrument).delete()

        nifty_bank = Instrument(
            token='26009',
            symbol='BANKNIFTY',
            name='NIFTY BANK',
            expiry='',
            strike=0.0,
            lotsize=15,
            instrumenttype='INDEX',
            exch_seg='NFO',
            tick_size=0.05
        )
        db.add(nifty_bank)
        db.commit()
        log.info("Instrument seeding complete.")

        # --- 2. Seed Historical OHLCV Table ---
        log.info("Seeding historical_ohlcv table...")

        # Clear existing data
        db.query(HistoricalOHLCV).delete()

        df = pd.read_csv('sample_data.csv', parse_dates=['timestamp'])
        df['instrument_token'] = nifty_bank.token
        df['interval'] = 'FIVE_MINUTE'

        df.to_sql('historical_ohlcv', con=db.get_bind(), if_exists='append', index=False)
        db.commit()
        log.info("Historical OHLCV data seeding complete.")

    except Exception as e:
        log.error(f"An error occurred during database seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
