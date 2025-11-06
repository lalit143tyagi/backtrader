import sys
import os

# Add the backend to the Python path to allow for absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

def verify_imports():
    """
    Attempts to import all key modules to check for syntax errors,
    circular dependencies, or other import-related issues.
    """
    print("--- Starting Import Verification ---")
    try:
        from core import broker_service, config
        print("[SUCCESS] Imported: core modules")

        from data import data_feed, historical_data_manager, instrument_manager
        print("[SUCCESS] Imported: data modules")

        from database import connection, models
        print("[SUCCESS] Imported: database modules")

        from strategies import indicators, supertrend
        print("[SUCCESS] Imported: strategies modules")

        from trading import angelbroker, angelstore, oms
        print("[SUCCESS] Imported: trading modules")

        from main import app
        print("[SUCCESS] Imported: main FastAPI app")

        print("\n--- All modules imported successfully! ---")
        return True

    except ImportError as e:
        print(f"\n[FAILURE] An error occurred during import: {e}")
        return False

if __name__ == "__main__":
    if not verify_imports():
        sys.exit(1)
