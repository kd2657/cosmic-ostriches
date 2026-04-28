import numpy as np
from typing import List, Dict, Any, Optional
from .db import collection

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

def compute_source_divergence(articles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes source narrative divergence metrics.
    Groups articles by source and calculates Euclidean distance from the 'Rest of Media' mean embedding.
    """
    valid_articles = [a for a in articles if a.get("source")]
    if not valid_articles:
        return {"sources": {}}
        
    ids = [a["id"] for a in valid_articles]
    data = collection.get(ids=ids, include=["embeddings", "metadatas"])
    
    if data.get("embeddings") is None or len(data["embeddings"]) == 0:
        return {"sources": {}}
        
    embeddings = np.array(data["embeddings"], dtype=np.float32)
    fetched_metas = data["metadatas"]
    
    source_groups = {}
    for i, meta in enumerate(fetched_metas):
        s = meta.get("source", "Unknown Source")
        if s not in source_groups:
            source_groups[s] = {
                "indices": [],
                "count": 0,
                "articles": []
            }
        source_groups[s]["indices"].append(i)
        source_groups[s]["count"] += 1
        
        # Add basic article info for the frontend
        source_groups[s]["articles"].append({
            "id": data["ids"][i],
            "title": meta.get("title", ""),
            "url": meta.get("url", ""),
            "category": meta.get("category", "General"),
            "publish_date": meta.get("publish_date", "")
        })
        
    source_means = {}
    for s, group in source_groups.items():
        s_embs = embeddings[group["indices"]]
        source_means[s] = np.mean(s_embs, axis=0)
        
    source_stats = {}
    for s in source_groups.keys():
        other_indices = []
        for other_s, group in source_groups.items():
            if other_s != s:
                other_indices.extend(group["indices"])
                
        if len(other_indices) > 0:
            rest_of_media_emb = np.mean(embeddings[other_indices], axis=0)
            divergence = float(np.linalg.norm(source_means[s] - rest_of_media_emb))
        else:
            divergence = 0.0
            
        source_stats[s] = {
            "count": source_groups[s]["count"],
            "divergence": divergence,
            "articles": source_groups[s]["articles"]
        }
        
    return {"sources": source_stats}
