import os
import sys

os.environ["KMP_WARNINGS"] = "0"
os.environ["OMP_WARNINGS"] = "0"

if sys.platform != "win32":
    import warnings
    warnings.filterwarnings("ignore", category=UserWarning, module="multiprocessing.resource_tracker")
    try:
        from multiprocessing import resource_tracker
        # Monkey-patch to suppress the "leaked semaphore" warning on exit
        resource_tracker._warn = lambda *args, **kwargs: None
    except Exception:
        pass

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from api import fetch_news, fetch_daily_gradient
from ml import vectorize_and_store, process_batch_cluster, query_local_database, compute_similarity_scores, process_daily_gradient, get_article_by_id, compute_global_divergence, model_manager
from sentiment import SentimentClassifier
from cluster_stream import stream_search_pipeline
from fastapi.responses import StreamingResponse

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start model loading in the background when the server boots."""
    model_manager.start_background_init()
    yield

app = FastAPI(title="The Local Minima API", lifespan=lifespan)

# Sentiment classifier is pre-loaded by ModelManager during boot sequence
def get_sentiment_classifier():
    if model_manager.sentiment is None:
        # Fallback in case a request hits before background thread finishes Stage 4
        from sentiment import SentimentClassifier
        model_manager.sentiment = SentimentClassifier()
    return model_manager.sentiment

# Allow Next.js frontend to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchRequest(BaseModel):
    query: str
    algorithm: Optional[str] = "hdbscan"  # "hdbscan", "kmeans", "gmm"
    k: Optional[int] = None
    dim_reduction: str = "umap"
    force_local: Optional[bool] = False

class ArticleRequest(BaseModel):
    query: str
    force_local: Optional[bool] = False


def attach_article_sentiment(articles):
    sentiment_inputs = []
    sentiment_indexes = []

    for index, article in enumerate(articles):
        title = (article.get("title") or "").strip()
        description = (article.get("description") or "").strip()
        body = (article.get("body") or "").strip()
        combined_text = " ".join(part for part in [title, description, body] if part).strip()

        if not combined_text:
            article["sentiment"] = None
            continue

        sentiment_inputs.append(combined_text)
        sentiment_indexes.append(index)

    if not sentiment_inputs:
        return articles

    results = get_sentiment_classifier().classify_batch(sentiment_inputs)
    for index, result in zip(sentiment_indexes, results):
        articles[index]["sentiment"] = result.to_dict()

    return articles

@app.post("/api/articles")
def run_article_feed(req: ArticleRequest):
    try:
        is_offline_cache = req.force_local
        if req.force_local:
            articles = query_local_database(req.query)
        else:
            try:
                live_articles = fetch_news(req.query)
                local_articles = query_local_database(req.query)
                
                # Merge logic: prioritize live RSS, then append local DB
                # Using a set of IDs to prevent duplicates
                seen_ids = {a["id"] for a in live_articles}
                articles = live_articles
                for a in local_articles:
                    if a["id"] not in seen_ids:
                        articles.append(a)
                        seen_ids.add(a["id"])
                
                if live_articles:
                    # Only vectorize the NEW live articles (RSS)
                    vectorize_and_store(live_articles)
                else:
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
        ranked_articles = attach_article_sentiment(ranked_articles)
        
        return {"status": "success", "articles": ranked_articles, "is_offline_cache": is_offline_cache}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/search")
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
        articles = attach_article_sentiment(articles)
        results = process_batch_cluster(
            articles, 
            method=req.algorithm, 
            cluster_k=req.k, 
            dim_reduction=req.dim_reduction
        )
        
        results["is_offline_cache"] = is_offline_cache
        
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/search/stream")
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
            req.force_local
        ),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"}
    )

@app.get("/api/daily-gradient")
def get_daily_gradient(force_local: bool = False):
    try:
        articles = []
        if force_local:
            # Query the database for recent top articles (if we have a way to fetch recent)
            # Actually our query_local_database requires a query string, but we can just pull some vectors.
            # But query_local_database needs a query string.
            # We can use "news" as a generic query to pull the most recent / general articles.
            articles = query_local_database("news", n_results=100)
        else:
            articles = fetch_daily_gradient(page_size=100)
            if articles:
                articles = vectorize_and_store(articles)
                
        if not articles:
            raise Exception("No recent articles could be fetched.")
            
        gradient = process_daily_gradient(articles)
        return {"status": "success", "results": gradient}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/global-analysis")
def run_global_analysis(req: SearchRequest):
    try:
        is_offline_cache = req.force_local
        if req.force_local:
            articles = query_local_database(req.query)
        else:
            try:
                articles = fetch_news(req.query)
                if articles:
                    articles = vectorize_and_store(articles)
                else:
                    articles = query_local_database(req.query)
                    is_offline_cache = True
            except Exception as api_err:
                articles = query_local_database(req.query)
                is_offline_cache = True
                if not articles:
                    raise Exception(f"NewsAPI failed AND local database empty: {str(api_err)}")
        
        if not articles:
            return {"status": "success", "results": {"countries": {}, "pairwise_matrix": [], "top_countries": []}, "is_offline_cache": is_offline_cache}
            
        articles = attach_article_sentiment(articles)
        divergence_results = compute_global_divergence(articles)
        
        # Populate article lists & mean sentiments per country
        countries_dict = divergence_results["countries"]
        for a in articles:
            c = a.get("country")
            if c and c in countries_dict:
                countries_dict[c]["articles"].append({
                    "title": a.get("title"),
                    "source": a.get("source"),
                    "url": a.get("url"),
                    "sentiment": a.get("sentiment"),
                    "publish_date": a.get("publish_date")
                })
                
        # Calculate mean sentiment per country (-1.0 to 1.0)
        for c, data in countries_dict.items():
            scores = []
            for art in data["articles"]:
                if art.get("sentiment"):
                    s = art["sentiment"]
                    val = s.get("polarity")
                    if val is None:
                        val = s.get("confidence", 0.0)
                        if s.get("sentiment", "positive").lower() in ("negative", "slightly_negative"):
                            val = -val
                    scores.append(val)
            if scores:
                data["mean_sentiment"] = sum(scores) / len(scores)
            else:
                data["mean_sentiment"] = 0.0
                
        return {"status": "success", "results": divergence_results, "is_offline_cache": is_offline_cache}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/status")
def get_system_status():
    """Returns the current model initialization status for the frontend boot sequence."""
    return model_manager.get_status()

@app.get("/api/article/{article_id:path}")
def fetch_single_article(article_id: str):
    data = get_article_by_id(article_id)
    if not data:
        raise HTTPException(status_code=404, detail="Article not found")
    attach_article_sentiment([data])
    return {"status": "success", "article": data}
