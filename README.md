# Cosmic Ostriches: The Local Minima
**CS473 — Fundamentals of Machine Learning | NYU, Spring 2026**

**Authors:** Kevin Ding, Wayne Zhang, Haokai Ma, Mohamed Alremeithi, Terence Xu

---

A **News Narrative Explorer** that fetches, vectorizes, reduces, and dynamically clusters the hidden semantic structure behind today's global news. Built as a full-stack Next.js + FastAPI application, it pulls live articles from NewsAPI, embeds them locally using HuggingFace `sentence-transformers`, clusters them with a suite of algorithms, and generates AI-powered narrative summaries via Google Gemini.

## ✨ Core Features

*   **Live Cosine-Similarity Article Feed:** Searches are decoupled from clustering. Fetching a topic downloads live articles and performs a mathematical Cosine Similarity matrix check against the query, exposing exact "Match Percentage" scores before the user decides to cluster.
*   **Multi-Algorithm Narrative Clustering:** Translates the raw text of complex news into a 2D Plotly scatter plot by semantic closeness. Supports **HDBSCAN** (auto-detect), **K-Means** (custom from-scratch implementation), **GMM**, **Agglomerative**, and **Affinity Propagation**.
*   **Flexible Dimensionality Reduction:** Choose between **UMAP** (global structure), **t-SNE** (local density), and **PCA** (custom from-scratch SVD implementation) for the 2D projection.
*   **Hybrid AI Narrative Summaries:** Uses Google **Gemini 2.5 Flash** (free tier) to generate paragraph-length cluster summaries in a single batched API call. Gracefully falls back to a local `distilgpt2` pipeline if no key is configured or the quota is exhausted — with a visible "Local Summary Only" badge in the UI.
*   **Offline Vector Caching:** All fetched articles are persistently embedded and stored in a local **ChromaDB** vector database. If the NewsAPI quota is exhausted, the system automatically falls back to semantically searching the local cache — with a visible animated warning banner in the UI.
*   **Media Publisher Source Mapping:** Lists the precise media outlets (e.g., *BBC News, Reuters*) comprising each narrative cluster for source-level transparency.
*   **Backend-Ready UI Gating:** The search input is automatically disabled with a "Warming up AI vector models..." placeholder until the Python backend finishes loading its ML models — preventing premature fetch errors.

## 📁 Repository Structure

```text
cosmic-ostriches/                # Project Root
├── project-planning/            # Planning Documents & Research
├── Implementation.md            # Technical implementation log
├── start.sh                     # One-command application bootstrapper
├── backend/                     # Python FastAPI + ML Pipeline
│   ├── .env                     # Local secrets (do NOT commit)
│   ├── .env.example             # Template for required environment variables
│   ├── .venv/                   # uv-managed virtual environment (git-ignored)
│   ├── chroma_db/               # Local ChromaDB persistent vector storage
│   ├── main.py                  # FastAPI endpoints & CORS orchestration
│   ├── api.py                   # NewsAPI.org data retrieval
│   ├── ml.py                    # Embedding, Reduction, Clustering & LLM Pipeline
│   └── requirements.txt         # Frozen PyPI dependencies
├── frontend/                    # Next.js React Application
│   ├── public/                  # Static assets
│   ├── src/app/
│   │   ├── page.tsx             # Home Page (Cosine Similarity Feed & Physics Engine)
│   │   ├── globals.css          # Global styles
│   │   ├── layout.tsx           # Next.js Application wrapper
│   │   └── cluster/page.tsx     # Visual Clustering Dashboard (Plotly.js + AI Summaries)
│   ├── package.json             # Node.js dependencies
│   └── next.config.ts           # Next.js configuration
└── prototyping/                 # Archive of earlier prototype work
```

## 🚀 How to Run

### Prerequisites (First-Time Setup)

> [!IMPORTANT]
> Complete these steps once before running for the first time.

**1. Install system dependencies**
- [Python 3.11+](https://www.python.org/downloads/)
- [Node.js 18+](https://nodejs.org/) (includes `npm`)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) — the Python package manager used by this project:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

**2. Set up the Python virtual environment**
```bash
cd backend
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

**3. Install frontend dependencies**
```bash
cd frontend
npm install
```

**4. Configure API keys**
```bash
cp backend/.env.example backend/.env
```
Then open `backend/.env` and fill in your keys (see table below).

| Variable | Required | Where to get it |
|---|---|---|
| `NEWSAPI_KEY` | ✅ Yes | Free key at [newsapi.org](https://newsapi.org) |
| `GEMINI_API_KEY` | ⚪ Optional | Free key at [aistudio.google.com](https://aistudio.google.com) — enables AI summaries |

> [!NOTE]
> Without a `GEMINI_API_KEY`, the app still runs fully — it falls back to the local `distilgpt2` summarizer and shows a "Local Summary Only" badge.

---

### Running the App

**The easy way (recommended):** Run both servers with a single command from the project root:
```bash
./start.sh
```
This loads your `.env`, activates the virtual environment, starts both servers simultaneously, and shuts them down cleanly on `Ctrl+C`.

**The manual way** (if you prefer isolated terminals):
```bash
# Terminal 1 — Backend
cd backend && source .venv/bin/activate && export $(grep -v '^#' .env | xargs) && uvicorn main:app --reload

# Terminal 2 — Frontend
cd frontend && npm run dev
```

Once both are running, open **http://localhost:3000** in your browser.

---

## 👥 Division of Labor (5 Students)

All five students contribute to the shared Machine Learning core while owning a distinct layer of the full-stack architecture.

### Student 1: ML & Frontend UX
*   **Machine Learning:** Fine-tuning dimensionality reduction algorithms (UMAP, t-SNE, PCA) to ensure semantic clusters render intuitively in 2D space.
*   **Architecture:** Lead the Next.js foundation, manage the Plotly data rendering pipeline, and style the cluster maps, interactive physics particle layouts, and all animated UI components.

### Student 2: ML & Backend API Orchestration
*   **Machine Learning:** Experiment with and tune the full clustering suite — HDBSCAN sensitivity (`min_cluster_size`, `min_samples`), K-Means convergence logic, and Agglomerative distance thresholds.
*   **Architecture:** Maintain the FastAPI integration layer, structured error fallback chains, CORS middleware, and the `is_offline_cache` status propagation to the frontend.

### Student 3: ML & Vector Infrastructure
*   **Machine Learning:** Manage the `sentence-transformers` embedding pipeline — tokenization, `all-MiniLM-L6-v2` model configuration, and vector dimensionality (`384-dim`).
*   **Architecture:** Own the ChromaDB schema, persistent vector storage, semantic fallback queries, and the cosine-similarity scoring system against search queries.

### Student 4: ML & External Integrations
*   **Machine Learning:** Build and evaluate the from-scratch Custom K-Means (Lloyd's algorithm via NumPy broadcasting) and Custom PCA (SVD-based decomposition) implementations.
*   **Architecture:** Handle the NewsAPI.org integration — API key abstraction, request pagination, error handling, and structural article normalization for the ML layer.

### Student 5: ML & AI Summarization
*   **Machine Learning:** Architect the hybrid AI summarization pipeline — Gemini 2.5 Flash batched JSON inference, dynamic token budget scaling, and the local `distilgpt2` offline fallback.
*   **Architecture:** Implement the frontend summary rendering, "Local Summary Only" badge logic, UI backend-readiness health polling, and the auto-dismissing offline cache warning banner.