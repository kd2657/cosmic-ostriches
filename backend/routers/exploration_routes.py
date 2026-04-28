from fastapi import APIRouter, HTTPException, Request, Response

from api import fetch_news, fetch_daily_gradient as fetch_daily_articles
from logger import log_request
from ml import (
    compute_global_divergence,
    compute_source_divergence,
    process_daily_gradient,
    query_local_database,
    vectorize_and_store,
)
from .dependencies import attach_article_sentiment
from .schemas import SearchRequest


explore_router = APIRouter()

@explore_router.get("/api/daily-gradient")
@log_request
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
            articles = fetch_daily_articles(page_size=100)
            if articles:
                articles = vectorize_and_store(articles)
                
        if not articles:
            raise Exception("No recent articles could be fetched.")
            
        gradient = process_daily_gradient(articles)
        return {"status": "success", "results": gradient}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@explore_router.post("/api/global-analysis")
@log_request
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


@explore_router.post("/api/source-analysis")
@log_request
def run_source_analysis(req: SearchRequest):
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
            return {"status": "success", "results": {"sources": {}}, "is_offline_cache": is_offline_cache}
            
        articles = attach_article_sentiment(articles)
        divergence_results = compute_source_divergence(articles)
        
        sources_dict = divergence_results["sources"]
        for a in articles:
            s = a.get("source", "Unknown Source")
            if s and s in sources_dict:
                # Find if we already added it in ml.py (we did add title/url/etc, but let's add sentiment)
                for sa in sources_dict[s]["articles"]:
                    if sa["id"] == a["id"]:
                        sa["sentiment"] = a.get("sentiment")
                        break
                        
        return {"status": "success", "results": divergence_results, "is_offline_cache": is_offline_cache}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


