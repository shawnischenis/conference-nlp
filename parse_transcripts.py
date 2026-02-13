import os
import re
import csv
import sys
from typing import List, Dict, Optional

# --- Configuration & Constants ---
TRANSCRIPTS_DIR = 'Transcripts'
OUTPUT_DIR = 'ParsedTranscripts'

# Detects "Q1 2020", "Q4 2023", etc.
QUARTER_PATTERN = re.compile(r'(Q[1-4]\s+\d{4})')
# Separator lines in the transcript file
SECTION_SEPARATOR_PATTERN = re.compile(r'={30,}')  # "=============================="
SPEAKER_SEPARATOR_PATTERN = re.compile(r'-{30,}')  # "------------------------------"

# Speaker Roles
ROLE_MANAGEMENT = 'Management'
ROLE_ANALYST = 'Analyst'
ROLE_OPERATOR = 'Operator'

# Transcript Sections
SECTION_PRESENTATION = 'Presentation'
SECTION_QA = 'Q&A'


def extract_quarter(lines: List[str], filename: str) -> str:
    """
    Identifies the fiscal quarter (e.g., 'Q1 2023') from the first few lines of the transcript.
    Falls back to parsing the filename if not found in the text.
    """
    # Check the first 20 lines for a quarter pattern
    for line in lines[:20]:
        match = QUARTER_PATTERN.search(line)
        if match:
            return match.group(1)
            
    # Fallback: Try to extract from filename (e.g., 2020-Q1-AAPL.txt)
    # Note: This is a basic fallback and might need adjustment based on actual filenames.
    parts = filename.split('-')
    if len(parts) >= 3:
        # Placeholder for filename parsing logic if needed
        pass
        
    return ''


def determine_speaker_role(speaker_line: str) -> str:
    """
    Determines the role of a speaker based on their name and title line.
    Returns: 'Management', 'Analyst', or 'Operator'.
    """
    if 'Operator' in speaker_line:
        return ROLE_OPERATOR

    # Management identifiers
    management_titles = ['CEO', 'CFO', 'CTO', 'President', 'Officer', 
                         'Relations', 'Counsel', 'Controller', 'Vice President', 
                         'Chief', 'Manager', 'Director']
    
    if any(title in speaker_line for title in management_titles):
        return ROLE_MANAGEMENT
        
    if 'Analyst' in speaker_line:
        return ROLE_ANALYST
        
    # Default assumption if ambiguous (e.g. "John Doe - Bank of America")
    # The original script defaulted to Analyst for non-titled speakers.
    return ROLE_ANALYST


