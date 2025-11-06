import pandas as pd
from sqlalchemy.orm import Session
from ..core.broker_service import angel_broking_service
from ..database.connection import get_db
from ..database.models import Instrument
import logging

log = logging.getLogger(__name__)

def update_instrument_list():
    """
    Fetches the latest instrument list from Angel Broking and updates the database.
    """
    try:
        smart_connect = angel_broking_service.login()
        instrument_list = smart_connect.get_instrument_list()

        if not instrument_list:
            log.error("Failed to fetch instrument list.")
            return

        df = pd.DataFrame(instrument_list)
        df = df[['token', 'symbol', 'name', 'expiry', 'strike', 'lotsize', 'instrumenttype', 'exch_seg', 'tick_size']]

        db: Session = next(get_db())

        # A simple way to bulk update/insert. For production, a more robust method like upsert might be needed.
        # For this phase, we clear the table and insert fresh data.
        log.info("Deleting old instrument data...")
        db.query(Instrument).delete()

        log.info(f"Inserting {len(df)} new instruments...")
        df.to_sql('instruments', con=db.get_bind(), if_exists='append', index=False)

        db.commit()
        log.info("Instrument list updated successfully.")

    except Exception as e:
        log.error(f"Error updating instrument list: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # This allows running the script directly to populate the database
    update_instrument_list()
