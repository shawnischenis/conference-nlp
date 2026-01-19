import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import glob
import re

TRANSCRIPTS_DIR = 'Transcripts'
STOCK_DATA_DIR = 'StockData'
OUTPUT_DIR = 'EarningsReturns'

def parse_date_from_filename(filename, quarter_text=None):
    # Filename format YYYY-Mon-DD-TICKER.txt
    try:
        parts = filename.split('-')
        if len(parts) >= 3:
            date_str = f"{parts[0]}-{parts[1]}-{parts[2]}"
            return datetime.strptime(date_str, '%Y-%b-%d').date()
    except:
        pass
    return None

def calculate_returns():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    if not os.path.exists(STOCK_DATA_DIR):
        print("Stock data directory not found.")
        return

    # Find all transcripts to get earnings dates
    # We can iterate through the Transcripts directory again or look at parsed transcripts?
    # Better to look at Transcripts directory to get the date from filename as we did in create_master_table.
    # But we want to do it for all companies.
    
    tickers = [d for d in os.listdir(TRANSCRIPTS_DIR) if os.path.isdir(os.path.join(TRANSCRIPTS_DIR, d))]
    tickers.sort()
    
    print(f"Calculating returns for {len(tickers)} tickers...")
    
    for ticker in tickers:
        stock_file = os.path.join(STOCK_DATA_DIR, f"{ticker}.csv")
        if not os.path.exists(stock_file):
            print(f"Stock data for {ticker} not found. Skipping.")
            continue
            
        print(f"Processing {ticker}...")
        try:
            # Load stock data
            stock_df = pd.read_csv(stock_file)
            # Ensure Date is datetime
            stock_df['Date'] = pd.to_datetime(stock_df['Date'], utc=True).dt.date
            stock_df = stock_df.sort_values('Date').reset_index(drop=True)
            
            # Find earnings dates
            ticker_dir = os.path.join(TRANSCRIPTS_DIR, ticker)
            transcript_files = [f for f in os.listdir(ticker_dir) if f.endswith('.txt')]
            
            results = []
            
            for filename in transcript_files:
                earnings_date = parse_date_from_filename(filename)
                
                if earnings_date:
                    quarter = None
                    # Try to extract quarter from file content
                    try:
                        file_path = os.path.join(ticker_dir, filename)
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            # Read first 20 lines
                            lines = [f.readline() for _ in range(20)]
                            quarter_pattern = re.compile(r'(Q[1-4]\s+\d{4})')
                            for line in lines:
                                match = quarter_pattern.search(line)
                                if match:
                                    quarter = match.group(1)
                                    break
                    except Exception as e:
                        print(f"Error reading quarter from {filename}: {e}")

                    # Logic to find Quarter (we could parse file, but maybe just filename/date is enough for now)
                    # The user asked for "earnings return csv for each company"
                    
                    # Find index in stock data
                    idx_list = stock_df.index[stock_df['Date'] == earnings_date].tolist()
                    
                    if not idx_list:
                        # Sometimes earnings data is slightly off or on weekend
                        # Find closest next trading day?
                        # For simplicity, let's try to find the next few days
                        found = False
                        for i in range(1, 5):
                            next_date = earnings_date + timedelta(days=i)
                            idx_list = stock_df.index[stock_df['Date'] == next_date].tolist()
                            if idx_list:
                                earnings_date = next_date # Update to actual trading day
                                found = True
                                break
                        if not found:
                            # print(f"  Date {earnings_date} not found for {ticker}")
                            continue
                            
                    idx = idx_list[0]
                    
                    # Ensure enough data
                    if idx + 10 < len(stock_df):
                        close_t = stock_df.at[idx, 'Close']
                        close_t_1 = stock_df.at[idx + 1, 'Close']
                        # close_t_5 = stock_df.at[idx + 5, 'Close'] 
                        # Check bounds for t+5 and t+10
                        if idx + 5 < len(stock_df):
                            close_t_5 = stock_df.at[idx + 5, 'Close']
                            ret_5d = (close_t_5 - close_t) / close_t
                        else:
                            ret_5d = None
                            
                        if idx + 10 < len(stock_df):
                            close_t_10 = stock_df.at[idx + 10, 'Close']
                            ret_10d = (close_t_10 - close_t) / close_t
                        else:
                            ret_10d = None
                            
                        ret_1d = (close_t_1 - close_t) / close_t
                        
                        results.append({
                            'ticker': ticker,
                            'quarter': quarter,
                            'earnings_date': earnings_date, # This is the trading date used (t=0)
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
                
        except Exception as e:
            print(f"Error processing {ticker}: {e}")

if __name__ == "__main__":
    calculate_returns()
