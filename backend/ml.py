import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import chromadb
from umap import UMAP
from sentence_transformers import SentenceTransformer, util
from sklearn.cluster import HDBSCAN, AgglomerativeClustering, AffinityPropagation
from sklearn.mixture import GaussianMixture
from sklearn.manifold import TSNE
from transformers import pipeline
from google import genai
from typing import List, Dict, Any, Optional
import numpy as np
import warnings
from threading import Lock
from transformers import logging as transformers_logging

warnings.filterwarnings("ignore", category=FutureWarning, module="sklearn.*")
warnings.filterwarnings("ignore", category=UserWarning, module="umap.*")
warnings.filterwarnings("ignore", module="transformers.*")
transformers_logging.set_verbosity_error()

# Load the vectorizer model
# all-MiniLM-L6-v2 is selected to balance performance with low compute 
print("Loading model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

print("Loading LLM summarization pipeline (Offline NLP)...")
summarizer = pipeline("text-generation", model="distilgpt2")

# Initialize ChromaDB persistent client locally
CHROMA_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")
os.makedirs(CHROMA_PATH, exist_ok=True)
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma_client.get_or_create_collection(name="news_diversity_v3_collection")

# UMAP relies on Numba's workqueue threading layer in this environment, which
# can abort the process if multiple FastAPI threads enter it concurrently.
_cluster_pipeline_lock = Lock()

def vectorize_and_store(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Takes cleaned articles, checks if they exist in ChromaDB, 
    embeds them if not, and stores them. Returns the full local metadata bundle.
    """
    if not articles:
        return []

    stored_ids = collection.get(ids=[a["id"] for a in articles])["ids"]
    new_articles = [a for a in articles if a["id"] not in stored_ids]

    if new_articles:
        texts_to_embed = [a["embed_text"] for a in new_articles]
        embeddings = model.encode(texts_to_embed).tolist()
        
        ids = [a["id"] for a in new_articles]
        metadatas = [{
            "title": a["title"],
            "url": a.get("url", ""),
            "source": a.get("source", ""),
            "body": a.get("body", ""),
            "category": a.get("category", "General"),
            "publish_date": a.get("publish_date", "")
        } for a in new_articles]
        
        collection.add(
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas,
            documents=texts_to_embed
        )

    return articles

def fetch_vectors(article_ids: List[str]):
    """Fetch stored embeddings directly from ChromaDB."""
    return collection.get(ids=article_ids, include=["embeddings", "metadatas"])

def query_local_database(query_text: str, n_results: int = 50) -> List[Dict[str, Any]]:
    """
    Fallback method: Embeds the search query and searches the local ChromaDB 
    for the semantically closest existing articles when the API fails.
    """
    if collection.count() == 0:
        return []
        
    query_embedding = model.encode([query_text]).tolist()
    
    # Query ChromaDB (returns Dict of lists)
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=min(n_results, collection.count())
    )
    
    articles = []
    if results and results["ids"] and len(results["ids"]) > 0:
        ids_list = results["ids"][0]
        metadatas_list = results["metadatas"][0]
        
        for i, uid in enumerate(ids_list):
            meta = metadatas_list[i]
            articles.append({
                "id": uid,
                "title": meta.get("title", "Unknown"),
                "description": meta.get("description", ""),
                "url": meta.get("url", ""),
                "source": meta.get("source", ""),
                "publish_date": meta.get("publish_date", ""),
                "embed_text": f"{meta.get('title', '')}. {meta.get('description', '')}"
            })
            
    return articles

def compute_similarity_scores(query: str, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Calculates cosine similarity matching-percentages between vector states."""
    if not articles:
        return []
    
    # Do not force convert to PyTorch tensor here so numpy can bridge them safely
    query_emb = model.encode(query)
    
    ids = [a["id"] for a in articles]
    data = collection.get(ids=ids, include=["embeddings"])
    
    if data.get("embeddings") is None or len(data["embeddings"]) == 0:
        for a in articles:
            a["match_score"] = 0
        return articles
        
    # Cast explicitly to float32 to match the model's 32-bit dimension typing
    doc_embs = np.array(data["embeddings"], dtype=np.float32)
    cosine_scores = util.cos_sim(query_emb, doc_embs)[0]
    
    for idx, a in enumerate(articles):
        score = float(cosine_scores[idx]) * 100
        a["match_score"] = round(max(0, min(100, score)), 1)
        
    articles.sort(key=lambda x: x["match_score"], reverse=True)
    return articles

class CustomKMeans:
    def __init__(self, n_clusters=8, max_iter=100, random_state=None):
        self.n_clusters = n_clusters
        self.max_iter = max_iter
        if random_state is not None:
            np.random.seed(random_state)
            
    def fit_predict(self, X):
        if len(X) <= self.n_clusters:
            return np.arange(len(X))
        indices = np.random.choice(X.shape[0], self.n_clusters, replace=False)
        centroids = X[indices].copy()
        
        labels = np.zeros(X.shape[0])
        for _ in range(self.max_iter):
            # Form computationally clean 3D broadcast matrix for bulk Euclidean vector distance comparison
            distances = np.linalg.norm(X[:, np.newaxis] - centroids, axis=2)
            new_labels = np.argmin(distances, axis=1)
            
            if np.array_equal(labels, new_labels):
                break
            labels = new_labels
            
            for k in range(self.n_clusters):
                if np.sum(labels == k) > 0:
                    centroids[k] = np.mean(X[labels == k], axis=0)
                    
        return labels

class CustomPCA:
    """
    From-scratch PCA implementation using numpy SVD.
    Centers the data, computes the covariance matrix, and projects onto 
    the top n_components principal axes via eigendecomposition.
    Mathematically equivalent to sklearn PCA at this scale.
    """
    def __init__(self, n_components: int = 2):
        self.n_components = n_components
        self.components_ = None
        self.mean_ = None
        
    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        # Step 1: Center the data
        self.mean_ = np.mean(X, axis=0)
        X_centered = X - self.mean_
        
        # Step 2: SVD decomposition (numerically more stable than direct eigen on covariance)
        # U: left singular vectors (sample projections)
        # S: singular values
        # Vt: right singular vectors (principal axes / components)
        _, _, Vt = np.linalg.svd(X_centered, full_matrices=False)
        
        # Step 3: Store top n_components principal axes and project
        self.components_ = Vt[:self.n_components]
        return X_centered @ self.components_.T

def process_batch_cluster(
    articles: List[Dict[str, Any]], 
    method: str = "hdbscan", 
    cluster_k: Optional[int] = None,
    dim_reduction: str = "umap"
) -> List[Dict[str, Any]]:
    """
    Fetches embeddings, performs UMAP dimensionality reduction to 2D for the UI,
    and applies the chosen clustering algorithm.
    """
    if not articles:
        return []
    
    # Retrieve
    ids = [a["id"] for a in articles]
    data = collection.get(ids=ids, include=["embeddings", "metadatas"])
    
    if data.get("embeddings") is None or len(data["embeddings"]) == 0:
        return []
    
    embeddings = np.array(data["embeddings"])

    with _cluster_pipeline_lock:
        # Clustering
        labels = []
        if method == "kmeans" and cluster_k:
            k = min(cluster_k, len(embeddings))
            kmeans = CustomKMeans(n_clusters=k, random_state=42)
            labels = kmeans.fit_predict(embeddings)
        elif method == "gmm" and cluster_k:
            k = min(cluster_k, len(embeddings))
            gmm = GaussianMixture(n_components=k, random_state=42)
            labels = gmm.fit_predict(embeddings)
        elif method == "agglomerative":
            k = min(cluster_k, len(embeddings)) if cluster_k else None
            if k:
                agg = AgglomerativeClustering(n_clusters=k)
            else:
                agg = AgglomerativeClustering(n_clusters=None, distance_threshold=0.5)
            labels = agg.fit_predict(embeddings)
        elif method == "affinity":
            aff = AffinityPropagation(random_state=42)
            labels = aff.fit_predict(embeddings)
        else:
            # Fallback to HDBSCAN
            # Works well when k is unknown. tuned to aggressive sensitivity.
            min_cluster = min(len(embeddings), 3)
            if len(embeddings) < 3:
                labels = [0] * len(embeddings) # not enough data to cluster
            else:
                hdb = HDBSCAN(min_cluster_size=min_cluster, min_samples=2)
                labels = hdb.fit_predict(embeddings)

        # Dimensionality Reduction for 2D Plotting
        if dim_reduction == "tsne" and len(embeddings) > 1:
            # Perplexity strictly bound to sample size logic constraints
            perplexity = min(30, max(1, len(embeddings) - 1))
            if perplexity >= len(embeddings):
                perplexity = len(embeddings) - 1
                
            if perplexity < 1:
                reduced_embeddings = np.zeros((len(embeddings), 2))
            else:
                reducer = TSNE(n_components=2, perplexity=perplexity, random_state=42, init='pca', learning_rate='auto')
                reduced_embeddings = reducer.fit_transform(embeddings)
        elif dim_reduction == "pca":
            pca = CustomPCA(n_components=2)
            reduced_embeddings = pca.fit_transform(embeddings)
        else:
            # Fallback to standard UMAP mapping
            n_neighbors = min(15, len(embeddings) - 1)
            if n_neighbors < 2:
                reduced_embeddings = np.zeros((len(embeddings), 2))
            else:
                reducer = UMAP(n_neighbors=n_neighbors, min_dist=0.1, n_components=2, random_state=42)
                reduced_embeddings = reducer.fit_transform(embeddings)

    from models.metrics import compute_article_distances_from_center
    article_distances = compute_article_distances_from_center(embeddings, np.array(labels))

    # Build response points
    results = []
    cluster_texts = {}
    
    # Hybrid Gemini / Local Auto-Summarization Key detection
    gemini_key = os.getenv("GEMINI_API_KEY")
    client = None
    if gemini_key:
        try:
            client = genai.Client(api_key=gemini_key)
        except Exception:
            pass

    used_local_fallback = False if client else True
    
    for idx, article_id in enumerate(ids):
        meta = data["metadatas"][idx]
        cluster_id = int(labels[idx])
        
        if cluster_id not in cluster_texts:
            cluster_texts[cluster_id] = []
            
        t = meta.get("title", "")
        b = meta.get("body", "")
        
        # Chunk logic based on API constraints
        if b:
            chunk = b[:2500] if client else b[:200]
            cluster_texts[cluster_id].append(f"{t}: {chunk}")
        else:
            cluster_texts[cluster_id].append(t)
            
        results.append({
            "id": article_id,
            "title": meta.get("title", "Unknown"),
            "url": meta.get("url", ""),
            "source": meta.get("source", ""),
            "body": meta.get("body", ""),
            "cluster": cluster_id,
            "x": float(reduced_embeddings[idx][0]),
            "y": float(reduced_embeddings[idx][1]),
            "distance_from_center": round(float(article_distances[idx]), 3) if cluster_id != -1 else 0.0
        })
        
    summaries = {}
    cluster_strings = ""
    target_clusters = []
    
    for cluster_id, texts in cluster_texts.items():
        if cluster_id == -1:
            summaries[str(cluster_id)] = "Unclustered noise and outlier narratives."
            continue
        
        # Pass up to 5 full text chunks for AI analysis
        top_texts_str = "\n---\n".join(texts[:5])
        cluster_strings += f"Cluster {cluster_id}:\n{top_texts_str}\n\n"
        target_clusters.append(cluster_id)
        
    summary_generated = False
    
    if client and target_clusters:
        try:
            prompt = f"You are an analytical AI bot. Read the following sets of news reporting grouped by cluster. Synthesize and summarize the main narrative connecting each cluster into a clear, concise paragraph without strict limits. Highlight any notable differences between each cluster. Avoid using the word 'cluster' in your response. Return your response STRICTLY as a valid JSON object where each KEY is the plain cluster number as a string (e.g. \"0\", \"1\", \"2\") and each VALUE is the summary paragraph. Ensure all text values are properly escaped and contain absolutely NO literal newlines. \n\n{cluster_strings}"
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=8192,
                    response_mime_type="application/json"
                )
            )
            
            import json
            json_text = response.text.strip()
            if json_text.startswith("```json"):
                json_text = json_text[7:]
            elif json_text.startswith("```"):
                json_text = json_text[3:]
            if json_text.endswith("```"):
                json_text = json_text[:-3]
                
            batch_summaries = json.loads(json_text.strip())
            
            for cid in target_clusters:
                # Try plain numeric key first ("0"), then fall back to "Cluster 0" format
                summary = (
                    batch_summaries.get(str(cid)) or
                    batch_summaries.get(f"Cluster {cid}")
                )
                summaries[str(cid)] = summary if summary else "Narrative summary unavailable."
            summary_generated = True
        except Exception as api_err:
            print(f"Gemini API Batch Error: {api_err} - Routing individual clusters to local offline model.")
            used_local_fallback = True
            
    if not summary_generated:
        for cid in target_clusters:
            # Only pass a severely truncated subset of the first headline text block for GPT2 logic
            input_text = cluster_texts[cid][0][:100] if cluster_texts.get(cid) else "Global news."
            prompt = f"Summarize the context: {input_text}"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                out = summarizer(
                    prompt, 
                    max_new_tokens=25, 
                    temperature=0.3, 
                    do_sample=True,
                    return_full_text=False,
                    pad_token_id=50256
                )
            generated = out[0]["generated_text"].strip()
            if "\n" in generated: 
                generated = generated.split("\n")[0]
            summaries[str(cid)] = generated
    from models.metrics import compute_narrative_diversity_score
    nds_scores = compute_narrative_diversity_score(embeddings, np.array(labels))
            
    return {
        "points": results, 
        "summaries": summaries,
        "nds_scores": nds_scores,
        "is_local_summary": used_local_fallback
    }

