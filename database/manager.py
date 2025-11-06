import psycopg2
import psycopg2.extras
import pandas as pd
from SmartApi.smartConnect import SmartConnect
import json
import os
import getpass

"""
This module handles all interactions with the PostgreSQL database.
It is responsible for:
- Establishing a connection to the database.
- Creating the necessary tables (e.g., for instruments).
- Populating the tables with data fetched from the Angel Broking API.
- Providing helper functions to query the database (e.g., looking up an instrument token).
"""

def get_db_connection():
    """
    Establishes a connection to the PostgreSQL database.

    IMPORTANT: Replace the placeholder values below with your actual
    database credentials. For better security, it is highly recommended to
    use environment variables or a configuration file to store these secrets,
    rather than hardcoding them.
    """
    try:
        conn = psycopg2.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            database=os.environ.get("DB_NAME", "your_db_name"),
            user=os.environ.get("DB_USER", "your_db_user"),
            password=os.environ.get("DB_PASSWORD", "your_db_password")
        )
        return conn
    except psycopg2.OperationalError as e:
        print(f"Error: Could not connect to the PostgreSQL database.")
        print(f"Please ensure the database is running and that your connection details are correct.")
        print(f"You can set them using environment variables: DB_HOST, DB_NAME, DB_USER, DB_PASSWORD")
        raise e


def create_instruments_table():
    """Creates the 'instruments' table if it doesn't exist."""
    print("Creating 'instruments' table if it does not exist...")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS instruments (
            token VARCHAR(255) PRIMARY KEY,
            symbol VARCHAR(255),
            name VARCHAR(255),
            expiry DATE,
            strike NUMERIC,
            lotsize INTEGER,
            instrumenttype VARCHAR(255),
            exch_seg VARCHAR(255),
            tick_size NUMERIC
        );
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("'instruments' table created successfully.")


def _fetch_instrument_list_from_api(smart_connect_session):
    """
    Fetches the full instrument list from the Angel Broking API.

    Args:
        smart_connect_session: An authenticated SmartConnect session object.

    Returns:
        A list of dictionaries, where each dictionary represents an instrument.
    """
    try:
        instrument_list = smart_connect_session.get_instrument_list()
        if instrument_list is None or "data" not in instrument_list:
            print("Error: Could not fetch instrument list from API. The response was empty or invalid.")
            return None
        return instrument_list["data"]
    except Exception as e:
        print(f"An error occurred while fetching instrument list from API: {e}")
        return None


def populate_instruments_table(smart_connect_session):
    """
    Fetches the instrument list from Angel Broking and populates the database.

    This function will clear the existing 'instruments' table before inserting
    the new list to ensure the data is always up-to-date.

    Args:
        smart_connect_session: An authenticated SmartConnect session object.
    """
    print("Fetching latest instrument list from Angel Broking API...")
    instrument_list = _fetch_instrument_list_from_api(smart_connect_session)

    if not instrument_list:
        print("Could not populate instruments table because the instrument list could not be fetched.")
        return

    print(f"Successfully fetched {len(instrument_list)} instruments. Populating database...")
    df = pd.DataFrame(instrument_list)

    # Clean and format data before insertion
    df['strike'] = pd.to_numeric(df['strike'], errors='coerce') * 100 # Convert to cents or smallest unit
    df['expiry'] = pd.to_datetime(df['expiry'], errors='coerce')
    df = df.where(pd.notnull(df), None) # Replace NaN with None for DB compatibility

    conn = get_db_connection()
    cur = conn.cursor()

    print("Clearing existing data from 'instruments' table...")
    cur.execute("TRUNCATE TABLE instruments;")

    print("Inserting new instrument data...")
    # Use executemany for efficient bulk insertion
    values = df[[
        'token', 'symbol', 'name', 'expiry', 'strike', 'lotsize',
        'instrumenttype', 'exch_seg', 'tick_size'
    ]].values.tolist()

    psycopg2.extras.execute_values(
        cur,
        """
        INSERT INTO instruments (token, symbol, name, expiry, strike, lotsize, instrumenttype, exch_seg, tick_size)
        VALUES %s
        ON CONFLICT (token) DO NOTHING;
        """,
        values
    )

    conn.commit()
    cur.close()
    conn.close()
    print("Instruments table populated successfully.")


def get_instrument_token(symbol, exch_seg='NSE'):
    """
    Looks up the token for a given instrument symbol from the local database.

    Args:
        symbol (str): The trading symbol (e.g., 'SBIN-EQ').
        exch_seg (str): The exchange segment (e.g., 'NSE').

    Returns:
        The instrument token as a string, or None if not found.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT token FROM instruments WHERE symbol = %s AND exch_seg = %s", (symbol, exch_seg))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else None

def main():
    """
    Main function to demonstrate the module's capabilities.

    This will guide the user through logging in, creating the table,
    and populating it with the latest instrument data.
    """
    print("--- Database Manager ---")

    try:
        # Create the table first
        create_instruments_table()

        # Explain the next step
        print("\nTo populate the database, you need to log in to Angel Broking.")
        api_key = input("Enter your API Key: ")
        client_id = getpass.getpass("Enter your Client ID (PIN): ")
        password = getpass.getpass("Enter your Password: ")
        totp = input("Enter your TOTP: ")

        # Create a SmartConnect session
        smart_api = SmartConnect(api_key)

        # Login and generate session
        data = smart_api.generate_session(client_id, password, totp)

        if data['status'] and data['data']['jwtToken']:
            print("Login successful!")
            # Populate the table using the authenticated session
            populate_instruments_table(smart_api)

            # Example lookup
            print("\n--- Example Lookup ---")
            token = get_instrument_token('SBIN-EQ', 'NSE')
            if token:
                print(f"Successfully found token for SBIN-EQ: {token}")
            else:
                print("Could not find token for SBIN-EQ. Please check the symbol.")
        else:
            print(f"Login Failed: {data['message']}")

    except psycopg2.OperationalError:
        # Error is already handled in get_db_connection
        pass
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == '__main__':
    main()
