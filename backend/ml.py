import os
import sys
import warnings
from threading import Lock
from typing import Any, Dict, List, Optional

import chromadb
import numpy as np
from google import genai
from sentence_transformers import util
from sklearn.cluster import (AffinityPropagation, AgglomerativeClustering, HDBSCAN)
from sklearn.mixture import GaussianMixture
from sklearn.manifold import TSNE
from transformers import logging as transformers_logging
from transformers import pipeline
from umap import UMAP

from model_manager import ModelManager

# Setup path for internal imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Suppress noisy model-loading warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="sklearn.*")
warnings.filterwarnings("ignore", category=UserWarning, module="umap.*")
warnings.filterwarnings("ignore", module="transformers.*")
transformers_logging.set_verbosity_error()

# Singleton model manager — created immediately, but models load in background
model_manager = ModelManager()

# Initialize ChromaDB persistent client locally
CHROMA_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")
os.makedirs(CHROMA_PATH, exist_ok=True)
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma_client.get_or_create_collection(name="news_diversity_v3_collection")

# UMAP relies on Numba's workqueue threading layer in this environment, which
# can abort the process if multiple FastAPI threads enter it concurrently.
_cluster_pipeline_lock = Lock()

# Sentiment/Narrative Logic Constants
TONE_NEUTRAL_THRESHOLD = 0.10
STABILITY_MIXED_THRESHOLD = 0.03
STABILITY_POLARIZED_THRESHOLD = 0.15


def _get_model():
    """Proxy for the singleton model manager's vectorizer."""
    if not model_manager.model:
        # If not loaded yet, force synchronous load (safe due to singleton)
        model_manager.initialize()
    return model_manager.model


def _get_summarizer():
    """Proxy for the singleton model manager's local NLP pipeline."""
    return model_manager.summarizer


def _classify_cluster_tone(mean_polarity: float) -> str:
    if mean_polarity > TONE_NEUTRAL_THRESHOLD:
        return "Positive"
    if mean_polarity < -TONE_NEUTRAL_THRESHOLD:
        return "Negative"
    return "Neutral"


def _classify_cluster_stability(variance: float) -> str:
    if variance < STABILITY_MIXED_THRESHOLD:
        return "Stable"
    if variance < STABILITY_POLARIZED_THRESHOLD:
        return "Mixed"
    return "Highly Polarized"


def _compute_cluster_sentiment_stats(cluster_polarities: Dict[int, List[float]]) -> Dict[str, Dict[str, Any]]:
    stats = {}
    for cluster_id, polarities in cluster_polarities.items():
        if cluster_id == -1 or not polarities:
            continue

        mean_polarity = float(np.mean(polarities))
        variance = float(np.var(polarities))
        stats[str(cluster_id)] = {
            "tone": _classify_cluster_tone(mean_polarity),
            "stability": _classify_cluster_stability(variance),
            "mean_polarity": round(mean_polarity, 3),
            "polarity_variance": round(variance, 3),
            "article_count": len(polarities),
        }

    return stats

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
        embeddings = _get_model().encode(texts_to_embed).tolist()
        
        ids = [a["id"] for a in new_articles]
        metadatas = [{
            "title": a.get("title") or "",
            "url": a.get("url") or "",
            "source": a.get("source") or "",
            "country": a.get("country") or "",
            "body": a.get("body") or "",
            "category": a.get("category") or "General",
            "publish_date": a.get("publish_date") or ""
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
        
    query_embedding = _get_model().encode([query_text]).tolist()
    
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
                "body": meta.get("body", ""),
                "url": meta.get("url", ""),
                "source": meta.get("source", ""),
                "publish_date": meta.get("publish_date", ""),
                "embed_text": f"{meta.get('title', '')}. {meta.get('body', '') or meta.get('description', '')}"
            })
            
    return articles

