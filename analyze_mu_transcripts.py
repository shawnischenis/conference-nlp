import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import numpy as np
import re
import os

# Constants
INPUT_FILE = 'mu_transcript_data.csv'
OUTPUT_FILE = 'mu_transcript_features.parquet'
OUTPUT_CSV = 'mu_transcript_features.csv'
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
        # Use regex to match whole words only
        count += len(re.findall(r'\b' + re.escape(word) + r'\b', text))
    return count

def get_finbert_sentiment(text, tokenizer, model, device):
    if not isinstance(text, str) or not text.strip():
        return {'positive': 0.0, 'negative': 0.0, 'neutral': 0.0}
    
    # Chunking
    tokens = tokenizer(text, return_tensors='pt', padding=True, truncation=True, max_length=512, stride=128, return_overflowing_tokens=True)
    
    input_ids = tokens['input_ids'].to(device)
    attention_mask = tokens['attention_mask'].to(device)
    
    with torch.no_grad():
        outputs = model(input_ids, attention_mask=attention_mask)
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        
    # Average probabilities across chunks
    avg_probs = probs.mean(dim=0).cpu().numpy()
    
    return {
        'positive': avg_probs[0],
        'negative': avg_probs[1],
        'neutral': avg_probs[2]
    }

def main():
    print("Loading data...")
    df = pd.read_csv(INPUT_FILE)
    
    print("Initializing FinBERT...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()
    
    print("Processing transcripts...")
    
    # Initialize new columns
    df['finbert_prepared_remarks_pos'] = 0.0
    df['finbert_prepared_remarks_neg'] = 0.0
    df['finbert_prepared_remarks_neu'] = 0.0
    
    df['finbert_qa_management_pos'] = 0.0
    df['finbert_qa_management_neg'] = 0.0
    df['finbert_qa_management_neu'] = 0.0
    
    df['uncertainty_count_qa_management'] = 0
    df['forward_looking_count_prepared_remarks'] = 0
    df['forward_looking_count_qa_management'] = 0
    
    total_rows = len(df)
    
    for index, row in df.iterrows():
        print(f"Processing row {index + 1}/{total_rows}...")
        
        # Word Counts
        df.at[index, 'uncertainty_count_qa_management'] = count_words_from_list(row['qa_management'], UNCERTAINTY_WORDS)
        df.at[index, 'forward_looking_count_prepared_remarks'] = count_words_from_list(row['prepared_remarks'], FORWARD_LOOKING_WORDS)
        df.at[index, 'forward_looking_count_qa_management'] = count_words_from_list(row['qa_management'], FORWARD_LOOKING_WORDS)
        
        # FinBERT - Prepared Remarks
        sent_pr = get_finbert_sentiment(row['prepared_remarks'], tokenizer, model, device)
        df.at[index, 'finbert_prepared_remarks_pos'] = sent_pr['positive']
        df.at[index, 'finbert_prepared_remarks_neg'] = sent_pr['negative']
        df.at[index, 'finbert_prepared_remarks_neu'] = sent_pr['neutral']
        
        # FinBERT - QA Management
        sent_qa = get_finbert_sentiment(row['qa_management'], tokenizer, model, device)
        df.at[index, 'finbert_qa_management_pos'] = sent_qa['positive']
        df.at[index, 'finbert_qa_management_neg'] = sent_qa['negative']
        df.at[index, 'finbert_qa_management_neu'] = sent_qa['neutral']

    # Z-score of QA Management Length
    # Assuming 'word_count_qa_management' exists from previous step
    if 'word_count_qa_management' in df.columns:
        mean_len = df['word_count_qa_management'].mean()
        std_len = df['word_count_qa_management'].std()
        df['qa_management_length_zscore'] = (df['word_count_qa_management'] - mean_len) / std_len
    else:
        print("Warning: 'word_count_qa_management' column not found. Calculating it now.")
        df['word_count_qa_management'] = df['qa_management'].apply(lambda x: len(str(x).split()))
        mean_len = df['word_count_qa_management'].mean()
        std_len = df['word_count_qa_management'].std()
        df['qa_management_length_zscore'] = (df['word_count_qa_management'] - mean_len) / std_len

    print("Saving to Parquet...")
    # Select numerical features to save
    features_df = df[[
        'ticker', 'quarter',
        'finbert_prepared_remarks_pos', 'finbert_prepared_remarks_neg', 'finbert_prepared_remarks_neu',
        'finbert_qa_management_pos', 'finbert_qa_management_neg', 'finbert_qa_management_neu',
        'uncertainty_count_qa_management',
        'forward_looking_count_prepared_remarks',
        'forward_looking_count_qa_management',
        'qa_management_length_zscore'
    ]]
    
    features_df.to_parquet(OUTPUT_FILE, index=False)
    features_df.to_csv(OUTPUT_CSV, index=False)
    print(f"Successfully saved features to {OUTPUT_FILE} and {OUTPUT_CSV}")

if __name__ == '__main__':
    main()