def farthest_point_sampling(embeddings: np.ndarray, k: int, categories: List[str] = None, max_per_category: int = 2) -> List[int]:
    """
    Selects k points from embeddings that are farthest apart.
    Implemented deterministically from scratch to maximize diversity.
    Optionally dynamically enforces categorical ceilings to prevent thematic saturation.
    """
    n = len(embeddings)
    if n <= k:
        return list(range(n))
    
    # 1. Start with the index furthest from the global centroid
    centroid = np.mean(embeddings, axis=0)
    distances_to_centroid = np.linalg.norm(embeddings - centroid, axis=1)
    
    first_selected = int(np.argmax(distances_to_centroid))
    selected = [first_selected]
    
    # Setup categorical limit trackers
    category_counts = {}
    if categories:
        first_cat = categories[first_selected]
        category_counts[first_cat] = 1
        
    # Maintain the minimum distance from each point to the selected set
    min_dist = np.full(n, np.inf)
    
    # 2. Iteratively pick the point that maximizes the minimum distance to existing selected points
    for _ in range(1, k):
        last_selected_emb = embeddings[selected[-1]]
        dist_to_last = np.linalg.norm(embeddings - last_selected_emb, axis=1)
        min_dist = np.minimum(min_dist, dist_to_last)
        
        # We don't want to re-select
        min_dist[selected] = -1.0
        
        # Try to find furthest unmapped boundary adhering to category cap constraints
        sorted_indices = np.argsort(min_dist)[::-1]
        found = False
        
        for candidate in sorted_indices:
            if min_dist[candidate] < 0:
                break # Since properties track descending, -1 denotes exhaustion of usable pools
                
            cat = categories[candidate] if categories else "General"
            
            # Category gating bounds (Hard cap per category)
            if category_counts.get(cat, 0) < max_per_category:
                selected.append(candidate)
                category_counts[cat] = category_counts.get(cat, 0) + 1
                found = True
                break
                
        # If mathematically EVERY remaining far-point violates the thematic cap, 
        # forcefully override the maximum constraint and capture the absolute furthest coordinate
        if not found:
            override_candidate = int(np.argmax(min_dist))
            selected.append(override_candidate)
            if categories:
                override_cat = categories[override_candidate]
                category_counts[override_cat] = category_counts.get(override_cat, 0) + 1
        
    return selected

