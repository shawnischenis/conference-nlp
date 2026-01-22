import os
import glob
import pandas as pd
import numpy as np
import pickle
import re
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity

# --- Configuration ---
TRANSCRIPTS_DIR = 'ParsedTranscripts'
RETURNS_DIR = 'EarningsReturns'
Signals_DIR = 'TranscriptFeatures'
OUTPUT_INDEX = 'rag_index.pkl'
EMBEDDING_MODEL = "text-embedding-3-small"
CHUNK_SIZE_SENTENCES = 7  # Number of sentences per chunk
OVERLAP_SENTENCES = 2     # Overlap between chunks

# Initialize OpenAI Client
# Expecting OPENAI_API_KEY in environment variables
# For this session, we will pass it if not found, but best practice is env var.
try:
    client = OpenAI()
except Exception as e:
    print(f"Error initializing OpenAI client: {e}")
    print("Ensure OPENAI_API_KEY is set.")
    exit(1)

def get_embeddings_batch(texts):
    # OpenAI supports up to 2048 inputs per request (though total tokens limit apply)
    # We will be conservative with batch size
    clean_texts = [t.replace("\n", " ") for t in texts]
    try:
        response = client.embeddings.create(input=clean_texts, model=EMBEDDING_MODEL)
        # Ensure order is preserved
        embeddings = [data.embedding for data in response.data]
        return embeddings
    except Exception as e:
        print(f"Error getting batch embeddings: {e}")
        return [[0.0] * 1536 for _ in texts]

def chunk_text(text, chunk_size=CHUNK_SIZE_SENTENCES, overlap=OVERLAP_SENTENCES):
    if not isinstance(text, str):
        return []
    
    # Simple sentence splitting by period. Could be more robust with nltk/spacy.
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    chunks = []
    if not sentences:
        return chunks
        
    for i in range(0, len(sentences), chunk_size - overlap):
        chunk_sentences = sentences[i:i + chunk_size]
        chunk_text = " ".join(chunk_sentences)
        if len(chunk_text) > 50: # Ignore very short chunks
            chunks.append(chunk_text)
            
    return chunks

def load_data():
    print("Loading data...")
    
    # Load Returns
    returns_files = glob.glob(os.path.join(RETURNS_DIR, '*_returns.csv'))
    returns_df = pd.DataFrame()
    for f in returns_files:
        try:
            df = pd.read_csv(f)
            returns_df = pd.concat([returns_df, df], ignore_index=True)
        except:
            pass
            
    # Load Features (Signals)
    features_files = glob.glob(os.path.join(Signals_DIR, '*_features.csv'))
    features_df = pd.DataFrame()
    for f in features_files:
        try:
            df = pd.read_csv(f)
            features_df = pd.concat([features_df, df], ignore_index=True)
        except:
            pass

    # Load Transcripts
    transcripts_files = glob.glob(os.path.join(TRANSCRIPTS_DIR, '*_transcript_data.csv'))
    transcript_data = []
    
    print(f"Found {len(transcripts_files)} transcript files.")
    
    for f in transcripts_files:
        try:
            df = pd.read_csv(f)
            # Add to list
            transcript_data.append(df)
        except Exception as e:
            print(f"Error reading {f}: {e}")
            
    if not transcript_data:
        print("No transcript data found.")
        return None, None, None
        
    transcripts_df = pd.concat(transcript_data, ignore_index=True)
    
    return transcripts_df, returns_df, features_df

def build_index():
    transcripts_df, returns_df, features_df = load_data()
    
    if transcripts_df is None:
        return

    print("Building Index...")
    rag_data = []
    
    total_rows = len(transcripts_df)
    
    for idx, row in transcripts_df.iterrows():
        print(f"Processing row {idx+1}/{total_rows}: {row.get('ticker')} {row.get('quarter')}")
        
        ticker = row.get('ticker')
        quarter = row.get('quarter')
        
        # Merge Metadata
        # Find matching returns
        ret_row = pd.DataFrame()
        if not returns_df.empty:
             ret_row = returns_df[(returns_df['ticker'] == ticker) & (returns_df['quarter'] == quarter)]
        
        ret_1d = ret_row.iloc[0]['1_day_return'] if not ret_row.empty else None
        ret_5d = ret_row.iloc[0]['5_day_return'] if not ret_row.empty else None
        
        # Find matching features
        feat_row = pd.DataFrame()
        if not features_df.empty:
            feat_row = features_df[(features_df['ticker'] == ticker) & (features_df['quarter'] == quarter)]
            
        # Extract signal metadata
        signals = {}
        if not feat_row.empty:
            for col in feat_row.columns:
                if col not in ['ticker', 'quarter']:
                    signals[col] = feat_row.iloc[0][col]
                    
        # Chunking
        # Prepared Remarks
        pr_text = row.get('prepared_remarks', '')
        pr_chunks = chunk_text(pr_text)
        
        for chunk in pr_chunks:
            rag_data.append({
                'text': chunk,
                'section': 'prepared_remarks',
                'ticker': ticker,
                'quarter': quarter,
                'return_1d': ret_1d,
                'return_5d': ret_5d,
                'signals': signals
            })
            
        # QA Management (most important for tone usually)
        qa_text = row.get('qa_management', '')
        qa_chunks = chunk_text(qa_text)
        
        for chunk in qa_chunks:
             rag_data.append({
                'text': chunk,
                'section': 'qa_management',
                'ticker': ticker,
                'quarter': quarter,
                'return_1d': ret_1d,
                'return_5d': ret_5d,
                'signals': signals
            })

    print(f"Generated {len(rag_data)} chunks. Creating embeddings (this may take a moment)...")
    
    # Batch processing for embeddings could be faster, but simple loop for now
    # Check cost: 10 files * ~50 chunks = 500 chunks. Very cheap.
    
    # Batch processing
    BATCH_SIZE = 100
    for i in range(0, len(rag_data), BATCH_SIZE):
        batch = rag_data[i:i+BATCH_SIZE]
        texts = [item['text'] for item in batch]
        
        if i % 500 == 0:
            print(f"Embedding {i}/{len(rag_data)}")
            
        embeddings = get_embeddings_batch(texts)
        
        for j, embedding in enumerate(embeddings):
            batch[j]['embedding'] = embedding
        
    print("Saving index...")
    with open(OUTPUT_INDEX, 'wb') as f:
        pickle.dump(rag_data, f)
        
    print(f"Index saved to {OUTPUT_INDEX}")

if __name__ == "__main__":
    build_index()
