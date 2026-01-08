import os
import re
import csv

TRANSCRIPT_DIR = '/Users/shawnchen/Downloads/conference-nlp-main/Transcripts/MU'
OUTPUT_FILE = 'mu_transcript_data.csv'

def parse_transcript(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    filename = os.path.basename(file_path)
    
    # Metadata
    ticker = 'MU'
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
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Detect Section Changes
        if section_separator.match(line):
            # Check the next meaningful line to identify the section
            # Look ahead a few lines to find the section title
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            
            if j < len(lines):
                next_line = lines[j].strip()
                if 'Presentation' in next_line:
                    current_section = 'Presentation'
                    i = j # Skip to the section title
                elif 'Questions and Answers' in next_line:
                    current_section = 'Q&A'
                    i = j # Skip to the section title
                elif 'Definitions' in next_line or 'Disclaimer' in next_line:
                    break # End of relevant content
        
        # Detect Speaker Changes
        elif speaker_separator.match(line):
            # The format is usually:
            # ----------------...
            # Speaker Name, Company - Title [id]
            # ----------------...
            
            # Look ahead to find speaker info
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            
            if j < len(lines):
                speaker_line = lines[j].strip()
                
                # Check if it's actually a speaker line (sometimes it's just a separator)
                # Speaker lines usually have a [number] at the end or are just a name
                # But sometimes the separator is just a separator.
                # Let's check if the line after the speaker line is another separator
                
                k = j + 1
                while k < len(lines) and not lines[k].strip():
                    k += 1
                
                if k < len(lines) and speaker_separator.match(lines[k].strip()):
                    # Valid speaker block
                    speaker_info = speaker_line
                    
                    if 'Operator' in speaker_info:
                        current_speaker_type = 'Operator'
                    elif 'Micron' in speaker_info:
                        current_speaker_type = 'Management'
                    else:
                        current_speaker_type = 'Analyst'
                    
                    i = k # Move past the second separator
                else:
                    # Not a speaker block, maybe just a separator in text?
                    # Treat as content if we are in a section
                    pass
        
        else:
            # Content Processing
            if line and current_section and current_speaker_type != 'Operator':
                # Skip lines that look like page numbers or garbage
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

    # Join text
    prepared_remarks_text = ' '.join(prepared_remarks)
    qa_management_text = ' '.join(qa_management)
    qa_analysts_text = ' '.join(qa_analysts)
    
    # Calculate stats
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
    files = [f for f in os.listdir(TRANSCRIPT_DIR) if f.endswith('.txt')]
    files.sort()
    
    all_data = []
    
    print(f"Found {len(files)} transcripts.")
    
    for filename in files:
        file_path = os.path.join(TRANSCRIPT_DIR, filename)
        print(f"Processing {filename}...")
        try:
            data = parse_transcript(file_path)
            all_data.append(data)
        except Exception as e:
            print(f"Error processing {filename}: {e}")

    # Write to CSV
    fieldnames = ['ticker', 'quarter', 'word_count_prepared_remarks', 'word_count_qa_management', 'word_count_qa_analysts', 'prepared_remarks', 'qa_management', 'qa_analysts']
    
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_data:
            writer.writerow(row)
            
    print(f"Successfully wrote data to {OUTPUT_FILE}")

if __name__ == '__main__':
    main()