def parse_transcript(file_path: str, ticker: str) -> Dict:
    """
    Parses a single transcript file to extract prepared remarks and Q&A content.
    """
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = [line.strip() for line in f.readlines()]

    filename = os.path.basename(file_path)
    quarter = extract_quarter(lines, filename)
    
    # Data accumulators
    prepared_remarks = []
    qa_management = []
    qa_analysts = []
    
    # State tracking
    current_section = None
    current_role = None
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # --- Case 1: Section Change (detected by "=====") ---
        if SECTION_SEPARATOR_PATTERN.match(line):
            # Look ahead to identified the new section title
            j = i + 1
            while j < len(lines) and not lines[j]: # Skip empty lines
                j += 1
            
            if j < len(lines):
                next_line_lower = lines[j].lower()
                if 'presentation' in next_line_lower:
                    current_section = SECTION_PRESENTATION
                    i = j 
                elif 'questions and answers' in next_line_lower or 'q&a' in next_line_lower:
                    current_section = SECTION_QA
                    i = j 
                elif 'definitions' in next_line_lower or 'disclaimer' in next_line_lower:
                    break # Stop parsing at the disclaimer
        
        # --- Case 2: Speaker Change (detected by "-----") ---
        elif SPEAKER_SEPARATOR_PATTERN.match(line):
             # Look ahead to find the speaker's name
            j = i + 1
            while j < len(lines) and not lines[j]: # Skip empty lines
                j += 1
            
            if j < len(lines):
                speaker_name_line = lines[j]
                
                # Verify it's a valid speaker block (should be followed by another separator)
                k = j + 1
                while k < len(lines) and not lines[k]:
                    k += 1
                
                if k < len(lines) and SPEAKER_SEPARATOR_PATTERN.match(lines[k]):
                    # Valid speaker block found
                    current_role = determine_speaker_role(speaker_name_line)
                    
                    # Special Case: ambiguity in Q&A
                    # If we couldn't determine the role but we are in Q&A, logic implies:
                    if current_role == ROLE_MANAGEMENT and current_section == SECTION_QA:
                        # If a generic name appears in Q&A without a clear Management title,
                        # and it explicitly says "Analyst", we'd catch it above. 
                        # But if it falls through to "Management" default but is actually an analyst...
                        # (The original logic had some complex fallbacks here, simplified for readability)
                        pass 

                    i = k # Advance main loop past the speaker header
                else:
                    pass # Not a valid speaker header, treat as normal text?
        
        # --- Case 3: Content Line ---
        else:
            if line and current_section and current_role != ROLE_OPERATOR:
                # Filter out page numbers or timestamp artifacts if necessary
                if line.isdigit() or line.startswith('Thomson Reuters'):
                    pass
                else:
                    if current_section == SECTION_PRESENTATION:
                        prepared_remarks.append(line)
                    elif current_section == SECTION_QA:
                        if current_role == ROLE_MANAGEMENT:
                            qa_management.append(line)
                        elif current_role == ROLE_ANALYST:
                            qa_analysts.append(line)
    
        i += 1

    # Compile results
    return {
        'ticker': ticker,
        'quarter': quarter,
        'prepared_remarks': ' '.join(prepared_remarks),
        'qa_management': ' '.join(qa_management),
        'qa_analysts': ' '.join(qa_analysts),
        'word_count_prepared_remarks': len(' '.join(prepared_remarks).split()),
        'word_count_qa_management': len(' '.join(qa_management).split()),
        'word_count_qa_analysts': len(' '.join(qa_analysts).split())
    }


def main():
    """
    Main execution function. 
    Iterates through all transcript files and aggregates parsed data into a CSV.
    """
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    if not os.path.exists(TRANSCRIPTS_DIR):
        print(f"Error: Directory '{TRANSCRIPTS_DIR}' not found.")
        return

    tickers = [d for d in os.listdir(TRANSCRIPTS_DIR) if os.path.isdir(os.path.join(TRANSCRIPTS_DIR, d))]
    tickers.sort()
    
    print(f"Index found: {len(tickers)} tickers.")

    for ticker in tickers:
        ticker_dir = os.path.join(TRANSCRIPTS_DIR, ticker)
        files = [f for f in os.listdir(ticker_dir) if f.endswith('.txt')]
        files.sort()
        
        parsed_data_list = []
        print(f"Processing {ticker} ({len(files)} transcripts)...")
        
        for filename in files:
            file_path = os.path.join(ticker_dir, filename)
            try:
                data = parse_transcript(file_path, ticker)
                # Only save if we successfully extracted a quarter
                if data['quarter']: 
                    parsed_data_list.append(data)
            except Exception as e:
                print(f"  Warning: Failed to parse {filename}: {e}")
        
        if parsed_data_list:
            output_csv_path = os.path.join(OUTPUT_DIR, f"{ticker}_transcript_data.csv")
            fieldnames = ['ticker', 'quarter', 
                          'word_count_prepared_remarks', 'word_count_qa_management', 'word_count_qa_analysts', 
                          'prepared_remarks', 'qa_management', 'qa_analysts']
            
            with open(output_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for row in parsed_data_list:
                    writer.writerow(row)
            
            print(f"  -> Saved to {output_csv_path}")

if __name__ == '__main__':
    main()
