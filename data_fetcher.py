import duckdb
import yfinance as yf
import pandas as pd
import numpy as np
import logging
import sys
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from constants import CREATE_SCHEMA_SQL, INSERT_COMPANY_DATA_SQL, INSERT_MARKET_DATA_SQL, SP500_TICKERS ,DB_PATH

# Configure logging to display messages in the terminal only
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(message)s'))  # Only show raw messages
logger.addHandler(handler)

def fetch_ticker_data(ticker: str, start_date: datetime, end_date: datetime) -> tuple:
    """Fetches historical market data and calculates market capitalization."""
    try:
        stock = yf.Ticker(ticker)
        # Retrieve historical closing prices
        hist = stock.history(start=start_date, end=end_date, interval="1d")["Close"]
        shares_outstanding = stock.info.get("sharesOutstanding", None)
        company_name = stock.info.get("longName", ticker)
        
        # Custom error for missing shares data
        if not shares_outstanding:
            logger.error(f"MISSING DATA ERROR: No shares outstanding data for {ticker}")
            return ticker, company_name, pd.Series(dtype='float64'), pd.Series(dtype='float64')
        
        # Calculate market capitalization directly
        market_caps = (hist * shares_outstanding).astype("int64")
        
        return ticker, company_name, hist, market_caps
    except Exception as e:
        logger.error(f"FETCH ERROR: {ticker} - {str(e)}")
        return ticker, ticker, pd.Series(dtype='float64'), pd.Series(dtype='float64')

def create_database_schema(conn):
    """Creates the necessary database schema in DuckDB."""
    try:
        conn.execute(CREATE_SCHEMA_SQL)
        logger.info("Schema created successfully")
    except Exception as e:
        logger.error(f"SCHEMA CREATION ERROR: {str(e)}")

def insert_company_data(conn, ticker: str, company_name: str):
    """Inserts company data into the companies table, ignoring duplicates."""
    try:
        conn.execute(INSERT_COMPANY_DATA_SQL, [ticker, company_name])
    except Exception as e:
        logger.error(f"DB INSERT ERROR: Company data for {ticker} - {str(e)}")

def insert_market_data(conn, df: pd.DataFrame):
    """Inserts market data into the market_data table using a temporary DataFrame."""
    try:
        conn.register('temp_df', df)
        conn.execute(INSERT_MARKET_DATA_SQL)
    except Exception as e:
        logger.error(f"DB INSERT ERROR: Market data - {str(e)}")

def main():
    """Main function that initializes the database, fetches data, and stores it."""
    conn = duckdb.connect(DB_PATH)
    # conn = duckdb.connect(':memory:')  # In memory

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Fetch S&P 500 market data.')
    parser.add_argument('--start-date', required=True, help='Start date in YYYYMMDD format')
    parser.add_argument('--end-date', required=True, help='End date in YYYYMMDD format')
    args = parser.parse_args()

    # Sanitize input by removing dashes if present
    args.start_date = args.start_date.replace("-", "")
    args.end_date = args.end_date.replace("-", "")

    try:
        # Parse and validate dates
        start_date_input = datetime.strptime(args.start_date, "%Y%m%d").date()
        end_date_input = datetime.strptime(args.end_date, "%Y%m%d").date()
    except ValueError as e:
        logger.error(f"INVALID DATE ERROR: {e}. Please use YYYYMMDD format.")
        sys.exit(1)

    if start_date_input >= end_date_input:
        logger.error("DATE ORDER ERROR: Start date must be before end date.")
        sys.exit(1)

    try:
        create_database_schema(conn)
        
        # Convert to pandas Timestamps and add 1 day to end date to make it inclusive
        start_date = pd.Timestamp(start_date_input)
        end_date = pd.Timestamp(end_date_input) + pd.DateOffset(days=1)
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_ticker_data, t, start_date, end_date) 
                       for t in SP500_TICKERS]
            
            for future in as_completed(futures):
                ticker, company_name, hist, market_caps = future.result()
                if not hist.empty and not market_caps.empty:
                    insert_company_data(conn, ticker, company_name)
                    
                    df = pd.DataFrame({
                        'date': hist.index.date,
                        'ticker': ticker,
                        'close_price': hist.values,
                        'market_cap': market_caps.values
                    })
                    insert_market_data(conn, df)

        logger.info(f"\nData successfully saved to {DB_PATH}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    main()
