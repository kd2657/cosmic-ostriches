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
