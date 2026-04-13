import os
import sys
import warnings

os.environ["KMP_WARNINGS"] = "0"
os.environ["OMP_WARNINGS"] = "0"

if sys.platform != "win32":
    warnings.filterwarnings("ignore", category=UserWarning, module="multiprocessing.resource_tracker")
    try:
        from multiprocessing import resource_tracker
        resource_tracker._warn = lambda *args, **kwargs: None
    except Exception:
        pass

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from api import fetch_news
from ml import vectorize_and_store, process_batch_cluster, query_local_database, compute_similarity_scores
from sentiment import SentimentClassifier

app = FastAPI(title="The Local Minima API")
sentiment_classifier = SentimentClassifier()

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

class ArticleRequest(BaseModel):
    query: str


def attach_article_sentiment(articles):
    sentiment_inputs = []
    sentiment_indexes = []

    for index, article in enumerate(articles):
        title = (article.get("title") or "").strip()
        description = (article.get("description") or "").strip()
        combined_text = " ".join(part for part in [title, description] if part).strip()

        if not combined_text:
            article["sentiment"] = None
            continue

        sentiment_inputs.append(combined_text)
        sentiment_indexes.append(index)

    if not sentiment_inputs:
        return articles

    results = sentiment_classifier.classify_batch(sentiment_inputs)
    for index, result in zip(sentiment_indexes, results):
        articles[index]["sentiment"] = result.to_dict()

    return articles

@app.post("/api/articles")
def run_article_feed(req: ArticleRequest):
    try:
        is_offline_cache = False
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
                raise Exception(f"NewsAPI failed AND local db empty: {str(api_err)}")
        
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
        is_offline_cache = False
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
            
        # Step 2: Cluster & Reduce Dimensionality
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

@app.get("/health")
def health_check():
    return {"status": "ok"}
