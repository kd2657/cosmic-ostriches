from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from api import fetch_news
from cluster_stream import stream_search_pipeline
from logger import log_request
from ml import (
    compute_similarity_scores,
    extract_query_parameters,
    get_article_by_id,
    query_local_database,
    vectorize_and_store,
)
from .dependencies import attach_article_sentiment
from .schemas import ArticleRequest, SearchRequest


api_router = APIRouter()

@api_router.post("/api/articles")
@log_request
def run_article_feed(req: ArticleRequest):
    try:
        is_offline_cache = req.force_local
        if req.force_local:
            articles = query_local_database(req.query)
        else:
            try:
                live_articles = fetch_news(req.query)
                if live_articles:
                    # Clone dicts immediately from cache to prevent ANY downstream mutation
                    articles = [dict(a) for a in live_articles]
                    vectorize_and_store(articles)
                else:
                    articles = query_local_database(req.query)
                    is_offline_cache = True
            except Exception as api_err:
                print(f"Fetch failure: {api_err}")
                articles = query_local_database(req.query)
                is_offline_cache = True
                if not articles:
                    raise Exception(f"All sources (API, RSS, Local DB) failed: {str(api_err)}")
        
        if not articles:
            return {"status": "success", "articles": [], "is_offline_cache": is_offline_cache}
            
        # Compute match percentages natively across all embeddings
        ranked_articles = compute_similarity_scores(req.query, articles)

        # Strict quality filter: Always purge low-confidence matches (<30%)
        ranked_articles = [a for a in ranked_articles if a.get("match_score", 0) >= 30]
        
        if req.parameterize_query and ranked_articles:
            params = extract_query_parameters(req.query)
            if params["location"] or params["time"]:
                filtered = []
                for a in ranked_articles:
                    text_to_search = (a.get("title", "") + " " + a.get("body", "")).lower()
                    keep = True
                    if params["location"] and params["location"].lower() not in text_to_search:
                        keep = False
                    if params["time"] and params["time"] not in a.get("publish_date", ""):
                        keep = False
                    if keep:
                        filtered.append(a)
                ranked_articles = filtered
        
        if req.use_sentiment:
            ranked_articles = attach_article_sentiment(ranked_articles)
            
        if not req.include_bodies:
            for a in ranked_articles:
                a["body"] = ""
        
        return {"status": "success", "articles": ranked_articles, "is_offline_cache": is_offline_cache}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/api/search")
@log_request
def run_search_pipeline(req: SearchRequest):
    try:
        # Step 1: Fetch from NewsAPI.org
        is_offline_cache = req.force_local
        if req.force_local:
            articles = query_local_database(req.query)
        else:
            try:
                articles = fetch_news(req.query)
                if articles:
                    # Vectorize & Store entirely new articles in local ChromaDB
                    articles = vectorize_and_store(articles)
                else:
                    # If API succeeded but found nothing, attempt local historical semantic search
                    articles = query_local_database(req.query)
                    is_offline_cache = True
            except Exception as api_err:
                print(f"API Error ({api_err}): Falling back to local ChromaDB semantic search offline mode.")
                # If the API crashed (rate-limited, no key), fallback entirely to the local vector DB
                articles = query_local_database(req.query)
                is_offline_cache = True
                if not articles:
                    raise Exception(f"NewsAPI failed AND local database is empty: {str(api_err)}")
        
        if not articles:
            return {"status": "success", "results": [], "is_offline_cache": is_offline_cache}
            
        # Step 2: Sentiment, Cluster & Reduce Dimensionality
        if req.use_sentiment:
            articles = attach_article_sentiment(articles)
        results = process_batch_cluster(
            articles, 
            method=req.algorithm, 
            cluster_k=req.k, 
            dim_reduction=req.dim_reduction
        )
        
        if not req.include_bodies:
            for pt in results.get("points", []):
                pt["body"] = ""

        
        results["is_offline_cache"] = is_offline_cache
        
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/api/search/stream")
@log_request
async def stream_search(req: SearchRequest):
    """
    Experimental SSE endpoint for narrative synthesis.
    Polls milestones from fetch -> cluster -> summarize and yields progress events.
    """
    return StreamingResponse(
        stream_search_pipeline(
            req.query, 
            req.algorithm, 
            req.k, 
            req.dim_reduction, 
            req.force_local,
            req.use_sentiment,
            req.include_bodies
        ),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"}
    )


@api_router.get("/api/article/{article_id:path}")
@log_request
def fetch_single_article(article_id: str):
    data = get_article_by_id(article_id)
    if not data:
        raise HTTPException(status_code=404, detail="Article not found")
    try:
        attach_article_sentiment([data])
    except Exception as e:
        print(f"Failed to attach sentiment: {e}")
        # Allow it to return without sentiment instead of crashing
    return {"status": "success", "article": data}

