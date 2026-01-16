import yfinance as yf
import pandas as pd
import os
import time

TRANSCRIPTS_DIR = 'Transcripts'
OUTPUT_DIR = 'StockData'

def get_tickers():
    if not os.path.exists(TRANSCRIPTS_DIR):
        print(f"Directory {TRANSCRIPTS_DIR} not found.")
        return []
    tickers = [d for d in os.listdir(TRANSCRIPTS_DIR) if os.path.isdir(os.path.join(TRANSCRIPTS_DIR, d))]
    return sorted(tickers)

def fetch_stock_data():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    tickers = get_tickers()
    print(f"Found {len(tickers)} tickers: {tickers}")
    
    for ticker in tickers:
        output_file = os.path.join(OUTPUT_DIR, f"{ticker}.csv")
        
        # Skip if already exists (optional, but good for resuming)
        if os.path.exists(output_file):
            print(f"Data for {ticker} already exists. Skipping...")
            continue
            
        print(f"Fetching data for {ticker}...")
        try:
            ticker_data = yf.Ticker(ticker)
            # Fetching max history to ensure coverage
            # Using auto_adjust=True to get split-adjusted prices which is generally better for returns
            hist = ticker_data.history(period="max", auto_adjust=True)
            
            if hist.empty:
                print(f"No data found for {ticker}")
            else:
                hist.to_csv(output_file)
                print(f"Saved {ticker} data to {output_file}")
                
            # Be nice to the API
            time.sleep(1)
            
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")

if __name__ == "__main__":
    fetch_stock_data()
