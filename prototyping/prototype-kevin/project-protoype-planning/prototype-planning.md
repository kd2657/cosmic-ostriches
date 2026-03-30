# Project Planning and Research Documentation: The Local Minima (Revised)

**Aim:** Address key architectural and machine learning research questions to scaffold "The Local Minima," an interactive news narrative explorer. This document serves as a persistent reference point for both human developers and AI assistants throughout the project's development cycle.

---

## 1. News API/Source Selection

Evaluating the primary source of news data is critical, balancing cost, commercial viability, and data quality.

*   **NewsData.io**
    *   **Pros:** Generous free tier (200 credits/day), allows commercial use on the free plan, provides access to latest, crypto, and market news. 
    *   **Cons:** Real-time data is delayed by ~12 hours on the free tier; no historical data access without paid plans.
    *   **Verdict:** Strong Candidate for Production/Commercial Viability on a budget. It removes the legal grey area of using developer-only APIs in deployed applications.
*   **NewsAPI.org**
    *   **Pros:** Extremely popular, easy to use, massive community support and straightforward documentation.
    *   **Cons:** The free tier (100 requests/day) is strictly limited to localhost development and testing. Articles have a 24-hour delay.
    *   **Verdict:** Good for initial, local sandbox testing, but fundamentally restrictive for any public-facing commercial deployment.

**Recommendation (Updated):** Proceed with **NewsAPI.org** (as elaborated in Section 5) because the strict educational-use constraint mitigates its commercial blockers, allowing you to leverage its unparalleled ease-of-use and dense English source catalog.

---

## 2. Infrastructure & Stack Architecture

For a data-heavy, machine-learning-centric application in 2025, decoupling the frontend user interface from the backend ML processing is the industry standard.

### Frontend: Next.js (React / TypeScript)
*   **Why:** Next.js provides the best-in-class framework for dynamic, responsive web applications. It handles routing and provides excellent UI libraries (like TailwindCSS and Shadcn UI) which will be crucial for making the "Clustering Page" and the diverse score visualizers feel premium and snappy without crashing.

### Backend: FastAPI (Python)
*   **Why:** FastAPI is explicitly designed for high-performance Python backends. Because "The Local Minima" relies heavily on Python-based machine learning (vectorization, clustering algorithms from scikit-learn, etc.), the backend must be Python.
*   **Advantage over Flask:** FastAPI's native asynchronous support means it can handle multiple simultaneous ML inference requests (like embedding generation or UMAP reduction) without blocking the thread, which is critical for a smooth user experience.

### Database Strategy (Local Phase)
The system requires both standard relational data (user accounts, saved preferences) and high-dimensional vector data (article embeddings).

*   **Vector Datastores:** 
    *   **Recommended: ChromaDB.** It is built specifically for local, developer-friendly embedding storage in Python. It abstracts away the complex indexing of libraries like FAISS and handles both metadata (article titles, publication dates, source names) and the vectors themselves in one unified local database.
    *   **Alternative: DuckDB.** For more rigorous analytical querying on tabular data alongside vectors, DuckDB provides blistering speed locally. However, for sheer ease-of-use with LLM/embedding workflows, ChromaDB is the prevailing standard for prototypes.
*   **Relational Storage:** Use a local **SQLite** database via SQLAlchemy or SQLModel in the FastAPI backend to handle user models securely without the overhead of a full PostgreSQL container during the prototyping phase.

---

## 3. Machine Learning & Data Pipeline Strategy

The core feature—the News Narrative Explorer—requires a highly specific ML pipeline.

### Vectorization & Embedding Models
To compute similarity and narrative differences, articles must be converted to dense vector representations.
*   **Model Selection:** The `sentence-transformers` library is the ideal choice.
    *   *Option A (High Speed):* `all-MiniLM-L6-v2`. Extremely fast, lightweight, and capable of running locally on CPU. Ideal for rapid prototyping.
    *   *Option B (High Quality):* `all-mpnet-base-v2`. Provides richer semantic understanding, which is crucial for nuanced tasks like the "Cross-Source Contradiction Finder."
*   **Data Preparation:** Embed a concatenated string of the `[Headline] + [First Paragraph]` rather than the whole article, as full articles often exceed context limits and dilute the core narrative focus.

