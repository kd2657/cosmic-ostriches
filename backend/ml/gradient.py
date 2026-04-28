import numpy as np
from typing import List, Dict, Any, Optional
from sentence_transformers import util
from .db import collection

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
        
    eval_metrics = {}
    if len(main_indices) > 1:
        main_embs = embeddings[main_indices]
        # Cosine distance = 1 - cosine_similarity
        sim_matrix = util.cos_sim(main_embs, main_embs).numpy()
        n_main_chosen = len(main_indices)
        sum_sim = np.sum(sim_matrix) - np.trace(sim_matrix) # excluding diagonal
        avg_sim = sum_sim / (n_main_chosen * (n_main_chosen - 1))
        eval_metrics["avg_pairwise_distance"] = round(1.0 - float(avg_sim), 3)
        
    return {
        "briefing": briefing,
        "eval_metrics": eval_metrics
    }

