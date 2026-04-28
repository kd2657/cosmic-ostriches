"""
Cluster Streaming Engine: SSE-based narrative synthesis pipeline.

Provides a generator that yields real-time progress events followed by the final
clustered data payload. Designed to be consumed by FastAPI's StreamingResponse.
"""

import json
import os
from typing import Any, Dict, List, Optional

import asyncio
import numpy as np
from google import genai

from api import fetch_news
from ml import (
    _cluster_pipeline_lock,
    _generate_narrative_summaries,
    _get_cluster_labels,
    _get_reduced_embeddings,
    collection,
    compute_similarity_scores,
    extract_query_parameters,
    query_local_database,
    vectorize_and_store,
)
from models.metrics import (
    compute_article_distances_from_center,
    compute_clustering_eval_metrics,
    compute_narrative_diversity_score,
)


async def stream_search_pipeline(
    query: str,
    algorithm: str,
    k: Optional[int],
    dim_reduction: str,
    force_local: bool,
    use_sentiment: bool = False,
    include_bodies: bool = False,
    parameterize_query: bool = False,
):
    """
    Generator that yields SSE-formatted events as it processes the search/clustering pipeline.
    """
    try:
        # Phase 1: News Fetching
        yield f"data: {json.dumps({'event': 'stage', 'data': {'stage': '📡 Fetching live news narratives', 'progress': 10}})}\n\n"
        await asyncio.sleep(0)

        is_offline_cache = force_local
        if force_local:
            articles = query_local_database(query)
        else:
            try:
                live_articles = fetch_news(query)

                if live_articles:
                    articles = live_articles
                else:
                    articles = query_local_database(query)
                    is_offline_cache = True

                if live_articles:
                    yield f"data: {json.dumps({'event': 'stage', 'data': {'stage': '🧬 Embedding discourse vectors', 'progress': 25}})}\n\n"
                    await asyncio.sleep(0)
                    vectorize_and_store(live_articles)
                else:
                    is_offline_cache = True
            except Exception as e:
                print(f"Streaming fetch error: {e}")
                articles = query_local_database(query)
                is_offline_cache = True

        if parameterize_query:
            params = extract_query_parameters(query)
            if params["location"] or params["time"]:
                filtered = []
                for a in articles:
                    text_to_search = (a.get("title", "") + " " + a.get("body", "")).lower()
                    keep = True
                    if params["location"] and params["location"].lower() not in text_to_search:
                        keep = False
                    if params["time"] and params["time"] not in a.get("publish_date", ""):
                        keep = False
                    if keep:
                        filtered.append(a)
                articles = filtered

        # Quality Filter: Compute Cross-Encoder scores and purge low-confidence results
        if articles:
            articles = compute_similarity_scores(query, articles)
            articles = [a for a in articles if a.get("match_score", 0) >= 30]

        if not articles:
            yield f"data: {json.dumps({'event': 'error', 'data': 'No articles found for the given query.'})}\n\n"
            await asyncio.sleep(0)
            return

        # Phase 2: Processing Embeddings
        yield f"data: {json.dumps({'event': 'stage', 'data': {'stage': '🔮 Computing structural clusters', 'progress': 50}})}\n\n"
        await asyncio.sleep(0)

        ids = [a["id"] for a in articles]
        data = collection.get(ids=ids, include=["embeddings", "metadatas"])

        if data.get("embeddings") is None or len(data["embeddings"]) == 0:
            yield f"data: {json.dumps({'event': 'error', 'data': 'Failed to retrieve vectors for narrative synthesis.'})}\n\n"
            await asyncio.sleep(0)
            return

        embeddings = np.array(data["embeddings"])

        # Phase 3: Spatial Analysis & Synthesis (lock protects UMAP/Numba thread safety)
        with _cluster_pipeline_lock:
            labels = _get_cluster_labels(embeddings, algorithm, k)
            reduced_embeddings = _get_reduced_embeddings(embeddings, dim_reduction)

        yield f"data: {json.dumps({'event': 'stage', 'data': {'stage': '✨ Generating AI narrative synthesis', 'progress': 75}})}\n\n"
        await asyncio.sleep(0)

        article_distances = compute_article_distances_from_center(embeddings, np.array(labels))

        results = []
        cluster_texts: Dict[int, List[str]] = {}
        gemini_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=gemini_key) if gemini_key else None

        for idx, article_id in enumerate(ids):
            meta = data["metadatas"][idx]
            cluster_id = int(labels[idx])
            if cluster_id not in cluster_texts:
                cluster_texts[cluster_id] = []

            t, b = meta.get("title", ""), meta.get("body", "")
            chunk = b[:2500] if client else b[:200]
            cluster_texts[cluster_id].append(f"{t}: {chunk}" if b else t)

            result_item: Dict[str, Any] = {
                "id": article_id,
                "title": meta.get("title", "Unknown"),
                "description": meta.get("description", ""),
                "url": meta.get("url", ""),
                "source": meta.get("source", ""),
                "publish_date": meta.get("publish_date", ""),
                "cluster": cluster_id,
                "x": float(reduced_embeddings[idx][0]),
                "y": float(reduced_embeddings[idx][1]),
                "distance_from_center": round(float(article_distances[idx]), 3) if cluster_id != -1 else 0.0,
            }
            if include_bodies:
                result_item["body"] = meta.get("body", "")
            if use_sentiment and "sentiment" in meta:
                result_item["sentiment"] = meta["sentiment"]

            results.append(result_item)

        target_clusters = [cid for cid in cluster_texts if cid != -1]
        summaries, used_local_fallback = _generate_narrative_summaries(cluster_texts, client, target_clusters)
        nds_scores = compute_narrative_diversity_score(embeddings, np.array(labels))
        eval_metrics = compute_clustering_eval_metrics(embeddings, np.array(labels), nds_scores)

        # Phase 4: Yield Result
        final_data = {
            "points": results,
            "summaries": summaries,
            "nds_scores": nds_scores,
            "eval_metrics": eval_metrics,
            "is_local_summary": used_local_fallback,
            "is_offline_cache": is_offline_cache,
        }

        yield f"data: {json.dumps({'event': 'result', 'data': final_data})}\n\n"
        await asyncio.sleep(0)

    except Exception as e:
        print(f"STREAM FATAL ERROR: {e}")
        yield f"data: {json.dumps({'event': 'error', 'data': str(e)})}\n\n"
