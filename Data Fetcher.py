import duckdb
import yfinance as yf
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from constant import CREATE_SCHEMA_SQL, INSERT_COMPANY_DATA_SQL, INSERT_MARKET_DATA_SQL, get_sp500_tickers


def calculate_adjusted_shares(shares_outstanding: float, splits: pd.Series, hist_index: pd.DatetimeIndex) -> pd.Series:
    """Adjusts shares outstanding based on stock split history."""
    if splits.empty:
        return pd.Series(shares_outstanding, index=hist_index)
    
    # Sort splits in ascending order to process them correctly
    splits_ascending = splits.sort_index(ascending=True)
    split_dates = splits_ascending.index
    split_ratios = splits_ascending.values
    
    # Reverse the split ratios and compute cumulative product in reverse order
    reverse_ratios = split_ratios[::-1]
    cumprod_reverse = np.cumprod(reverse_ratios)[::-1]
    split_products = pd.Series(cumprod_reverse, index=split_dates)
    
    # Find the applicable split adjustment for each historical date
    hist_dates_np = hist_index.to_numpy()
    split_dates_np = split_dates.to_numpy()
    indices = np.searchsorted(split_dates_np, hist_dates_np, side='right')
    
    product = [split_products.iloc[indices[i]] if indices[i] < len(split_dates_np) else 1 
               for i in range(len(hist_dates_np))]
    
    return shares_outstanding / np.array(product)


def fetch_ticker_data(ticker: str, start_date: datetime, end_date: datetime) -> tuple:
    """Fetches historical market data and calculates market capitalization."""
    try:
        stock = yf.Ticker(ticker)
        # Retrieve historical closing prices
        hist = stock.history(start=start_date, end=end_date, interval="1d")["Close"]
        shares_outstanding = stock.info.get("sharesOutstanding", None)
        company_name = stock.info.get("longName", ticker)
        
        # If shares outstanding data is unavailable, return empty series
        if not shares_outstanding:
            return ticker, company_name, pd.Series(dtype='float64'), pd.Series(dtype='float64')
        
        # Adjust shares for stock splits
        splits = stock.splits 
        adjusted_shares = calculate_adjusted_shares(shares_outstanding, splits, hist.index)
        market_caps = (hist * adjusted_shares).astype("int64")
        
        return ticker, company_name, hist, market_caps
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return ticker, ticker, pd.Series(dtype='float64'), pd.Series(dtype='float64')


def create_database_schema(conn):
    """Creates the necessary database schema in DuckDB."""
    try:
        conn.execute(CREATE_SCHEMA_SQL)
        print("Schema created successfully")
    except Exception as e:
        print(f"Schema creation error: {e}")

def insert_company_data(conn, ticker: str, company_name: str):
    """Inserts company data into the companies table, ignoring duplicates."""
    try:
        conn.execute(INSERT_COMPANY_DATA_SQL, [ticker, company_name])
    except Exception as e:
        print(f"Error inserting company data for {ticker}: {e}")

def insert_market_data(conn, df: pd.DataFrame):
    """Inserts market data into the market_data table using a temporary DataFrame."""
    try:
        conn.register('temp_df', df)
        conn.execute(INSERT_MARKET_DATA_SQL)
    except Exception as e:
        print(f"Error inserting market data: {e}")

def main():
    """Main function that initializes the database, fetches data, and stores it."""
    db_path = 'PATH_TO/market_cap_data_new_3.duckdb'  # STORE DATABASE
    conn = duckdb.connect(db_path)

    try:
        # Set up database schema
        create_database_schema(conn)
        
        # Get list of S&P 500 tickers
        sp500_tickers = get_sp500_tickers()
        end_date = pd.Timestamp.today()
        start_date = end_date - pd.DateOffset(years=5)

        # Use multithreading to fetch data efficiently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_ticker_data, t, start_date, end_date) 
                       for t in sp500_tickers]
            
            # Process results as they complete
            for future in as_completed(futures):
                ticker, company_name, hist, market_caps = future.result()
                if not hist.empty and not market_caps.empty:
                    # Insert company details into database
                    insert_company_data(conn, ticker, company_name)
                    
                    # Create dataframe for historical data and insert into database
                    df = pd.DataFrame({
                        'date': hist.index.date,
                        'ticker': ticker,
                        'close_price': hist.values,
                        'market_cap': market_caps.values
                    })
                    insert_market_data(conn, df)

        print(f"Data successfully saved to {db_path}")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()
