from flask import Flask, request, jsonify, render_template_string
import os
import sys

# Add current directory to path to ensure we can import rag_query
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rag_query import query_rag

app = Flask(__name__)

# --- Embedded Frontend (HTML/CSS/JS) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Earnings RAG</title>
    <style>
        :root {
            --bg-color: #f8f9fa;
            --card-bg: #ffffff;
            --text-color: #333;
            --accent-color: #2563eb;
            --border-color: #e5e7eb;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            min-height: 100vh;
        }

        .container {
            width: 100%;
            max_width: 800px;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            gap: 2rem;
        }

        h1 {
            font-size: 1.5rem;
            font-weight: 600;
            margin: 0;
            text-align: center;
            color: #111;
        }

        .search-box {
            display: flex;
            gap: 0.5rem;
        }

        input[type="text"] {
            flex: 1;
            padding: 0.75rem 1rem;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            font-size: 1rem;
            outline: none;
            transition: border-color 0.2s;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }

        input[type="text"]:focus {
            border-color: var(--accent-color);
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
        }

        button {
            padding: 0.75rem 1.5rem;
            background-color: var(--accent-color);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 500;
            cursor: pointer;
            transition: background-color 0.2s;
        }

        button:hover {
            background-color: #1d4ed8;
        }

        button:disabled {
            background-color: #93c5fd;
            cursor: not-allowed;
        }

        #results {
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        .answer-card {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }

        .answer-header {
            font-size: 0.875rem;
            color: #6b7280;
            margin-bottom: 1rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 600;
        }

        .markdown-body {
            line-height: 1.6;
        }

        .context-section {
            margin-top: 2rem;
            border-top: 1px solid var(--border-color);
            padding-top: 1rem;
        }

        .context-title {
            font-size: 0.875rem;
            font-weight: 600;
            color: #4b5563;
            margin-bottom: 1rem;
        }

        .context-item {
            background: #f9fafb;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 0.75rem;
            font-size: 0.875rem;
        }

        .context-meta {
            display: flex;
            gap: 0.75rem;
            font-size: 0.75rem;
            color: #6b7280;
            margin-bottom: 0.5rem;
            font-weight: 500;
        }

        .tag {
            background: #e5e7eb;
            padding: 2px 6px;
            border-radius: 4px;
        }

        .loading {
            text-align: center;
            color: #6b7280;
            display: none;
        }
        
        /* Markdown styles */
        .markdown-body p { margin-bottom: 1em; }
        .markdown-body ul { padding-left: 1.5em; margin-bottom: 1em; }
        .markdown-body li { margin-bottom: 0.5em; }

    </style>
</head>
<body>
    <div class="container">
        <h1>Earnings RAG</h1>
        
        <div class="search-box">
            <input type="text" id="queryInput" placeholder="Ask a question about earnings calls..." onkeydown="if(event.key === 'Enter') submitQuery()">
            <button onclick="submitQuery()" id="searchBtn">Ask</button>
        </div>

        <div id="loading" class="loading">Analyzing transcripts...</div>
        
        <div id="results"></div>
    </div>

    <!-- Minimal Markdown Parser -->
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>

    <script>
        async function submitQuery() {
            const query = document.getElementById('queryInput').value.trim();
            if (!query) return;

            const btn = document.getElementById('searchBtn');
            const loading = document.getElementById('loading');
            const resultsDiv = document.getElementById('results');

            btn.disabled = true;
            loading.style.display = 'block';
            resultsDiv.innerHTML = '';

            try {
                const response = await fetch('/query', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ query: query }),
                });

                const data = await response.json();

                if (data.error) {
                    resultsDiv.innerHTML = `<div class="answer-card" style="color: red;">Error: ${data.error}</div>`;
                } else {
                    renderResults(data);
                }

            } catch (error) {
                resultsDiv.innerHTML = `<div class="answer-card" style="color: red;">Network Error: ${error.message}</div>`;
            } finally {
                btn.disabled = false;
                loading.style.display = 'none';
            }
        }

        function renderResults(data) {
            const resultsDiv = document.getElementById('results');
            
            // Filters Used
            let filtersHtml = '';
            if (data.filters && Object.keys(data.filters).length > 0) {
                const activeFilters = Object.entries(data.filters)
                    .filter(([_, v]) => v !== null)
                    .map(([k, v]) => `<span class="tag">${k}: ${v}</span>`)
                    .join('');
                if (activeFilters) {
                    filtersHtml = `<div style="margin-bottom: 1rem; font-size: 0.8rem; color: #666;">Filters: ${activeFilters}</div>`;
                }
            }

            // Answer
            const answerHtml = marked.parse(data.answer);

            // Context
            let contextHtml = '';
            if (data.context && data.context.length > 0) {
                const items = data.context.slice(0, 3).map(item => `
                    <div class="context-item">
                        <div class="context-meta">
                            <span>${item.ticker}</span>
                            <span>${item.quarter}</span>
                            <span>Return: ${(item.return_1d * 100).toFixed(1)}%</span>
                        </div>
                        <div>${item.text}</div>
                    </div>
                `).join('');
                
                contextHtml = `
                    <div class="context-section">
                        <div class="context-title">Sources</div>
                        ${items}
                    </div>
                `;
            }

            resultsDiv.innerHTML = `
                ${filtersHtml}
                <div class="answer-card">
                    <div class="answer-header">Answer</div>
                    <div class="markdown-body">${answerHtml}</div>
                </div>
                ${contextHtml}
            `;
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/query', methods=['POST'])
def query_api():
    data = request.json
    query = data.get('query')
    if not query:
        return jsonify({"error": "No query provided"}), 400
    
    try:
        result = query_rag(query)
        if "error" in result:
             return jsonify(result), 500
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Run on port 5001 to avoid macOS AirPlay conflict on 5000
    app.run(debug=True, host='0.0.0.0', port=5001)
