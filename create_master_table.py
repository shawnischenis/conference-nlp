import os
import csv
import re

def create_master_table():
    transcripts_dir = 'Transcripts'
    output_file = 'earnings_master_table.csv'
    
    # Regex to find Quarter info like "Q1 2016", "Fourth Quarter 2019", etc.
    # Adjusting regex to be flexible enough to catch common variations
    quarter_pattern = re.compile(r'(Q[1-4]|First|Second|Third|Fourth)\s+Quarter\s+(\d{4})|(Q[1-4])\s+(\d{4})', re.IGNORECASE)

    table_data = []

    for ticker in os.listdir(transcripts_dir):
        ticker_path = os.path.join(transcripts_dir, ticker)
        if os.path.isdir(ticker_path):
            for filename in os.listdir(ticker_path):
                if filename.endswith('.txt'):
                    file_path = os.path.join(ticker_path, filename)
                    
                    # Extract earnings date from filename (YYYY-Mon-DD-TICKER.txt)
                    # Assuming format is consistent: 2016-Dec-21-MU.txt
                    parts = filename.split('-')
                    if len(parts) >= 3:
                        earnings_date = f"{parts[0]}-{parts[1]}-{parts[2]}"
                    else:
                        earnings_date = "Unknown"

                    quarter = "Unknown"
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            # Read first 20 lines
                            for _ in range(20):
                                line = f.readline()
                                if not line:
                                    break
                                match = quarter_pattern.search(line)
                                if match:
                                    # Extract the full matched string or construct it
                                    quarter = match.group(0)
                                    break
                    except Exception as e:
                        print(f"Error reading {file_path}: {e}")

                    table_data.append({
                        'ticker': ticker,
                        'quarter': quarter,
                        'earnings_date': earnings_date,
                        'transcript_path': os.path.abspath(file_path)
                    })

    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['ticker', 'quarter', 'earnings_date', 'transcript_path']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for row in table_data:
            writer.writerow(row)

    print(f"Master table created at {output_file}")

if __name__ == "__main__":
    create_master_table()
