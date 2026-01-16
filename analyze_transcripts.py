import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import numpy as np
import re
import os
import glob

INPUT_DIR = 'ParsedTranscripts'
OUTPUT_DIR = 'TranscriptFeatures'
MODEL_NAME = "ProsusAI/finbert"

# Word Lists
UNCERTAINTY_WORDS = [
    'may', 'could', 'might', 'possibly', 'perhaps', 'uncertain', 'risk', 
    'variable', 'fluctuation', 'instability', 'approximate', 'contingency', 
    'depend', 'exposure', 'indefinite', 'volatility'
]

FORWARD_LOOKING_WORDS = [
    'will', 'expect', 'anticipate', 'forecast', 'outlook', 'project', 
    'target', 'plan', 'believe', 'intend', 'estimate', 'future', 'goal', 
    'objective', 'upcoming'
]

def count_words_from_list(text, word_list):
    if not isinstance(text, str):
        return 0
    text = text.lower()
    count = 0
    for word in word_list:
        count += len(re.findall(r'\b' + re.escape(word) + r'\b', text))
    return count

def get_finbert_sentiment(text, tokenizer, model, device):
    if not isinstance(text, str) or not text.strip():
        return {'positive': 0.0, 'negative': 0.0, 'neutral': 0.0}
    
    tokens = tokenizer(text, return_tensors='pt', padding=True, truncation=True, max_length=512, stride=128, return_overflowing_tokens=True)
    
    input_ids = tokens['input_ids'].to(device)
    attention_mask = tokens['attention_mask'].to(device)
    
    with torch.no_grad():
        outputs = model(input_ids, attention_mask=attention_mask)
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        
    avg_probs = probs.mean(dim=0).cpu().numpy()
    
    return {
        'positive': avg_probs[0],
        'negative': avg_probs[1],
        'neutral': avg_probs[2]
    }

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    print("Initializing FinBERT...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)
        model.eval()
    except Exception as e:
        print(f"Error loading model: {e}")
        return

    csv_files = glob.glob(os.path.join(INPUT_DIR, '*_transcript_data.csv'))
    print(f"Found {len(csv_files)} transcript files to process.")
    
    for file_path in csv_files:
        filename = os.path.basename(file_path)
        ticker = filename.split('_')[0]
        output_file_csv = os.path.join(OUTPUT_DIR, f"{ticker}_features.csv")
        
        print(f"Processing {ticker} ({filename})...")
        try:
            df = pd.read_csv(file_path)
            
            # Initialize columns
            for col in ['finbert_prepared_remarks_pos', 'finbert_prepared_remarks_neg', 'finbert_prepared_remarks_neu',
                        'finbert_qa_management_pos', 'finbert_qa_management_neg', 'finbert_qa_management_neu']:
                df[col] = 0.0
                
            for col in ['uncertainty_count_qa_management', 'forward_looking_count_prepared_remarks', 'forward_looking_count_qa_management']:
                df[col] = 0
            
            total_rows = len(df)
            for index, row in df.iterrows():
                if index % 5 == 0:
                   print(f"  Row {index + 1}/{total_rows}")
                   
                # Word Counts
                df.at[index, 'uncertainty_count_qa_management'] = count_words_from_list(row.get('qa_management', ''), UNCERTAINTY_WORDS)
                df.at[index, 'forward_looking_count_prepared_remarks'] = count_words_from_list(row.get('prepared_remarks', ''), FORWARD_LOOKING_WORDS)
                df.at[index, 'forward_looking_count_qa_management'] = count_words_from_list(row.get('qa_management', ''), FORWARD_LOOKING_WORDS)
                
                # FinBERT
                sent_pr = get_finbert_sentiment(row.get('prepared_remarks', ''), tokenizer, model, device)
                df.at[index, 'finbert_prepared_remarks_pos'] = sent_pr['positive']
                df.at[index, 'finbert_prepared_remarks_neg'] = sent_pr['negative']
                df.at[index, 'finbert_prepared_remarks_neu'] = sent_pr['neutral']
                
                sent_qa = get_finbert_sentiment(row.get('qa_management', ''), tokenizer, model, device)
                df.at[index, 'finbert_qa_management_pos'] = sent_qa['positive']
                df.at[index, 'finbert_qa_management_neg'] = sent_qa['negative']
                df.at[index, 'finbert_qa_management_neu'] = sent_qa['neutral']

            # Z-score
            if 'word_count_qa_management' in df.columns:
                 # Check if zero variance
                 std_len = df['word_count_qa_management'].std()
                 if std_len > 0:
                     mean_len = df['word_count_qa_management'].mean()
                     df['qa_management_length_zscore'] = (df['word_count_qa_management'] - mean_len) / std_len
                 else:
                     df['qa_management_length_zscore'] = 0.0
            
            # Select features
            cols_to_keep = [
                'ticker', 'quarter',
                'finbert_prepared_remarks_pos', 'finbert_prepared_remarks_neg', 'finbert_prepared_remarks_neu',
                'finbert_qa_management_pos', 'finbert_qa_management_neg', 'finbert_qa_management_neu',
                'uncertainty_count_qa_management',
                'forward_looking_count_prepared_remarks',
                'forward_looking_count_qa_management',
                'qa_management_length_zscore'
            ]
            
            # Only keep columns that actually exist
            available_cols = [c for c in cols_to_keep if c in df.columns]
            features_df = df[available_cols]
            
            features_df.to_csv(output_file_csv, index=False)
            print(f"Saved features for {ticker} to {output_file_csv}")
            
        except Exception as e:
            print(f"Error processing {filename}: {e}")

if __name__ == '__main__':
    main()
