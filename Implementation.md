# Implementation Log: The Local Minima

This document tracks the implementation strategy and all subsequent engineering changes for "The Local Minima." It covers Step 0 (Basic Interface), Step 1 (Core Narrative Explorer), and all enhancements made thereafter.

---

## 1. Environment & Project Structure

The architecture is decoupled into a frontend service and a backend service, both living at the **repository root** (see §H for the reorganization details).

- **Virtual Environment:** Python environments and package management are handled exclusively using `uv` (as per project constraints).
- **Directory Layout:**
  ```text
  cosmic-ostriches/                # Repository Root
  ├── project-planning/            # Planning documents & research
  ├── Implementation.md            # This file
  ├── start.sh                     # One-command bootstrapper
  ├── backend/                     # FastAPI Python application
  │   ├── .venv/                   # uv-managed virtual environment (git-ignored)
  │   ├── chroma_db/               # Local ChromaDB persistent vector storage
  │   ├── main.py                  # FastAPI entry point & CORS orchestration
  │   ├── api.py                   # NewsAPI.org fetching logic
  │   ├── ml.py                    # Embedding, reduction, clustering & LLM pipeline
  │   └── requirements.txt         # Frozen PyPI dependencies
  ├── frontend/                    # Next.js React application
  │   ├── src/app/page.tsx         # Home/Search Page
  │   ├── src/app/cluster/page.tsx # Clustering Visualization Page
  │   └── package.json             # Node.js dependencies
  └── prototyping/                 # Archive of earlier prototype work
  ```

---

## 2. Step 0: Basic Interface

We will build the foundational UI using **Next.js** and styled with CSS/Tailwind.

- **Home/Article Search Page (`/`):**
  - A simple, visually premium interface where a user can input a news topic or query (e.g., "Global Warming").
  - On submission, it triggers a call to the backend, which queries NewsAPI.org to fetch recent articles on the topic.
- **Clustering Page (`/cluster`):**
  - Displays the loaded data points.
  - Features a UI control panel allowing the user to select the **Clustering Algorithm**:
    - K-Means (allows specifying `$k$`)
    - Gaussian Mixture Model / GMM (allows specifying `$k$`)
    - HDBSCAN (default fallback if `$k$` is omitted).
  - Integrates **Plotly.js** to visualize the heavily reduced (UMAP) high-dimensional vectors.

_(Note: The Login/Account Page is explicitly excluded from this build phase but the FastAPI router pattern will easily accept auth endpoints later)._

---

## 3. Step 1: News Narrative Explorer (Core Pipeline)

The heavy lifting will occur in the **FastAPI** backend using Python.

### A. Data Retrieval

- We will use the official **NewsAPI.org** API.
- The backend will take the search query from the frontend, hit the NewsAPI endpoints, and extract the JSON response (specifically combining the `title` and `description` to form the context payload).

### B. Vectorization & Database Storage

- We will use the `sentence-transformers` library (using the fast `all-MiniLM-L6-v2` model to ensure it runs comfortably on a laptop).
- The raw text and their corresponding vectors will be saved to a local **ChromaDB** database. This ensures that the articles are persistently stored locally, enabling future features (like "Article Enjoyment Labeler") to run without re-vectorizing or re-fetching from the API.

### C. Dimensionality Reduction & Visualization

- The raw 384-dimensional embeddings are unplottable on the web frontend. The backend will use **UMAP** from `umap-learn` to reduce these down to 2D coordinates (x, y) optimized for semantic mapping.

### D. Clustering

- The backend will take the user's algorithm choice from the UI request:
  - If **K-Means** or **GMM** is selected, `scikit-learn` will be used to assign cluster labels to the vectors based on the user-provided `$k$`.
  - If no input is provided, the backend falls back to `hdbscan`, automatically grouping narratives and isolating noise.
- The backend returns a clean JSON package to the frontend: `[{"title": "...", "url": "...", "x": 0.5, "y": -1.2, "cluster": 1}, ...]`

---