def compute_similarity_scores(query: str, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Calculates cosine similarity matching-percentages between vector states."""
    if not articles:
        return []
    
    # Do not force convert to PyTorch tensor here so numpy can bridge them safely
    query_emb = _get_model().encode(query)
    
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

def _get_cluster_labels(embeddings: np.ndarray, method: str, cluster_k: Optional[int]) -> np.ndarray:
    """Internal helper to apply clustering algorithm."""
    if method == "kmeans" and cluster_k:
        k = min(cluster_k, len(embeddings))
        return CustomKMeans(n_clusters=k, random_state=42).fit_predict(embeddings)
    elif method == "gmm" and cluster_k:
        k = min(cluster_k, len(embeddings))
        return GaussianMixture(n_components=k, random_state=42).fit_predict(embeddings)
    elif method == "agglomerative":
        k = min(cluster_k, len(embeddings)) if cluster_k else None
        agg = AgglomerativeClustering(n_clusters=k) if k else AgglomerativeClustering(n_clusters=None, distance_threshold=0.5)
        return agg.fit_predict(embeddings)
    elif method == "affinity":
        return AffinityPropagation(random_state=42).fit_predict(embeddings)
    else:
        min_cluster = min(len(embeddings), 3)
        if len(embeddings) < 3:
            return np.zeros(len(embeddings), dtype=int)
        return HDBSCAN(min_cluster_size=min_cluster, min_samples=2).fit_predict(embeddings)

def _get_reduced_embeddings(embeddings: np.ndarray, dim_reduction: str) -> np.ndarray:
    """Internal helper for 2D dimensionality reduction."""
    if dim_reduction == "tsne" and len(embeddings) > 1:
        perplexity = min(30, max(1, len(embeddings) - 1))
        reducer = TSNE(n_components=2, perplexity=perplexity, random_state=42, init='pca', learning_rate='auto')
        return reducer.fit_transform(embeddings)
    elif dim_reduction == "pca":
        return CustomPCA(n_components=2).fit_transform(embeddings)
    else:
        n_neighbors = min(15, len(embeddings) - 1)
        if n_neighbors < 2:
            return np.zeros((len(embeddings), 2))
        return UMAP(n_neighbors=n_neighbors, min_dist=0.1, n_components=2, random_state=42).fit_transform(embeddings)

def _generate_narrative_summaries(cluster_texts: Dict[int, List[str]], client: Optional[genai.Client], target_clusters: List[int]) -> tuple[Dict[str, Any], bool]:
    """Internal helper to generate summaries using Gemini, OpenAI, or local fallback."""
    summaries = {}
    cluster_strings = ""
    for cluster_id in cluster_texts:
        if cluster_id == -1:
            summaries["-1"] = "Unclustered noise and outlier narratives."
            continue
        if cluster_id in target_clusters:
            top_texts_str = "\n---\n".join(cluster_texts[cluster_id][:5])
            cluster_strings += f"Cluster {cluster_id}:\n{top_texts_str}\n\n"

    summary_generated = False
    used_local_fallback = False if client else True

    if client and target_clusters:
        try:
            prompt = (
                f"You are an analytical AI bot. Read the following sets of news reporting grouped by narrative. "
                f"Provide a short title and a strict 2-sentence summary for each narrative. "
                f"The first sentence should summarize the core narrative. "
                f"The second sentence MUST explicitly focus on what makes this particular narrative different from the others. "
                f"Avoid using the word 'cluster' in your response. "
                f"Return your response STRICTLY as a valid JSON object where each KEY is the plain narrative number as a string (e.g. \"0\", \"1\", \"2\") "
                f"and each VALUE is a nested object containing two string fields: \"title\" and \"summary\". "
                f"Ensure all text values are properly escaped and contain absolutely NO literal newlines. \n\n{cluster_strings}"
            )
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    temperature=0.3, max_output_tokens=8192, response_mime_type="application/json"
                )
            )
            import json
            json_text = response.text.strip()
            if "```json" in json_text: json_text = json_text.split("```json")[1].split("```")[0].strip()
            elif "```" in json_text: json_text = json_text.split("```")[1].split("```")[0].strip()
            elif "{" in json_text and "}" in json_text:
                json_text = json_text[json_text.find("{"):json_text.rfind("}")+1]
            
            batch_summaries = json.loads(json_text)
            for cid in target_clusters:
                summary = batch_summaries.get(str(cid)) or batch_summaries.get(f"Cluster {cid}") or batch_summaries.get(f"Narrative {cid}")
                summaries[str(cid)] = summary if summary else "Narrative summary unavailable."
            summary_generated = True
        except Exception as e:
            print(f"Gemini Error: {e}")

    if not summary_generated:
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and target_clusters:
            try:
                from openai import OpenAI
                import json
                openai_client = OpenAI(api_key=openai_key)
                prompt = (
                    f"You are an analytical AI bot. Read the following sets of news reporting grouped by narrative. "
                    f"Provide a short title and a strict 2-sentence summary for each narrative. "
                    f"The first sentence should summarize the core narrative. "
                    f"The second sentence MUST explicitly focus on what makes this particular narrative different from the others. "
                    f"Avoid using the word 'cluster' in your response. "
                    f"Return your response STRICTLY as a valid JSON object where each KEY is the plain narrative number as a string (e.g. \"0\", \"1\", \"2\") "
                    f"and each VALUE is a nested object containing two string fields: \"title\" and \"summary\". "
                    f"Ensure all text values are properly escaped and contain absolutely NO literal newlines. \n\n{cluster_strings}"
                )
                response = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=2048,
                    response_format={"type": "json_object"}
                )
                json_text = response.choices[0].message.content.strip()
                batch_summaries = json.loads(json_text)
                for cid in target_clusters:
                    summary = batch_summaries.get(str(cid)) or batch_summaries.get(f"Cluster {cid}") or batch_summaries.get(f"Narrative {cid}")
                    summaries[str(cid)] = summary if summary else "Narrative summary unavailable."
                summary_generated = True
                used_local_fallback = False
                print("Used OpenAI fallback for summaries.")
            except Exception as e:
                print(f"OpenAI Error: {e}")

    if not summary_generated:
        used_local_fallback = True
        summarizer = _get_summarizer()
        for cid in target_clusters:
            input_text = cluster_texts[cid][0][:100] if cluster_texts.get(cid) else "Global news."
            prompt = f"Summarize the context: {input_text}"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                out = summarizer(prompt, max_new_tokens=25, temperature=0.3, do_sample=True, return_full_text=False, pad_token_id=50256)
            generated = out[0]["generated_text"].strip().split("\n")[0]
            summaries[str(cid)] = generated

    return summaries, used_local_fallback

def process_batch_cluster(
    articles: List[Dict[str, Any]], 
    method: str = "hdbscan", 
    cluster_k: Optional[int] = None,
    dim_reduction: str = "umap"
) -> Dict[str, Any]:
    """
    Fetches embeddings, performs UMAP dimensionality reduction to 2D for the UI,
    and applies the chosen clustering algorithm.
    """
    if not articles:
        return {"points": [], "summaries": {}, "nds_scores": {}, "cluster_sentiment": {}, "is_local_summary": False}
    
    # Retrieve
    ids = [a["id"] for a in articles]
    data = collection.get(ids=ids, include=["embeddings", "metadatas"])
    
    if data.get("embeddings") is None or len(data["embeddings"]) == 0:
        return {"points": [], "summaries": {}, "nds_scores": {}, "cluster_sentiment": {}, "is_local_summary": False}
    
    embeddings = np.array(data["embeddings"])

    with _cluster_pipeline_lock:
        labels = _get_cluster_labels(embeddings, method, cluster_k)
        reduced_embeddings = _get_reduced_embeddings(embeddings, dim_reduction)

    from models.metrics import compute_article_distances_from_center
    article_distances = compute_article_distances_from_center(embeddings, np.array(labels))

    sentiment_by_id = {a.get("id"): a.get("sentiment") for a in articles}

    # Build response points
    results = []
    cluster_texts = {}
    cluster_polarities = {}
    
    gemini_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=gemini_key) if gemini_key else None
    
    for idx, article_id in enumerate(ids):
        meta = data["metadatas"][idx]
        cluster_id = int(labels[idx])
        sentiment = sentiment_by_id.get(article_id)
        
        if cluster_id not in cluster_texts:
            cluster_texts[cluster_id] = []
        if cluster_id not in cluster_polarities:
            cluster_polarities[cluster_id] = []

        if sentiment and sentiment.get("polarity") is not None:
            try:
                cluster_polarities[cluster_id].append(float(sentiment.get("polarity")))
            except (TypeError, ValueError):
                pass
            
        t, b = meta.get("title", ""), meta.get("body", "")
        chunk = b[:2500] if client else b[:200]
        cluster_texts[cluster_id].append(f"{t}: {chunk}" if b else t)
            
        results.append({
            "id": article_id,
            "title": meta.get("title", "Unknown"),
            "description": meta.get("description", ""),
            "url": meta.get("url", ""),
            "source": meta.get("source", ""),
            "body": meta.get("body", ""),
            "publish_date": meta.get("publish_date", ""),
            "sentiment": sentiment,
            "cluster": cluster_id,
            "x": float(reduced_embeddings[idx][0]),
            "y": float(reduced_embeddings[idx][1]),
            "distance_from_center": round(float(article_distances[idx]), 3) if cluster_id != -1 else 0.0
        })
        
    target_clusters = [cid for cid in cluster_texts if cid != -1]
    summaries, used_local_fallback = _generate_narrative_summaries(cluster_texts, client, target_clusters)
        
    from models.metrics import compute_narrative_diversity_score
    nds_scores = compute_narrative_diversity_score(embeddings, np.array(labels))
    cluster_sentiment = _compute_cluster_sentiment_stats(cluster_polarities)
            
    return {
        "points": results, 
        "summaries": summaries,
        "nds_scores": nds_scores,
        "cluster_sentiment": cluster_sentiment,
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

def get_article_by_id(article_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single article by its explicit ID from ChromaDB."""
    results = collection.get(ids=[article_id], include=["metadatas"])
    if results and results["ids"] and len(results["ids"]) > 0:
        meta = results["metadatas"][0]
        return {
            "id": results["ids"][0],
            "title": meta.get("title", "Unknown"),
            "description": meta.get("description", ""),
            "url": meta.get("url", ""),
            "source": meta.get("source", ""),
            "body": meta.get("body", ""),
            "publish_date": meta.get("publish_date", ""),
            "category": meta.get("category", "General"),
            "country": meta.get("country", "")
        }
    return None

def compute_global_divergence(articles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes geopolitical narrative divergence metrics.
    Filters exclusively for articles with valid country tags.
    """
    # 1. Filter articles with explicit country tags
    valid_articles = [a for a in articles if a.get("country")]
    if not valid_articles:
        return {"countries": {}, "pairwise_matrix": [], "top_countries": []}
        
    ids = [a["id"] for a in valid_articles]
    # In case any weren't vectorized yet, fetch from chroma
    data = collection.get(ids=ids, include=["embeddings", "metadatas"])
    
    if data.get("embeddings") is None or len(data["embeddings"]) == 0:
        return {"countries": {}, "pairwise_matrix": [], "top_countries": []}
        
    embeddings = np.array(data["embeddings"], dtype=np.float32)
    # Re-align metadata to fetched order to be safe
    fetched_metas = data["metadatas"]
    fetched_ids = data["ids"]
    
    # 2. Group by country
    country_groups = {}
    for i, meta in enumerate(fetched_metas):
        c = meta.get("country")
        if not c: continue
        if c not in country_groups:
            country_groups[c] = {
                "indices": [],
                "count": 0,
                "top_article": {
                    "title": meta.get("title", ""),
                    "source": meta.get("source", ""),
                    "url": meta.get("url", "")
                }
            }
        country_groups[c]["indices"].append(i)
        country_groups[c]["count"] += 1
        
    # Calculate Mean Embedding per country
    country_means = {}
    for c, group in country_groups.items():
        c_embs = embeddings[group["indices"]]
        mean_emb = np.mean(c_embs, axis=0)
        country_means[c] = mean_emb
        
    # Pick Top 15 countries by volume
    top_countries = sorted(country_groups.keys(), key=lambda c: country_groups[c]["count"], reverse=True)[:15]
    
    # Calculate "Rest of World" Divergence for EVERY remaining country
    country_stats = {}
    
    for c in country_groups.keys():
        # Get all indices EXCEPT this country's
        other_indices = []
        for other_c, group in country_groups.items():
            if other_c != c:
                other_indices.extend(group["indices"])
                
        if len(other_indices) > 0:
            rest_of_world_emb = np.mean(embeddings[other_indices], axis=0)
            divergence = float(np.linalg.norm(country_means[c] - rest_of_world_emb))
        else:
            divergence = 0.0
            
        country_stats[c] = {
            "count": country_groups[c]["count"],
            "divergence": divergence,
            "top_article": country_groups[c]["top_article"],
            "articles": [] # Can be populated later by mapping original articles
        }
        
    # Calculate Pairwise Matrix (Top 15)
    matrix = []
    for c1 in top_countries:
        row = []
        for c2 in top_countries:
            if c1 == c2:
                # 0 Divergence with itself
                row.append(0.0)
            else:
                dist = float(np.linalg.norm(country_means[c1] - country_means[c2]))
                row.append(dist)
        matrix.append(row)
        
    return {
        "countries": country_stats,
        "pairwise_matrix": matrix,
        "top_countries": top_countries
    }