def maximal_marginal_relevance(query_embedding: np.ndarray, doc_embeddings: np.ndarray, top_k: int, lambda_param: float = 0.5) -> List[int]:
    """
    Retrieves top_k related articles balancing cosine similarity to query (relevance) 
    and dissimilarity to already selected articles (diversity).
    Implemented from scratch using NumPy.
    """
    n = len(doc_embeddings)
    if n == 0:
        return []
    
    target_k = min(top_k, n)
    selected = []
    unselected = list(range(n))
    
    # Compute cosine similarity bounds precisely
    q_norm = np.linalg.norm(query_embedding) + 1e-9
    doc_norms = np.linalg.norm(doc_embeddings, axis=1) + 1e-9
    
    # sim_to_query: shape (n,)
    sim_to_query = np.dot(doc_embeddings, query_embedding) / (doc_norms * q_norm)
    
    for _ in range(target_k):
        if not unselected:
            break
            
        if not selected:
            # First item is purely the most relevant
            best_idx = unselected[np.argmax(sim_to_query[unselected])]
        else:
            # MMR formula
            unselected_embs = doc_embeddings[unselected]
            selected_embs = doc_embeddings[selected]
            
            # sim_to_selected: shape (len(unselected), len(selected))
            un_norms = doc_norms[unselected]
            sel_norms = doc_norms[selected]
            sim_matrix = np.dot(unselected_embs, selected_embs.T) / (un_norms[:, None] * sel_norms[None, :])
            
            # For diversity, we care about the max similarity to ANY already selected doc
            max_sim_to_selected = np.max(sim_matrix, axis=1)
            
            mmr_scores = lambda_param * sim_to_query[unselected] - (1.0 - lambda_param) * max_sim_to_selected
            best_idx_in_unselected = np.argmax(mmr_scores)
            best_idx = unselected[best_idx_in_unselected]
            
        selected.append(best_idx)
        unselected.remove(best_idx)
        
    return selected

