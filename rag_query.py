import os
import pickle
import pandas as pd
import numpy as np
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity
import re
import argparse
import json

# --- Configuration ---
INDEX_FILE = 'rag_index.pkl'
EMBEDDING_MODEL = "text-embedding-3-small"
GENERATION_MODEL = "gpt-4o-mini"
TOP_K = 10

# Initialize OpenAI Client
try:
    client = OpenAI()
except Exception as e:
    print(f"Error initializing OpenAI client: {e}")
    print("Ensure OPENAI_API_KEY is set.")
    exit(1)

def load_index():
    if not os.path.exists(INDEX_FILE):
        print(f"Index file {INDEX_FILE} not found. Run rag_indexer.py first.")
        return None
    with open(INDEX_FILE, 'rb') as f:
        return pickle.load(f)

def get_embedding(text):
    text = text.replace("\n", " ")
    try:
        return client.embeddings.create(input=[text], model=EMBEDDING_MODEL).data[0].embedding
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return [0.0] * 1536

def interpret_query(query):
    """
    Uses LLM to extract structured filters from the natural language query.
    Returns a dictionary of filters and the core semantic search query.
    """
    system_prompt = """
    You are a query parser for an earnings call RAG system.
    Extract filters and the core search text from the user's query.
    
    Available Metadata Filters:
    - ticker (e.g., AAPL)
    - quarter (e.g., Q2 2023)
    - section (prepared_remarks, qa_management)
    - return_1d_min (float, e.g., -0.05 for -5%)
    - return_1d_max (float)
    
    Output JSON format:
    {
        "filters": {
            "ticker": "AAPL" or null,
            "quarter": "Q2 2023" or null,
            "section": "qa_management" or null,
            "return_1d_min": -0.05 or null,
            "return_1d_max": null
        },
        "search_query": "negative tone signal language"
    }
    """
    
    try:
        response = client.chat.completions.create(
            model=GENERATION_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content) # JSON parsing
    except Exception as e:
        print(f"Error interpreting query: {e}")
        return {"filters": {}, "search_query": query}

def filter_data(data, filters):
    filtered_data = []
    for item in data:
        # Ticker Filter
        if filters.get('ticker') and item['ticker'] != filters['ticker']:
            continue
            
        # Quarter Filter
        if filters.get('quarter') and item['quarter'] != filters['quarter']:
            continue
            
        # Section Filter
        if filters.get('section') and item['section'] != filters['section']:
            continue
            
        # Return Filters
        r1d = item['return_1d']
        if r1d is not None:
            if filters.get('return_1d_min') is not None and r1d < filters['return_1d_min']:
                continue
            if filters.get('return_1d_max') is not None and r1d > filters['return_1d_max']:
                continue
        elif filters.get('return_1d_min') is not None or filters.get('return_1d_max') is not None:
             # If filter requires return data but item has none, skip it
             continue
             
        filtered_data.append(item)
    return filtered_data

def search(query):
    data = load_index()
    if not data:
        return

    print(f"Interpreting query: '{query}'...")
    parsed = interpret_query(query)
    filters = parsed.get('filters', {})
    search_text = parsed.get('search_query', query)
    
    print(f"Filters: {filters}")
    print(f"Semantic Query: '{search_text}'")
    
    # 1. Filter
    filtered_data = filter_data(data, filters)
    print(f"Found {len(filtered_data)} potential chunks after filtering.")
    
    if not filtered_data:
        print("No matching data found with current filters.")
        return

    # 2. Rank by Embedding Similarity
    query_embedding = get_embedding(search_text)
    
    # Calculate similarities
    # Optimization: Convert filtered_data embeddings to matrix if large, but list loop is okay for <10k chunks
    
    similarities = []
    for i, item in enumerate(filtered_data):
        sim = cosine_similarity([query_embedding], [item['embedding']])[0][0]
        similarities.append((sim, item))
        
    # Sort
    similarities.sort(key=lambda x: x[0], reverse=True)
    top_results = similarities[:TOP_K]
    
    # 3. Generate Answer
    context_text = ""
    for score, item in top_results:
        context_text += f"\n---\n[Ticker: {item['ticker']}, Quarter: {item['quarter']}, Return 1D: {item['return_1d']}]\n{item['text']}\n"
        
    print("\ngenerating answer...")
    
    system_prompt = f"""
    You are a financial analyst assistant. 
    Answer the user's question based ONLY on the provided context chunks from earnings calls.
    If the context doesn't answer the question, say so.
    Cite specific quotes where possible.
    """
    
    try:
        response = client.chat.completions.create(
            model=GENERATION_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context:\n{context_text}\n\nQuestion: {query}"}
            ]
        )
        print("\n=== ANSWER ===\n")
        print(response.choices[0].message.content)
        print("\n==============")
        
    except Exception as e:
        print(f"Error generating answer: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='RAG Query Interface')
    parser.add_argument('query', type=str, help='The natural language query')
    args = parser.parse_args()
    
    search(args.query)
