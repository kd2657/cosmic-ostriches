"""
Metrics computation module, including Narrative Diversity Score.
"""

import numpy as np
from sentence_transformers import util

def compute_narrative_diversity_score(embeddings: np.ndarray, labels: np.ndarray) -> dict:
    """
    Computes Narrative Diversity Score (NDS) for each cluster based on pairwise cosine similarity.
    """
    unique_clusters = set(labels)
    scores = {}
    
    for c in unique_clusters:
        if c == -1:
            continue
            
        cluster_mask = (np.array(labels) == c)
        cluster_embs = np.array(embeddings)[cluster_mask]
        
        n = len(cluster_embs)
        if n <= 1:
            scores[str(c)] = 0.0
            continue
            
        sim_matrix = util.cos_sim(cluster_embs, cluster_embs).numpy()
        np.fill_diagonal(sim_matrix, 0)
        sum_sim = np.sum(sim_matrix)
        
        avg_sim = sum_sim / (n * (n - 1))
        nds = 1.0 - float(avg_sim)
        
        # Handle tiny floating point errors causing slightly negative nears-zeros
        scores[str(c)] = max(0.0, round(nds, 2))
        
    return scores

def compute_article_distances_from_center(embeddings: np.ndarray, labels: np.ndarray) -> np.ndarray:
    """
    Computes Distance from Narrative Center for each article.
    Distance = 1 - cosine_similarity(article_embedding, cluster_centroid)
    """
    distances = np.zeros(len(labels))
    unique_clusters = set(labels)
    
    for c in unique_clusters:
        if c == -1:
            continue
            
        cluster_mask = (np.array(labels) == c)
        cluster_embs = np.array(embeddings)[cluster_mask]
        
        n = len(cluster_embs)
        if n <= 1:
            distances[cluster_mask] = 0.0
            continue
            
        centroid = np.mean(cluster_embs, axis=0)
        centroid_tensor = np.expand_dims(centroid, axis=0)
        sims = util.cos_sim(cluster_embs, centroid_tensor).numpy().flatten()
        
        dists = 1.0 - sims
        dists = np.maximum(0.0, dists)
        distances[cluster_mask] = dists
        
    return distances

def compute_clustering_eval_metrics(embeddings: np.ndarray, labels: np.ndarray, nds_scores: dict) -> dict:
    """
    Computes internal validation metrics for the clustering result.
    Includes Silhouette Score and Davies-Bouldin Index (with/without noise).
    """
    from sklearn.metrics import silhouette_score, davies_bouldin_score
    
    eval_metrics = {}
    unique_labels = set(labels)
    
    # With Noise
    if len(unique_labels) > 1:
        try:
            eval_metrics["silhouette_with_noise"] = round(float(silhouette_score(embeddings, labels)), 3)
            eval_metrics["davies_bouldin_with_noise"] = round(float(davies_bouldin_score(embeddings, labels)), 3)
        except:
            pass
    
    # Without Noise
    non_noise_mask = (labels != -1)
    if np.sum(non_noise_mask) > 1:
        non_noise_labels = labels[non_noise_mask]
        non_noise_embeddings = embeddings[non_noise_mask]
        if len(set(non_noise_labels)) > 1:
            try:
                eval_metrics["silhouette_no_noise"] = round(float(silhouette_score(non_noise_embeddings, non_noise_labels)), 3)
                eval_metrics["davies_bouldin_no_noise"] = round(float(davies_bouldin_score(non_noise_embeddings, non_noise_labels)), 3)
            except:
                pass
        
    # Aggregate NDS
    if nds_scores:
        avg_nds = sum(nds_scores.values()) / max(1, len(nds_scores))
        eval_metrics["avg_nds"] = round(avg_nds, 3)
        
    return eval_metrics
