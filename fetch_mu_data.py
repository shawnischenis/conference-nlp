import yfinance as yf
import pandas as pd

def fetch_micron_data():
    # Define the ticker symbol
    tickerSymbol = 'MU'

    # Get data on this ticker
    tickerData = yf.Ticker(tickerSymbol)

    # Get the historical prices for this ticker
    # Period is from 2016-01-01 to 2020-12-31
    tickerDf = tickerData.history(start='2016-01-01', end='2020-12-31')

    # Save to CSV
    output_file = 'micron_stock_2016_2020.csv'
    tickerDf.to_csv(output_file)
    print(f"Data saved to {output_file}")

if __name__ == "__main__":
    fetch_micron_data()
