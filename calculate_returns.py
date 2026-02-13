import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
import os
import re
from typing import Optional, List, Dict, Any

# --- Configuration & Constants ---
TRANSCRIPTS_DIR = 'Transcripts'
STOCK_DATA_DIR = 'StockData'
OUTPUT_DIR = 'EarningsReturns'

# Regex to detect quarters in text (e.g., "Q1 2024")
QUARTER_PATTERN = re.compile(r'(Q[1-4]\s+\d{4})')


def parse_date_from_filename(filename: str) -> Optional[date]:
    """
    Parses the earnings date from the transcript filename.
    Expected format: YYYY-Mon-DD-TICKER.txt (e.g., 2023-Oct-25-AMD.txt)
    """
    try:
        parts = filename.split('-')
        if len(parts) >= 3:
            # Construct date string: Year-Month-Day
            date_str = f"{parts[0]}-{parts[1]}-{parts[2]}"
            return datetime.strptime(date_str, '%Y-%b-%d').date()
    except (ValueError, IndexError):
        pass
    return None


def extract_quarter_from_file(file_path: str) -> Optional[str]:
    """
    Attempts to extract the fiscal quarter (e.g., 'Q3 2023') from the 
    first 20 lines of the transcript file.
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            # Read only the first 20 lines to avoid processing the whole file
            lines = [f.readline() for _ in range(20)]
            
        for line in lines:
            match = QUARTER_PATTERN.search(line)
            if match:
                return match.group(1)
    except Exception as e:
        print(f"Warning: Could not read quarter from {file_path}: {e}")
    
    return None


def load_stock_data(ticker: str) -> Optional[pd.DataFrame]:
    """
    Loads and preprocesses stock data for a given ticker.
    Returns a DataFrame with a 'Date' column normalized to datetime.date objects, 
    sorted by date.
    """
    stock_file = os.path.join(STOCK_DATA_DIR, f"{ticker}.csv")
    if not os.path.exists(stock_file):
        print(f"Stock data for {ticker} not found at {stock_file}. Skipping.")
        return None

    try:
        df = pd.read_csv(stock_file)
        # Convert Date column to datetime objects, then extract the date part
        # UTC=True is used to handle potential timezone awareness in source data
        df['Date'] = pd.to_datetime(df['Date'], utc=True).dt.date
        df = df.sort_values('Date').reset_index(drop=True)
        return df
    except Exception as e:
        print(f"Error loading stock data for {ticker}: {e}")
        return None


def calculate_window_return(
    df: pd.DataFrame, 
    start_idx: int, 
    window_days: int
) -> Optional[float]:
    """
    Calculates the return over a specific window (e.g., 1 day, 5 days).
    
    Args:
        df: Stock DataFrame
        start_idx: The index of the earnings date (t=0)
        window_days: Number of days forward to calculate return for
        
    Returns:
        The percentage return (e.g., 0.05 for 5%) or None if data is insufficient.
    """
    target_idx = start_idx + window_days
    
    # Ensure the target index is within bounds of the DataFrame
    if target_idx < len(df):
        price_t = df.at[start_idx, 'Close']
        price_target = df.at[target_idx, 'Close']
        
        if price_t == 0: # Avoid division by zero
            return None
            
        return (price_target - price_t) / price_t
        
    return None


def find_trading_day_index(
    df: pd.DataFrame, 
    target_date: date, 
    max_lookahead: int = 5
) -> Optional[int]:
    """
    Finds the index of the target date in the DataFrame.
    If the target date is not a trading day (e.g., weekend/holiday),
    searches for the next available trading day within `max_lookahead` days.
    """
    # First, try to find the exact date
    idx_list = df.index[df['Date'] == target_date].tolist()
    if idx_list:
        return idx_list[0]
    
    # If not found, look ahead for the next trading day
    for i in range(1, max_lookahead + 1):
        next_date = target_date + timedelta(days=i)
        idx_list = df.index[df['Date'] == next_date].tolist()
        if idx_list:
            return idx_list[0]
            
    return None


def process_ticker(ticker: str):
    """
    Processes a single ticker: finds transcripts, matches with stock data,
    calculates returns, and saves the result to a CSV.
    """
    print(f"Processing {ticker}...")
    
    stock_df = load_stock_data(ticker)
    if stock_df is None:
        return

    ticker_dir = os.path.join(TRANSCRIPTS_DIR, ticker)
    if not os.path.isdir(ticker_dir):
        return

    transcript_files = [f for f in os.listdir(ticker_dir) if f.endswith('.txt')]
    results = []

    for filename in transcript_files:
        earnings_date = parse_date_from_filename(filename)
        
        if not earnings_date:
            continue
            
        # 1. content parsing
        quarter = extract_quarter_from_file(os.path.join(ticker_dir, filename))
        
        # 2. Match with stock data
        start_idx = find_trading_day_index(stock_df, earnings_date)
        
        if start_idx is None:
            # Date (and near future dates) not found in stock data
            continue
        
        # Retrieve the actual date used (in case we moved forward)
        actual_date = stock_df.at[start_idx, 'Date']

        # 3. Calculate returns for different windows
        ret_1d = calculate_window_return(stock_df, start_idx, 1)
        ret_5d = calculate_window_return(stock_df, start_idx, 5)
        ret_10d = calculate_window_return(stock_df, start_idx, 10)

        results.append({
            'ticker': ticker,
            'quarter': quarter,
            'earnings_date': actual_date, # The trading date used for t=0
            'original_filename': filename,
            '1_day_return': ret_1d,
            '5_day_return': ret_5d,
            '10_day_return': ret_10d
        })

    if results:
        results_df = pd.DataFrame(results)
        output_csv = os.path.join(OUTPUT_DIR, f"{ticker}_returns.csv")
        results_df.to_csv(output_csv, index=False)
        print(f"  Saved returns to {output_csv}")


def calculate_returns():
    """
    Main entry point. Iterates through all tickers in the transcripts directory
    and calculates earnings returns.
    """
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    if not os.path.exists(STOCK_DATA_DIR):
        print(f"Error: Stock data directory '{STOCK_DATA_DIR}' not found.")
        return

    # Get list of tickers from directories in Transcripts/
    if not os.path.exists(TRANSCRIPTS_DIR):
        print(f"Error: Transcripts directory '{TRANSCRIPTS_DIR}' not found.")
        return

    tickers = [
        d for d in os.listdir(TRANSCRIPTS_DIR) 
        if os.path.isdir(os.path.join(TRANSCRIPTS_DIR, d))
    ]
    tickers.sort()
    
    print(f"Calculating returns for {len(tickers)} tickers...")
    
    for ticker in tickers:
        process_ticker(ticker)


if __name__ == "__main__":
    calculate_returns()
