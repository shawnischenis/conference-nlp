import pandas as pd
import numpy as np
from datetime import datetime

def calculate_returns():
    # Load Master Table
    master_df = pd.read_csv('earnings_master_table.csv')
    mu_earnings = master_df[master_df['ticker'] == 'MU'].copy()

    # Load Stock Data
    stock_df = pd.read_csv('MU_data/micron_stock_2016_2020.csv')
    
    # Convert 'Date' to datetime and normalize to remove time/timezone for matching
    stock_df['Date'] = pd.to_datetime(stock_df['Date'], utc=True).dt.date
    stock_df = stock_df.sort_values('Date').reset_index(drop=True)

    # Function to parse earnings date
    def parse_date(date_str):
        try:
            return datetime.strptime(date_str, '%Y-%b-%d').date()
        except ValueError:
            return None

    mu_earnings['parsed_date'] = mu_earnings['earnings_date'].apply(parse_date)

    results = []

    for index, row in mu_earnings.iterrows():
        earnings_date = row['parsed_date']
        if earnings_date is None:
            print(f"Skipping invalid date: {row['earnings_date']}")
            continue

        # Find index in stock data
        # We look for the exact date. If not found, we can't calculate exact return from that date.
        # However, earnings calls are usually on trading days.
        try:
            # Get the index of the earnings date
            idx_list = stock_df.index[stock_df['Date'] == earnings_date].tolist()
            
            if not idx_list:
                print(f"Date {earnings_date} not found in stock data.")
                continue
            
            idx = idx_list[0]
            
            # Ensure we have enough data for 10-day return
            if idx + 10 >= len(stock_df):
                print(f"Not enough data for {earnings_date}")
                continue

            close_t = stock_df.at[idx, 'Close']
            close_t_1 = stock_df.at[idx + 1, 'Close']
            close_t_5 = stock_df.at[idx + 5, 'Close']
            close_t_10 = stock_df.at[idx + 10, 'Close']

            ret_1d = (close_t_1 - close_t) / close_t
            ret_5d = (close_t_5 - close_t) / close_t
            ret_10d = (close_t_10 - close_t) / close_t

            results.append({
                'ticker': 'MU',
                'quarter': row['quarter'],
                'earnings_date': row['earnings_date'],
                '1_day_return': ret_1d,
                '5_day_return': ret_5d,
                '10_day_return': ret_10d
            })

        except Exception as e:
            print(f"Error processing {earnings_date}: {e}")

    # Create DataFrame and save
    results_df = pd.DataFrame(results)
    output_file = 'mu_earnings_returns.csv'
    results_df.to_csv(output_file, index=False)
    print(f"Returns calculated and saved to {output_file}")
    print(results_df)

if __name__ == "__main__":
    calculate_returns()
