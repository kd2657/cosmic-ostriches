# Cosmic Ostriches: The Local Minima
**CS473 — Fundamentals of Machine Learning | NYU, Spring 2026**

**Authors:** Kevin Ding, Wayne Zhang, Haokai Ma, Mohamed Alremeithi, Terence Xu

---

A **News Narrative Explorer** that fetches, vectorizes, reduces, and dynamically clusters the hidden semantic structure behind today's global news. Built as a full-stack Next.js + FastAPI application, it pulls live articles from NewsAPI, embeds them locally using HuggingFace `sentence-transformers`, clusters them with a suite of algorithms, and generates AI-powered narrative summaries via Google Gemini.

## ✨ Core Features

*   **Live Cosine-Similarity Feed:** Real-time semantic relevance scoring for news articles using vector-space distance math.
*   **The Daily Gradient:** A diverse intelligence tab utilizing custom **Farthest Point Sampling (FPS)** and **MMR** to surface unique global narratives.
*   **Multi-Algorithm Clustering:** Interactive 2D mapping of news narratives supporting **HDBSCAN**, **K-Means**, **GMM**, and more.
*   **Flexible Dimensionality Reduction:** Switch between **UMAP**, **t-SNE**, and a custom SVD-based **PCA** for semantic projection.
*   **Hybrid AI Summaries:** Generates concise cluster narratives via **Gemini 2.5 Flash** with a robust local T5-based fallback.
*   **Personalized Recommender:** A preference-driven ranking system that learns from user votes to surface tailored content.
*   **SourceLens Divergence:** Quantitative framing analysis to detect and visualize ideological outliers across news publishers.
*   **Offline Vector Resilience:** Persistent **ChromaDB** storage with "Local Mode" and automatic API fallback for disconnected exploration.

## 📁 Repository Structure

```text
cosmic-ostriches/                # Project Root
├── project-planning/            # Planning Documents & Research
├── Implementation.md            # Technical implementation & Feature Log
├── start.sh                     # One-command application bootstrapper
├── backend/                     # Python FastAPI + ML Pipeline
│   ├── .env                     # Local secrets (do NOT commit)
│   ├── .venv/                   # uv-managed virtual environment
│   ├── chroma_db/               # Local ChromaDB persistent vector storage
│   ├── main.py                  # FastAPI Application Entry Point
│   ├── ml/                      # ML Package (Clustering, PCA, Gradient)
│   ├── routers/                 # API Endpoint Routers
│   ├── models/                  # Internal Math & Metrics package
│   └── requirements.txt         # Frozen PyPI dependencies
├── frontend/                    # Next.js React Application
│   ├── src/app/
│   │   ├── page.tsx             # Home Page (Search & Recommendations)
│   │   └── cluster/page.tsx     # Narrative Clustering Dashboard
│   ├── src/components/          # Modular UI Components (Modals, Blobs)
│   └── package.json             # Node.js dependencies
└── README.md
```

## 🚀 How to Run

### Prerequisites (First-Time Setup)

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
| `NEWSAPI_AI_KEY` | ✅ Yes | [newsapi.ai](https://newsapi.ai) — Main article engine |
| `GEMINI_API_KEY` | ⚪ Optional | [aistudio.google.com](https://aistudio.google.com) — AI summaries |
| `OPENAI_API_KEY` | ⚪ Optional | [platform.openai.com](https://platform.openai.com) — Secondary LLM fallback |

> Without a `GEMINI_API_KEY` or `OPENAI_API_KEY`, the app still runs fully — it falls back to the local `T5-Small` summarizer and shows a "Local Summary Only" badge.

---

### Running the App

**Quick Start (Recommended):** Run both servers with a single command from the project root:
```bash
./start.sh
```
This loads your `.env`, activates the virtual environment, starts both servers simultaneously, and shuts them down cleanly on `Ctrl+C`.

**Manual Method** (requires 2 separate terminals):
```bash
# Terminal 1 — Backend
cd backend && source .venv/bin/activate && export $(grep -v '^#' .env | xargs) && uvicorn main:app --reload

# Terminal 2 — Frontend
cd frontend && npm run dev
```

Once both are running, open **http://localhost:3000** in your browser.

---