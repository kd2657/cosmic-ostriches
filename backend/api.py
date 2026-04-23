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
        "includeArticleLocation": True,
        "includeSourceLocation": True,
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
            source_obj = article.get("source", {})
            source = source_obj.get("title", "Unknown")
            
            # Geographic resolution for Global Maxima
            country = None
            
            # First attempt: Source location
            loc = source_obj.get("location")
            if not loc:
                # Fallback attempt: Article event location
                loc = article.get("location", {})
                
            if isinstance(loc, dict):
                c_obj = loc.get("country", loc) # Fallback to loc itself if country prop is missing
                if isinstance(c_obj, dict):
                    lbl = c_obj.get("label", {})
                    if isinstance(lbl, dict):
                        country = lbl.get("eng", None)
                    elif isinstance(lbl, str):
                        country = lbl
            
            cleaned_articles.append({
                "id": uid,
                "title": title,
                "body": body,
                "category": category,
                "url": article.get("url"),
                "source": source,
                "country": country,
                "publish_date": article.get("dateTimePub", ""),
                # The precise FULL TEXT we'll embed
                "embed_text": f"{title}. {body}"
            })
            
    return cleaned_articles

@lru_cache(maxsize=32)
def fetch_daily_gradient(page_size: int = 100, category: str = "all") -> List[Dict[str, Any]]:
    """
    Fetches the latest top headlines for the daily gradient via NewsAPI.ai.
    """
    if not NEWS_API_AI_KEY:
        raise ValueError("NEWSAPI_AI_KEY environment variable is not set.")

    payload = {
        "action": "getArticles",
        "lang": "eng",
        "articlesPage": 1,
        "articlesCount": 100,
        "articlesSortBy": "date",
        "resultType": "articles",
        "includeArticleCategories": True,
        "includeArticleLocation": True,
        "includeSourceLocation": True,
        "apiKey": NEWS_API_AI_KEY,
        "articleBodyLen": -1
    }
    
    if category != "all":
        # Mapping to NewsAPI.ai (Event Registry) DMOZ categories for precise topical filtering
        uri_map = {
            "politics": "dmoz/Society/Politics",
            "business": "dmoz/Business",
            "technology": "dmoz/Computers",
            "sports/entertainment": ["dmoz/Sports", "dmoz/Arts/Entertainment"]
        }
        if category in uri_map:
            payload["categoryUri"] = uri_map[category]


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
            source_obj = article.get("source", {})
            source = source_obj.get("title", "Unknown")
            
            # Geographic resolution
            country = None
            
            # First attempt: Source location
            loc = source_obj.get("location")
            if not loc:
                # Fallback attempt: Article event location
                loc = article.get("location", {})
                
            if isinstance(loc, dict):
                c_obj = loc.get("country", loc)
                if isinstance(c_obj, dict):
                    lbl = c_obj.get("label", {})
                    if isinstance(lbl, dict):
                        country = lbl.get("eng", None)
                    elif isinstance(lbl, str):
                        country = lbl
            
            cleaned_articles.append({
                "id": uid,
                "title": title,
                "body": body,
                "category": category,
                "url": article.get("url"),
                "source": source,
                "country": country,
                "publish_date": article.get("dateTimePub", ""),
                "embed_text": f"{title}. {body}"
            })
            
    # Post-filtering for strict adherence
    if category != "all":
        target = category.split('/')[-1].lower() # e.g. 'politics'
        if target == "entertainment": target = "arts" # Event Registry often uses Arts for entertainment
        
        filtered = []
        for a in cleaned_articles:
            cat_str = a["category"].lower()
            # Check if target category appears in the article's category label
            if target in cat_str or (target == "politics" and "society" in cat_str):
                filtered.append(a)
        return filtered[:page_size]
            
    return cleaned_articles[:page_size]
