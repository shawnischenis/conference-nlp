import os
import re
import csv
import sys

TRANSCRIPTS_DIR = 'Transcripts'
OUTPUT_DIR = 'ParsedTranscripts'

def parse_transcript(file_path, ticker):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    filename = os.path.basename(file_path)
    
    # Metadata
    quarter = ''
    
    # Content accumulators
    prepared_remarks = []
    qa_management = []
    qa_analysts = []
    
    # State tracking
    current_section = None # 'Presentation', 'Q&A', or None
    current_speaker_type = None # 'Management', 'Analyst', 'Operator', or None
    
    # Regex patterns
    quarter_pattern = re.compile(r'(Q[1-4]\s+\d{4})')
    section_separator = re.compile(r'={30,}')
    speaker_separator = re.compile(r'-{30,}')
    
    # Find Quarter in the first few lines
    for line in lines[:20]:
        match = quarter_pattern.search(line)
        if match:
            quarter = match.group(1)
            break
            
    # Try to extract quarter from filename if not found in text
    # Filename format expected: YYYY-Mon-DD-TICKER.txt or similar
    if not quarter:
         parts = filename.split('-')
         if len(parts) >= 3:
             # This is a fallback and might not give "Q1 2020", but at least a date.
             # Ideally we want the fiscal quarter.
             pass

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Detect Section Changes
        if section_separator.match(line):
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            
            if j < len(lines):
                next_line = lines[j].strip().lower()
                if 'presentation' in next_line:
                    current_section = 'Presentation'
                    i = j 
                elif 'questions and answers' in next_line or 'q&a' in next_line:
                    current_section = 'Q&A'
                    i = j 
                elif 'definitions' in next_line or 'disclaimer' in next_line:
                    break 
        
        # Detect Speaker Changes
        elif speaker_separator.match(line):
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            
            if j < len(lines):
                speaker_line = lines[j].strip()
                
                k = j + 1
                while k < len(lines) and not lines[k].strip():
                    k += 1
                
                if k < len(lines) and speaker_separator.match(lines[k].strip()):
                    speaker_info = speaker_line
                    
                    if 'Operator' in speaker_info:
                        current_speaker_type = 'Operator'
                    # Generalizing Management detection:
                    # Usually company name is mentioned or title implies management.
                    # Simple heuristic: If it's not Operator and not asking a question (Analyst), it's Management?
                    # Better heuristic: Check against ticker or common management titles?
                    # For now, let's assume if it contains the Company Name (Ticker's company) it's management.
                    # But we don't have the full company name easily available.
                    # Let's use the inverse: If 'Analyst' is NOT in the line, and it's not 'Operator', assume Management
                    # NO, Analysts often have "Analyst" in their title line in these transcripts?
                    # Let's look at `parse_mu_transcripts.py`: it used `elif 'Micron' in speaker_info`.
                    # We might need to map Ticker -> Company Name or be smarter.
                    # Or we can treat "analyst" generally.
                    
                    # Heuristic A: If "Analyst" is in the text, it's an analyst.
                    elif 'Analyst' in speaker_info or 'Vice President' not in speaker_info and 'Chief' not in speaker_info and 'CEO' not in speaker_info and 'CFO' not in speaker_info and 'Manager' not in speaker_info and 'Director' not in speaker_info:
                         # This is risky. 
                         # Let's try: Operator is clear.
                         # Analysts usually are listed with their firm.
                         # Management usually has titles like CEO, CFO, VP.
                         
                         if any(title in speaker_info for title in ['CEO', 'CFO', 'CTO', 'President', 'Officer', 'Relations', 'Counsel', 'Controller']):
                             current_speaker_type = 'Management'
                         elif 'Analyst' in speaker_info:
                             current_speaker_type = 'Analyst'
                         else:
                             # Fallback: assume Analyst if not clearly management? Or assume Management?
                             # Let's assume Analyst if it's Q&A and not management.
                             current_speaker_type = 'Analyst'
                    else:
                        current_speaker_type = 'Management'

                    i = k 
                else:
                    pass
        
        else:
            if line and current_section and current_speaker_type != 'Operator':
                if line.isdigit() or line.startswith('Thomson Reuters'):
                    pass
                else:
                    if current_section == 'Presentation':
                        prepared_remarks.append(line)
                    elif current_section == 'Q&A':
                        if current_speaker_type == 'Management':
                            qa_management.append(line)
                        elif current_speaker_type == 'Analyst':
                            qa_analysts.append(line)
        
        i += 1

    prepared_remarks_text = ' '.join(prepared_remarks)
    qa_management_text = ' '.join(qa_management)
    qa_analysts_text = ' '.join(qa_analysts)
    
    def count_words(text):
        return len(text.split())

    return {
        'ticker': ticker,
        'quarter': quarter,
        'prepared_remarks': prepared_remarks_text,
        'qa_management': qa_management_text,
        'qa_analysts': qa_analysts_text,
        'word_count_prepared_remarks': count_words(prepared_remarks_text),
        'word_count_qa_management': count_words(qa_management_text),
        'word_count_qa_analysts': count_words(qa_analysts_text)
    }

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    if not os.path.exists(TRANSCRIPTS_DIR):
        print(f"Directory {TRANSCRIPTS_DIR} not found.")
        return

    tickers = [d for d in os.listdir(TRANSCRIPTS_DIR) if os.path.isdir(os.path.join(TRANSCRIPTS_DIR, d))]
    tickers.sort()
    
    print(f"Found {len(tickers)} tickers.")

    for ticker in tickers:
        ticker_dir = os.path.join(TRANSCRIPTS_DIR, ticker)
        files = [f for f in os.listdir(ticker_dir) if f.endswith('.txt')]
        files.sort()
        
        ticker_data = []
        print(f"Processing {ticker} ({len(files)} files)...")
        
        for filename in files:
            file_path = os.path.join(ticker_dir, filename)
            try:
                data = parse_transcript(file_path, ticker)
                if data['quarter']: # Only add if we successfully parsed the quarter/content
                    ticker_data.append(data)
            except Exception as e:
                print(f"Error processing {filename}: {e}")
        
        if ticker_data:
            output_file = os.path.join(OUTPUT_DIR, f"{ticker}_transcript_data.csv")
            fieldnames = ['ticker', 'quarter', 'word_count_prepared_remarks', 'word_count_qa_management', 'word_count_qa_analysts', 'prepared_remarks', 'qa_management', 'qa_analysts']
            
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for row in ticker_data:
                    writer.writerow(row)
            print(f"Saved {ticker} data to {output_file}")

if __name__ == '__main__':
    main()
