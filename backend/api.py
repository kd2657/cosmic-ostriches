import os
import requests
from typing import List, Dict, Any
from functools import lru_cache

NEWS_API_AI_KEY = os.environ.get("NEWSAPI_AI_KEY", "")
NEWS_API_AI_URL = "https://newsapi.ai/api/v1/article/getArticles"

@lru_cache(maxsize=32)
def fetch_news(query: str, page_size: int = 50) -> List[Dict[str, Any]]:
    """
    Fetches FULL BODY news articles from NewsAPI.ai (Event Registry) based on a query.
    If the API keys are not supplied or the request fails, it will attempt
    to gracefully fall back or raise an exception to the frontend.
    """
    if not NEWS_API_AI_KEY:
        raise ValueError("NEWSAPI_AI_KEY environment variable is not set. Please obtain a free developer key from newsapi.ai.")

    payload = {
        "action": "getArticles",
        "keyword": query,
        "lang": "eng",
        "articlesPage": 1,
        "articlesCount": min(page_size, 100),
        "articlesSortBy": "rel",
        "resultType": "articles",
        "includeArticleCategories": True,
        "apiKey": NEWS_API_AI_KEY,
        "articleBodyLen": -1
    }

    response = requests.post(NEWS_API_AI_URL, json=payload)
    
    if response.status_code != 200:
        error_msg = response.json().get("error", "Unknown error from NewsAPI.ai")
        raise Exception(f"NewsAPI.ai Error ({response.status_code}): {error_msg}")

    data = response.json()
    # Event Registry nests results in data['articles']['results']
    articles = data.get("articles", {}).get("results", [])
    
    cleaned_articles = []
    
    for idx, article in enumerate(articles):
        title = article.get("title") or ""
        body = article.get("body") or ""
        
        cats = article.get("categories", [])
        category = "General"
        if cats and len(cats) > 0:
            c = cats[0]
            if isinstance(c, dict):
                category = str(c.get("label", c.get("uri", "General"))).split("/")[-1].replace("dmoz", "").replace("News", "").strip("_ ")
            else:
                category = str(c)
        category = category if category else "General"
        
        # We need at least some semantic content to work with
        if len(title.split()) > 3 or len(body.split()) > 10:
            uid = article.get("uri") or f"article-{idx}-{title[:10]}"
            source = article.get("source", {}).get("title", "Unknown")
            
            cleaned_articles.append({
                "id": uid,
                "title": title,
                "body": body,
                "category": category,
                "url": article.get("url"),
                "source": source,
                "publish_date": article.get("dateTimePub", ""),
                # The precise FULL TEXT we'll embed
                "embed_text": f"{title}. {body}"
            })
            
    return cleaned_articles

@lru_cache(maxsize=32)
def fetch_daily_gradient(page_size: int = 100) -> List[Dict[str, Any]]:
    """
    Fetches the latest top headlines for the daily gradient via NewsAPI.ai.
    """
    if not NEWS_API_AI_KEY:
        raise ValueError("NEWSAPI_AI_KEY environment variable is not set.")

    payload = {
        "action": "getArticles",
        "lang": "eng",
        "articlesPage": 1,
        "articlesCount": min(page_size, 100),
        "articlesSortBy": "date",
        "resultType": "articles",
        "includeArticleCategories": True,
        "apiKey": NEWS_API_AI_KEY,
        "articleBodyLen": -1
    }

    response = requests.post(NEWS_API_AI_URL, json=payload)
    
    if response.status_code != 200:
        error_msg = response.json().get("error", "Unknown error from NewsAPI.ai")
        raise Exception(f"NewsAPI.ai Error ({response.status_code}): {error_msg}")

    data = response.json()
    articles = data.get("articles", {}).get("results", [])
    
    cleaned_articles = []
    for idx, article in enumerate(articles):
        title = article.get("title") or ""
        body = article.get("body") or ""
        
        cats = article.get("categories", [])
        category = "General"
        if cats and len(cats) > 0:
            c = cats[0]
            if isinstance(c, dict):
                category = str(c.get("label", c.get("uri", "General"))).split("/")[-1].replace("dmoz", "").replace("News", "").strip("_ ")
            else:
                category = str(c)
        category = category if category else "General"
        
        if len(title.split()) > 3 or len(body.split()) > 10:
            uid = article.get("uri") or f"daily-{idx}-{title[:10]}"
            source = article.get("source", {}).get("title", "Unknown")
            
            cleaned_articles.append({
                "id": uid,
                "title": title,
                "body": body,
                "category": category,
                "url": article.get("url"),
                "source": source,
                "publish_date": article.get("dateTimePub", ""),
                "embed_text": f"{title}. {body}"
            })
            
    return cleaned_articles