### Similarity Metrics
*   **Cosine Similarity:** The absolute standard for text embeddings. You care about the *direction* (the semantic meaning) of the vectors, not their *magnitude* (which can be influenced arbitrarily by article length).

### Dimensionality Reduction (For Visualization)
Visualizing 384+ dimensional vectors on a 2D/3D web interface requires reduction.
*   **UMAP (Uniform Manifold Approximation and Projection):** This is the mandatory choice for modern embedding visualization. 
    *   **Why:** Unlike **PCA** (which is merely linear and misses complex topic clusters) and **t-SNE** (which gets local clusters right but destroys the meaning of global distances between different clusters), **UMAP** preserves both the local clustering of identical news stories AND the global relationships between broad topics (e.g., keeping "Tech" clusters somewhat near "Science" clusters, but far from "Sports").

### Clustering Algorithms
The application needs to group articles covering the "same event."
*   **Challenge:** The number of news events (clusters) on any given day is completely unpredictable. Therefore, algorithms that require you to specify $k$ (the number of clusters) upfront, like **K-Means**, are inappropriate.
*   **Recommended: HDBSCAN (Hierarchical DBSCAN).** 
    *   **Why:** It is an advanced density-based clustering algorithm. It automatically discovers the number of clusters, and crucially, it actively identifies **noise** (articles that don't fit into any major narrative), gracefully omitting them rather than forcing them into unrelated clusters.
*   **Event Centroid (for Influence Score):** Once HDBSCAN identifies a cluster, computing the centroid (mean vector of the cluster) natively supports your planned "Source Influence Score" and "Narrative Diversity Score."

### Visualization Libraries
*   **Plotly.js:** The most pragmatic choice for the frontend. It has built-in zooming, panning, and hovering interactivity, and can effortlessly render thousands of points in web browsers. While **D3.js** offers more bespoke control, it has a massive learning curve; Plotly will deliver the "Clustering Page" in a fraction of the time with near-peer aesthetic quality.

---

## 4. Addressing Advanced and Unconfirmed Features

*   **Cross-Source Contradiction Finder:** Calculate the distance between articles belonging to the *same* HDBSCAN cluster. The pair with the lowest cosine similarity within a tightly bound cluster represents the highest narrative divergence on the exact same event.
*   **Article Enjoyment Labeler:** This frames a *Classification* problem. A simple Support Vector Machine (SVM) or Logistic Regression model trained on standard user-labeled data (Enjoyed = 1, Did Not Enjoy = 0), operating on top of the text embeddings, is sufficient to predict probabilities for new, unseen articles.

---

## 5. API Reliability and Source Range (Addendum: English Focus & Educational Use)

While all three original providers offer substantial global source counts, utility for English-only content varies significantly, especially when considering the project's **educational-use only** constraint and the priority on developer ease-of-use outlined in Section 1:

*   **NewsData.io:** Although it boasts massive language diversity (89 languages), it still tracks tens of thousands of reliable English publications. It is cost-effective, but its API can be slightly less streamlined for absolute beginners compared to older market standards.
*   **NewsAPI.org:** With a narrower global focus (14 languages), a significantly higher percentage of its 150,000+ sources are English publications. It is widely considered the gold standard for English news reliability and is notoriously easy to use with excellent documentation. Previously disregarded due to strict commercial prohibitions on its free tier, the new **educational use** constraint completely unlocks this API for the prototype.

*Conclusion:* Given the pivot to purely educational use, **NewsAPI.org** is now the firmly recommended choice. It perfectly satisfies the constraints for free deployment, highly concentrated English-language data, and exceptional developer ease-of-use.

---

## 6. Data Retrieval & Vectorization Analysis (Addendum)

Comparing the two leading API candidates regarding developer experience and text processing pipelines:

*   **Ease of Use:** Both APIs use standard REST endpoints returning JSON arrays. **NewsAPI.org** is universally praised for having the most straightforward query structure and extremely clean documentation, making it the fastest to integrate for a beginner. **NewsData.io** is also relatively easy but features a strictly paginated query structure that requires slightly more boilerplate code to handle properly. 
*   **Type of Data Retrieved:** Both APIs return metadata (Title, Creator, Publish Date, Source) and snippet content. Neither provides the full-text article body on their free tiers.
    *   *NewsAPI.org:* Returns `title`, `description`, and a `content` field that is strictly truncated to roughly 200 characters on the free tier.
    *   *NewsData.io:* Returns `title`, `description`, and a highly truncated `content` field.
*   **Ease of Vectorization:** Because neither API offers full-text without requiring custom web scraping of the source URLs, the vectorization strategy is identical for both: you must concatenate the `[Title] + [Description]` fields to form the semantic representation of the article. Because processing standard JSON strings is uniform across both APIs, the *ease of vectorization* is identical (a simple dictionary key extraction before feeding the string to `sentence-transformers`).

*Conclusion:* Since vectorization effort and data richness are practically identical on their free tiers, **NewsAPI.org** wins this specific comparison purely on its superior, frictionless developer experience.

---

## 7. PyTorch vs. Scikit-learn for Clustering (Addendum)

Regarding the use of PyTorch instead of scikit-learn for the clustering pipelines (specifically K-Means and Gaussian Mixture Models):

*   **Scikit-learn (Recommended for Prototype Constraints):** Scikit-learn is extremely stable, essentially free (as it runs purely on standard CPUs with standard Python libraries), and handles both K-Means and GMM out-of-the-box perfectly for datasets that fit in memory. It perfectly aligns with the project constraint of running locally on a decently powerful laptop without risking memory freezing/crashing under complex neural network compilation.
*   **PyTorch (Not Advisable for Prototyping):** While PyTorch enables immense GPU acceleration for deep learning, applying it to standard clustering tasks like K-Means or GMM involves significant custom implementation (there are no robust, built-in PyTorch equivalents to `sklearn.cluster.KMeans`). It introduces unnecessary dependencies and higher risk of crashing on local hardware due to VRAM limitations or CUDA mismatches, violating the primary stability constraint.

*Conclusion:* Since the project prioritizes stability and local/free-tier execution over massive scale speed, **scikit-learn** is strongly advised over PyTorch for this specific task.

---

## 8. Constraint Alignment & Updated Architecture

The recently introduced project constraints impact previous ML assumptions:
1.  **Stability over Aesthetics:** Reinforces the decision to use **Plotly.js** and **Next.js**; they provide robust, battle-tested standard components compared to custom D3.js setups.
2.  **Free/Low-cost Execution:** Reinforces the selection of **NewsAPI.org** (excellent free tier for educational apps) and **ChromaDB/SQLite** (free, local, no cloud VM required). It also ensures the app can comfortably deploy to educational tiers on Vercel/Render without needing GPU instances.
3.  **UI-Driven Clustering Algorithms:** The UX constraints mandate user-selectable **K-Means** and **Gaussian Mixture Models (GMM)** in the UI. The FastAPI backend will compute these dynamically based on the user's `$k$` parameter. However, per the updated constraints, if the user explicitly chooses not to specify a $k$ value, the application will robustly default to **HDBSCAN**.

---

## 9. Feedback and Next Steps

> [!IMPORTANT]
> **Human Input Required:** Please review the following architecture points before code execution begins:

1.  **API Finalization:** Given the new educational-use constraint, and the conclusion that NewsAPI.org provides identical vectorization capability but superior developer ease-of-use, do you formally approve pivoting to **NewsAPI.org** as the primary data source?
2.  **Clustering Flow:** Does the hybrid approach—using K-Means/GMM when the user wants to specify clusters ($k$), but defaulting to HDBSCAN when they don't—fully satisfy your UI and ML expectations?
3.  **Constraint Check:** Does the pivot back to `scikit-learn` for K-Means and GMM align with your stability vs. functionality goals, knowing it avoids the overhead of PyTorch?
4.  **Tech Stack Approval:** Do you approve of a decoupled architecture (Next.js frontend + FastAPI Python backend)? It will require running two servers during local development but scales easily onto platforms like Render/Vercel.
5.  **Database Storage:** Do you approve using ChromaDB locally for vector storage to facilitate immediate, easy-to-iterate development runs?
