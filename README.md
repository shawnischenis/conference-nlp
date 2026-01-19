# Earnings Call Transcript Analysis

This project provides a generalized pipeline for analyzing earnings call transcripts to extract linguistic features (sentiment, uncertainty, Q&A length) and correlate them with post-earnings stock returns.

## Project Structure

The workflow consists of four main stages:
1.  **Data Fetching**: `fetch_stock_data.py` - Fetches historical stock data for companies found in the `Transcripts/` directory.
2.  **Parsing**: `parse_transcripts.py` - Parses raw text transcripts into structured sections (Presentation, Q&A Management, Q&A Analysts).
3.  **Feature Extraction**: `analyze_transcripts.py` - Uses FinBERT and Loughran-McDonald dictionaries to extract sentiment and uncertainty metrics.
4.  **Returns Calculation**: `calculate_returns.py` - Computes 1-day, 5-day, and 10-day post-earnings returns.

## Installation

1.  Clone the repository.
2.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1.  **Prepare Transcripts**: Place your raw transcript files in the `Transcripts/{TICKER}/` directory.
2.  **Run the Pipeline**:
    ```bash
    python3 fetch_stock_data.py
    python3 parse_transcripts.py
    python3 analyze_transcripts.py
    python3 calculate_returns.py
    ```
3.  **Analysis**:
    *   Open `industryEDA-2.ipynb` to view the exploratory data analysis and visualizations.

## Key Findings

Based on the analysis performed in `industryEDA-2.ipynb`, we observed significant relationships between transcript features and stock performance:

*   **Uncertainty & Returns**: Companies with **higher uncertainty** in the Management Q&A section tended to exhibit **weaker post-earnings price movements**. This suggests that market participants penalize ambiguity or lack of confidence from management.
*   **Q&A Length & Returns**: **Shorter Management Q&A sections** were associated with **weaker post-earnings movements**. A possible interpretation is that brief answers may signal a lack of detail or transparency, which investors view negatively, or conversely, that there was less "good news" to expound upon.

## Future Work

There are several avenues for extending this research:

*   **Granular Sentiment Analysis**: Differentiate between "Management" and "Analyst" sentiment more strictly to see if analyst tone is a leading indicator.
*   **Topic Modeling**: Apply LDA or other topic modeling techniques to identify *specific* topics (e.g., "Supply Chain", "AI", "Guidance") that drive uncertainty.
*   **Sector Benchmarking**: Normalize features against sector averages to account for industry-specific baselines (e.g., Biotech is naturally more uncertain than Utilities).
*   **Intraday Data**: Use minute-level price data to capture immediate market reactions during the call itself.