## 4. Execution Sequence

1.  Initialize the Next.js `frontend` app and set up routing/Plotly.
2.  Use `uv` to initialize the `backend` environment and install dependencies (`fastapi`, `uvicorn`, `sentence-transformers`, `scikit-learn`, `umap-learn`, `requests`).
3.  Write the FastAPI Python endpoints tying the ML pipeline together.
4.  Wire the frontend Search Page to hit the backend, compute the ML results, and plot them interactively on the Clustering Page.
5.  Populate the root `README.md` with the requested repository diagram and logical 5-person team division.

---

## 5. Enhancements

### A. Resource Tracker Error Fix

- The `resource_tracker: leaked semaphore objects` warning during Uvicorn shutdown (caused by underlying scikit-learn/joblib threadpools from HDBSCAN/UMAP) will be resolved by gracefully patching the warnings or explicitly closing the multiprocessing tracker on `SIGTERM`.

### B. Cosmetic & UI Upgrades

- **Legend Sizing & Noise Ordering:** The Plotly configuration in `/cluster` will be updated to uniformly push the "Noise" (`-1`) trace to the bottom of the legend and significantly increase the legend font size for readability.
- **Home Page Feed:** The `/` page will be decoupled from instant clustering. Instead, it will feature an interim feed state:
  - It will query a new backend endpoint to fetch articles and embed them.
  - It will rapidly calculate the **Cosine Similarity** between the target search query vector and the article vectors to display a dynamic "Matching Percentage."
  - It will display a stylized vertical list of these headlines + descriptions.
  - A prominent "Cluster Narratives" button will then bridge the user to the `/cluster` visualization.

### C. AI Cluster Summarization

- **Dynamic Narratives:** Once the user calculates their clusters (e.g., K-Means $k=3$), the backend will map the article bodies in each cluster and generate a brief 1-2 sentence AI summary of the narrative structure.
- **Implementation Path:** To remain compliant with strict free-tier/local-execution constraints, the system will execute entirely offline using a lightweight sequence-to-sequence local NLP model (`google/flan-t5-small`) via the HuggingFace `pipeline`. This will run purely on the local CPU alongside `sentence-transformers`.

### D. Source Mapping & Generation Strictness (Phase 2.5)

- **Narrative Sourcing:** Following UI rendering, the system dynamically iterates the datapoints to build a Set of unique journalistic sources (e.g., _BBC News, Reuters_) corresponding to each narrative cluster, explicitly exposing the underlying publisher-bias driving a group's logic.
- **LLM Output Truncation:** To enforce strict analytical constraints against the free-tier Causal LM generation quirks, the raw sequence-output is parsed directly at the UI layer to explicitly terminate at the very first full period character (`.`).

### E. Algorithmic Fundamentals & Cloud AI

- **From-Scratch Clustering (K-Means):** The black-box `scikit-learn` KMeans dependency was formally removed and replaced with a custom-engineered mathematical `CustomKMeans` algorithm running native numpy array broadcasting (Euclidean distances) to execute Lloyd's algorithm natively. GMM remains leveraging `scikit-learn`.
- **Dimensionality Engine (t-SNE vs UMAP):** Integrated `t-SNE` functionally into the UI dropdowns alongside `UMAP`, allowing the user to select whether they want to optimize exclusively for hyper-local cluster density (t-SNE) vs preserving accurate global mathematical distances across narratives (UMAP).
- **Hybrid AI Summarization:** Integrated the Google `google-genai` Python package to explicitly target `gemini-2.5-flash` for high-speed, hyper-deterministic 1-sentence cluster summarizations on the free-tier infrastructure. Operates natively on an environment toggle: if a valid `GEMINI_API_KEY` is missing or the API rate-limits, the backend seamlessly catches the failure and falls back to the heavily-constrained local `distilgpt2` HuggingFace pipeline, automatically lighting up a "Local Mode" warning UI badge in the Next.js dashboard perfectly preventing user interruption.

### F. Vector Caching & Clustering Array

