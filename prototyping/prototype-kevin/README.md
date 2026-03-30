# The Local Minima

A proof-of-concept for an interactive "**News Narrative Explorer**" designed to fetch, vectorize, reduce, and dynamically cluster the complex narratives hidden behind today's global news logic. The Local Minima is a full-stack Next.js and FastAPI application that fetches live articles from NewsAPI, mathematically embeds them locally using HuggingFace `sentence-transformers`, and automatically clusters them using algorithms like HDBSCAN and K-Means. It dynamically calculates cosine-similarity scores to populate localized Article Feeds, and utilizes a lightweight local LLM (`distilgpt2`) to automatically summarize abstract news narratives into single intuitive sentences.

## ✨ Core Features

*   **Live Cosine-Similarity Article Feed:** Searches are decoupled from automatic clustering. Fetching a topic downloads live articles and performs a mathematical Cosine Similarity matrix check against the query, exposing exact "Match Percentage" scores before the user decides to cluster.
*   **Mathematical Narrative Clustering:** Translates the raw text of complex geopolitical news logic into a 2-Dimensional Plotly graph, isolating groups of text by their semantic closeness rather than explicit keyword tagging.
*   **Zero-Cost Local AI Summarization:** Bypasses expensive OpenAI API calls by passing the clustered headline arrays explicitly into a lightweight, local sequence-to-sequence model (`distilgpt2`) via HuggingFace's `pipeline` to dynamically generate a 1-sentence narrative summary describing the logic driving a specific cluster.
*   **Media Publisher Source Mapping:** Explicitly iterates across the embedded datasets to reconstruct and list the precise media outlets (e.g., *BBC News, Reuters*) comprising each narrative bias, ensuring source-level transparency. 

## 📁 Repository Structure

```text
prototype-kevin/               # Project Root
├── project-protoype-planning/ # Comprehensive Planning Documents & Research
│   ├── outline.md             
│   ├── research.md            
│   ├── constraints.md         
│   └── prototype-planning.md  
├── Implementation.md          
├── start.sh                   # Native Application Bootstrapper
├── backend/                   # Python FastAPI Machine Learning Pipeline
│   ├── .venv/                 # uv-managed virtual environment
│   ├── chroma_db/             # Local ChromaDB persistent vector storage
│   ├── main.py                # FastAPI endpoints & CORS orchestration
│   ├── api.py                 # NewsAPI.org data retrieval
│   ├── ml.py                  # Embedding, Reduction, Clustering, and Local LLM Pipeline
│   └── requirements.txt       # Frozen PyPI dependencies
└── frontend/                  # Next.js React Application
    ├── public/                # Static assets
    ├── src/app/
    │   ├── page.tsx           # Home Page (Cosine Similarity Feed & Physics Engine)
    │   ├── globals.css        # Tailwind directives
    │   ├── layout.tsx         # Next.js Application wrapper
    │   └── cluster/page.tsx   # Visual Clustering Results (Plotly.js + AI Subtext)
    ├── package.json           # Node.js dependencies
    └── tailwind.config.ts     # Styling Configuration
```

## 🚀 How to Run

Because the architecture decouples the frontend logic from the backend machine learning compute, both servers must be running simultaneously.

### 1. API Configuration
1. Register for an educational/developer key at [NewsAPI.org](https://newsapi.org).
2. Create an environment file: `cp backend/.env.example backend/.env`
3. Paste your key into `backend/.env`.

### 2. The Easy Way (Startup Script)
Simply execute the provided terminal runner. It will load your API key, activate the virtual environment, start both the React interface and Python pipeline simultaneously, and shut them cleanly when you type `Ctrl+C`.
```bash
./start.sh
```

### 3. The Manual Way
If you prefer isolated terminals:
*   **Backend:** `cd backend && source .venv/bin/activate && export $(grep -v '^#' .env | xargs) && uvicorn main:app --reload`
*   **Frontend:** `cd frontend && npm run dev`

---

## 👥 Proposed Division of Labor (5 Students)

Because the project fuses modern web technologies with heavy natural language processing (NLP), the labor is horizontally distributed so that all five students contribute significantly to the Machine Learning logic while simultaneously owning a distinct layer of the full-stack architecture.

### Student 1: Machine Learning & Frontend UX
*   **Machine Learning:** Fine-tuning the dimensionality reduction (UMAP) logic to properly spread visual outliers, ensuring the arrays graph intuitively.
*   **Architecture:** Lead the Next.js foundation, manage the Plotly data rendering pipeline, and style the 2D cluster maps and interactive physics layouts.

### Student 2: Machine Learning & Backend API Orchestration
*   **Machine Learning:** Experiment with the optimal clustering algorithms (HDBSCAN vs K-Means) and analyze parameter thresholds (e.g. `min_cluster_size`).
*   **Architecture:** Maintain the core Python FastAPI integration, structured error fallback, CORS middleware, and handle all asynchronous payload distribution to the Javascript client.

### Student 3: Machine Learning & Vector Infrastructure
*   **Machine Learning:** Manage the Python `sentence-transformers` vectorization pipeline, specifically dealing with tokenization, document embeddings, and the exact vector dimensions (`384` for `MiniLM`).
*   **Architecture:** Own the setup, schema, and raw data queries for `ChromaDB` to ensure historical vectors aren't redundantly cached, acting as the primary data safety buffer.

### Student 4: Machine Learning & External Integrations
*   **Machine Learning:** Establish the raw mathematical evaluation logic, calculating the exact PyTorch Cosine Similarity matrix representing the distance between a raw Search Query and the historical Embeddings.
*   **Architecture:** Handle the direct integration with NewsAPI.org (including API key abstraction, pagination requests, and structural alignment for the ML layer).

### Student 5: Machine Learning & Local AI NLP
*   **Machine Learning:** Architect the local HuggingFace `pipeline` inference logic, selecting and optimizing lightweight open-source large language models (e.g., `distilgpt2`) to execute directly on the server's CPU.
*   **Architecture:** Implement the strict natural language truncation parsing inside the frontend loops to effectively cap and format the local LLM generation strings securely within the UI constraints.
