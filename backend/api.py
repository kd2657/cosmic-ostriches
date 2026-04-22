import os
import requests
from typing import List, Dict, Any
from functools import lru_cache
from dotenv import load_dotenv

# Force load .env because terminal injection is disabled
load_dotenv()

NEWS_API_AI_KEY = os.environ.get("NEWSAPI_AI_KEY", "")
NEWS_API_AI_URL = "https://newsapi.ai/api/v1/article/getArticles"

# Support for the user's existing NewsAPI.org key
NEWS_API_ORG_KEY = os.environ.get("NEWSAPI_KEY", "")
NEWS_API_ORG_URL = "https://newsapi.org/v2/everything"
NEWS_API_ORG_TOP_URL = "https://newsapi.org/v2/top-headlines"

@lru_cache(maxsize=32)
def fetch_news(query: str, page_size: int = 50) -> List[Dict[str, Any]]:
    """
    Fetches news. Defaults to NewsAPI.ai, falls back to NewsAPI.org.
    """
    if NEWS_API_AI_KEY and not NEWS_API_AI_KEY.startswith("your_"):
        return _fetch_from_newsapi_ai(query, page_size)
    elif NEWS_API_ORG_KEY:
        return _fetch_from_newsapi_org(query, page_size)
    else:
        raise ValueError("No valid API Key found in .env. Please set NEWSAPI_AI_KEY or NEWSAPI_KEY.")

def _fetch_from_newsapi_ai(query: str, page_size: int = 50) -> List[Dict[str, Any]]:
    
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

def _fetch_from_newsapi_org(query: str, page_size: int = 50) -> List[Dict[str, Any]]:
    params = {"q": query, "apiKey": NEWS_API_ORG_KEY, "pageSize": min(page_size, 100), "language": "en"}
    res = requests.get(NEWS_API_ORG_URL, params=params)
    if res.status_code != 200: raise Exception(f"NewsAPI.org Error: {res.text}")
    articles = res.json().get("articles", [])
    return [{
        "id": a.get("url"), "title": a.get("title"), "body": a.get("description"),
        "category": "General", "url": a.get("url"), "source": a.get("source", {}).get("name"),
        "country": None, "publish_date": a.get("publishedAt"), "embed_text": f"{a.get('title')}. {a.get('description')}"
    } for a in articles]

@lru_cache(maxsize=32)
def fetch_daily_gradient(page_size: int = 100) -> List[Dict[str, Any]]:
    if NEWS_API_AI_KEY and not NEWS_API_AI_KEY.startswith("your_"):
        return _fetch_daily_gradient_ai(page_size)
    elif NEWS_API_ORG_KEY:
        return _fetch_daily_gradient_org(page_size)
    else:
        raise ValueError("No API Key found.")

def _fetch_daily_gradient_ai(page_size: int = 100) -> List[Dict[str, Any]]:
    payload = {
        "action": "getArticles",
        "lang": "eng",
        "articlesPage": 1,
        "articlesCount": min(page_size, 100),
        "articlesSortBy": "date",
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
                "id": uid, "title": title, "body": body, "category": category, "url": article.get("url"),
                "source": source, "country": country, "publish_date": article.get("dateTimePub", ""),
                "embed_text": f"{title}. {body}"
            })
            
    return cleaned_articles

def _fetch_daily_gradient_org(page_size: int = 100) -> List[Dict[str, Any]]:
    params = {"apiKey": NEWS_API_ORG_KEY, "pageSize": min(page_size, 100), "language": "en", "category": "general"}
    res = requests.get(NEWS_API_ORG_URL.replace("everything", "top-headlines"), params=params)
    if res.status_code != 200: return []
    articles = res.json().get("articles", [])
    return [{
        "id": a.get("url"), "title": a.get("title"), "body": a.get("description"),
        "category": "General", "url": a.get("url"), "source": a.get("source", {}).get("name"),
        "country": None, "publish_date": a.get("publishedAt"), "embed_text": f"{a.get('title')}. {a.get('description')}"
    } for a in articles]