- **Offline Vector Resilience:** Integrated structural fault-tolerance around the primary API ingestion pipeline. When `NewsAPI.org` extraction limits are exhausted (HTTP 429), the FastAPI backend intentionally intercepts the failure block and flips gracefully into `is_offline_cache` mode. It queries entirely from local `ChromaDB` embeddings natively, triggering a high-visibility animated yellow UI Warning Banner telling the user they are viewing cached semantic vectors perfectly preventing runtime disruption.
- **Expansion of non-parametric Manifolds:** Extended the native UI execution state capabilities to encompass two additional non-parametric architectures allowing operation without needing predetermined `$k$` allocations:
  - **Agglomerative Clustering:** Rigged mathematically to default against a strict `0.5` dimensional distance threshold if `$k$` isn't given.
  - **Affinity Propagation:** Explores structure organically utilizing peer message-passing models via rigid deterministic seed protocols.
- **HDBSCAN Fine-Tuning:** Specifically depressed the baseline mathematical volume thresholds for Density-Based mapping (`min_cluster_size=3, min_samples=2`). This greatly enhances algorithmic sensitivity ensuring hyper-dense micro-narratives previously discarded are aggressively extracted from `-1` noise space.

### G. From-Scratch PCA Dimensionality Reduction

- **Custom PCA Implementation:** Removed the `scikit-learn` PCA dependency from the dimensionality reduction pipeline and replaced it with a hand-engineered `CustomPCA` class implemented entirely in NumPy. The algorithm:
  1. Centers the data by subtracting the column-wise mean.
  2. Applies NumPy's `linalg.svd` (more numerically stable than direct eigendecomposition of the covariance matrix at this scale).
  3. Extracts the top `n_components` right singular vectors as principal axes and projects the centered data onto them.
- This makes PCA, alongside the existing `CustomKMeans`, the second from-scratch ML primitive in the pipeline — both running natively with no `scikit-learn` calls.

### H. Repository Reorganization

- **Promotion to Root:** The working implementation, previously developed under `prototyping/prototype-kevin/`, was promoted to the repository root of `cosmic-ostriches/`. All backend and frontend files were copied to the root-level `backend/` and `frontend/` directories respectively.
- **Data Preservation:** The `chroma_db/` vector database and `backend/.env` secrets file were **moved** (not copied) to avoid duplication — preserving all cached article embeddings and API keys in place.
- **Zero Code Changes Required:** Because `ml.py` resolves the ChromaDB path using `os.path.dirname(__file__)` (self-relative), and `start.sh` uses paths relative to its working directory, no source code modifications were needed after the move.
- **Planning Docs Rename:** The planning directory was renamed from `project-protoype-planning/` to `project-planning/` for correctness.
- **README Update:** The root `README.md` was expanded from a placeholder to a full project README incorporating the complete feature list, directory structure, setup instructions, and team division of labor.

### I. Daily Briefing & Advanced Document Retrieval

- **Daily Briefing Mechanism:** Added a dedicated "Daily Briefing" mode alongside the traditional clustering view. This fetches the top 100 US headlines over the past 24 hours via NewsAPI, vectorizes them, and surfaces an accordion-style visual grid highlighting the overarching news themes.
- **Farthest Point Sampling (FPS):** Implemented a custom, pure NumPy version of the FPS algorithm (no scikit-learn). It works by selecting the vector furthest from the global centroid, and iteratively picking subsequent articles that maximize the maximum minimum distance to all already-selected articles. This ensures the 8-10 major "Hero Cards" spanned fundamentally different news domains.
- **Maximal Marginal Relevance (MMR):** Implemented a custom MMR algorithm in NumPy to populate the sub-articles underneath each expanded Hero Card. Rather than pulling the 4 most synonymous articles via standard KNN cosine similarity (which often yields exact syndicate copies of the same wire report), the MMR penalty dynamically selects articles that are highly relevant to the main topic but introduce novel perspectives (maximizing semantic distance among the chosen subset).