def process_daily_gradient(articles: List[Dict[str, Any]], n_main: int = 8, n_related: int = 4) -> List[Dict[str, Any]]:
    """
    Main orchestrator for the backend math of the daily gradient.
    Vectorizes local articles, clusters by FPS, and populates by MMR.
    """
    if not articles:
        return []
        
    # Get all embeddings via collection
    ids = [a["id"] for a in articles]
    data = collection.get(ids=ids, include=["embeddings", "metadatas"])
    
    if data.get("embeddings") is None or len(data["embeddings"]) == 0:
        return []
        
    embeddings = np.array(data["embeddings"])
    
    # Extract bounded metadata
    all_categories = [data["metadatas"][i].get("category", "General") for i in range(len(ids))]
    
    # Run categorical capped FPS
    main_indices = farthest_point_sampling(embeddings, k=min(n_main, len(embeddings)), categories=all_categories)
    
    briefing = []
    
    for m_idx in main_indices:
        main_id = ids[m_idx]
        main_meta = data["metadatas"][m_idx]
        main_emb = embeddings[m_idx]
        
        main_article = {
            "id": main_id,
            "title": main_meta.get("title", ""),
            "body": main_meta.get("body", ""),
            "category": main_meta.get("category", "General"),
            "url": main_meta.get("url", ""),
            "source": main_meta.get("source", ""),
            "publish_date": main_meta.get("publish_date", "")
        }
        
        # We need docs excluding the main article to avoid choosing it again
        # Actually MMR will just not select from unselected docs, but it's easier to just pass everything and 
        # remove the m_idx from the pool manually, or let MMR handle it.
        # But wait, MMR as written takes a document pool. Let's pass the whole pool, then filter it from the return list if it selects itself.
        # Better: pass the pool excluding the main article.
        pool_mask = np.ones(len(embeddings), dtype=bool)
        pool_mask[m_idx] = False
        
        pool_indices = np.where(pool_mask)[0]
        pool_embeddings = embeddings[pool_indices]
        
        if len(pool_embeddings) > 0:
            related_local_indices = maximal_marginal_relevance(
                query_embedding=main_emb,
                doc_embeddings=pool_embeddings,
                top_k=n_related,
                lambda_param=0.6  # Balance relevance and diversity
            )
            
            related_articles = []
            for r_local_idx in related_local_indices:
                global_idx = pool_indices[r_local_idx]
                r_id = ids[global_idx]
                r_meta = data["metadatas"][global_idx]
                related_articles.append({
                    "id": r_id,
                    "title": r_meta.get("title", ""),
                    "body": r_meta.get("body", ""),
                    "category": r_meta.get("category", "General"),
                    "url": r_meta.get("url", ""),
                    "source": r_meta.get("source", ""),
                    "publish_date": r_meta.get("publish_date", "")
                })
        else:
            related_articles = []
            
        briefing.append({
            "main_article": main_article,
            "related_articles": related_articles
        })
        
    return briefing

