# Implementation Plan: The Local Minima (PoC Prototype)

This document outlines the implementation strategy for the initial proof-of-concept for "The Local Minima." Based on the updated constraints and research, it covers Step 0 (Basic Interface) and Step 1 (Core Narrative Explorer), omitting user accounts for now but leaving the architecture flexible for their later addition.

---

## 1. Environment & Project Structure

The project will reside entirely within the `prototype-kevin` directory. The architecture is decoupled into a frontend service and a backend service.

*   **Virtual Environment:** Python environments and package management will be handled exclusively using `uv` (as per user constraints).
*   **Directory Layout:**
    ```text
    prototype-kevin/
    ├── project-protoype-planning/ # Documentation (Already populated)
    ├── backend/                   # FastAPI Python application
    │   ├── .venv/                 # uv-managed virtual environment
    │   ├── chroma_db/             # Local ChromaDB persistent vector storage
    │   ├── main.py                # FastAPI entry point
    │   ├── api.py                 # NewsAPI.org fetching logic
    │   ├── ml.py                  # Sentence-transformers, UMAP, Clustering
    │   └── requirements.txt       # Dependencies
    ├── frontend/                  # Next.js React application
    │   ├── src/app/page.tsx       # Home/Search Page
    │   ├── src/app/cluster/page.tsx # Clustering Visualization Page
    │   └── package.json           # Node.js dependencies
    └── Implementation.md          # This file
    ```

---

## 2. Step 0: Basic Interface

We will build the foundational UI using **Next.js** and styled with CSS/Tailwind.

*   **Home/Article Search Page (`/`):**
    *   A simple, visually premium interface where a user can input a news topic or query (e.g., "Global Warming").
    *   On submission, it triggers a call to the backend, which queries NewsAPI.org to fetch recent articles on the topic.
*   **Clustering Page (`/cluster`):**
    *   Displays the loaded data points.
    *   Features a UI control panel allowing the user to select the **Clustering Algorithm**:
        *   K-Means (allows specifying `$k$`)
        *   Gaussian Mixture Model / GMM (allows specifying `$k$`)
        *   HDBSCAN (default fallback if `$k$` is omitted).
    *   Integrates **Plotly.js** to visualize the heavily reduced (UMAP) high-dimensional vectors.

*(Note: The Login/Account Page is explicitly excluded from this build phase but the FastAPI router pattern will easily accept auth endpoints later).*

---

## 3. Step 1: News Narrative Explorer (Core Pipeline)

The heavy lifting will occur in the **FastAPI** backend using Python.

### A. Data Retrieval
*   We will use the official **NewsAPI.org** API.
*   The backend will take the search query from the frontend, hit the NewsAPI endpoints, and extract the JSON response (specifically combining the `title` and `description` to form the context payload).

### B. Vectorization & Database Storage
*   We will use the `sentence-transformers` library (using the fast `all-MiniLM-L6-v2` model to ensure it runs comfortably on a laptop).
*   The raw text and their corresponding vectors will be saved to a local **ChromaDB** database. This ensures that the articles are persistently stored locally, enabling future features (like "Article Enjoyment Labeler") to run without re-vectorizing or re-fetching from the API.

### C. Dimensionality Reduction & Visualization
*   The raw 384-dimensional embeddings are unplottable on the web frontend. The backend will use **UMAP** from `umap-learn` to reduce these down to 2D coordinates (x, y) optimized for semantic mapping.

### D. Clustering
*   The backend will take the user's algorithm choice from the UI request:
    *   If **K-Means** or **GMM** is selected, `scikit-learn` will be used to assign cluster labels to the vectors based on the user-provided `$k$`.
    *   If no input is provided, the backend falls back to `hdbscan`, automatically grouping narratives and isolating noise.
*   The backend returns a clean JSON package to the frontend: `[{"title": "...", "url": "...", "x": 0.5, "y": -1.2, "cluster": 1}, ...]`

---

## 4. Execution Sequence

1.  Initialize the Next.js `frontend` app and set up routing/Plotly.
2.  Use `uv` to initialize the `backend` environment and install dependencies (`fastapi`, `uvicorn`, `sentence-transformers`, `scikit-learn`, `umap-learn`, `requests`).
3.  Write the FastAPI Python endpoints tying the ML pipeline together.
4.  Wire the frontend Search Page to hit the backend, compute the ML results, and plot them interactively on the Clustering Page.
5.  Populate the root `README.md` with the requested repository diagram and logical 5-person team division.
