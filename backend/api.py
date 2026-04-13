import os
import requests
from typing import List, Dict, Any

NEWS_API_KEY = os.environ.get("NEWSAPI_KEY", "")
NEWS_API_URL = "https://newsapi.org/v2/everything"

def fetch_news(query: str, page_size: int = 50) -> List[Dict[str, Any]]:
    """
    Fetches news articles from NewsAPI.org based on a query.
    If the API keys are not supplied or the request fails, it will attempt
    to gracefully fall back or raise an exception to the frontend.
    """
    if not NEWS_API_KEY:
        raise ValueError("NEWSAPI_KEY environment variable is not set. Please obtain a free developer key from NewsAPI.org.")

    params = {
        "q": query,
        "language": "en",
        "pageSize": min(page_size, 100),
        "sortBy": "relevancy",
        "apiKey": NEWS_API_KEY
    }

    response = requests.get(NEWS_API_URL, params=params)
    
    if response.status_code != 200:
        error_msg = response.json().get("message", "Unknown error from NewsAPI")
        raise Exception(f"NewsAPI.org Error ({response.status_code}): {error_msg}")

    data = response.json()
    articles = data.get("articles", [])
    
    # Clean and filter articles that have sufficient text to vectorize
    cleaned_articles = []
    
    for idx, article in enumerate(articles):
        title = article.get("title") or ""
        description = article.get("description") or ""
        
        # We need at least some semantic content to work with
        if len(title.split()) > 3 or len(description.split()) > 5:
            # We generate a unique ID based on the URL or title as a fallback
            uid = article.get("url") or f"article-{idx}-{title[:10]}"
            
            cleaned_articles.append({
                "id": uid,
                "title": title,
                "description": description,
                "url": article.get("url"),
                "source": article.get("source", {}).get("name", "Unknown"),
                "publish_date": article.get("publishedAt", ""),
                # The precise text we'll embed
                "embed_text": f"{title}. {description}"
            })
            
    return cleaned_articles

def fetch_daily_briefing(page_size: int = 100) -> List[Dict[str, Any]]:
    """
    Fetches the latest top US headlines for the daily briefing.
    """
    if not NEWS_API_KEY:
        raise ValueError("NEWSAPI_KEY environment variable is not set.")

    params = {
        "country": "us",
        "pageSize": min(page_size, 100),
        "apiKey": NEWS_API_KEY
    }

    # using top-headlines as it's guaranteed to be recent vs 'everything'
    import requests # in case it's not imported at the top, though it is.
    response = requests.get("https://newsapi.org/v2/top-headlines", params=params)
    
    if response.status_code != 200:
        error_msg = response.json().get("message", "Unknown error from NewsAPI")
        raise Exception(f"NewsAPI.org Error ({response.status_code}): {error_msg}")

    data = response.json()
    articles = data.get("articles", [])
    
    cleaned_articles = []
    for idx, article in enumerate(articles):
        title = article.get("title") or ""
        description = article.get("description") or ""
        
        if len(title.split()) > 3 or len(description.split()) > 5:
            uid = article.get("url") or f"daily-{idx}-{title[:10]}"
            cleaned_articles.append({
                "id": uid,
                "title": title,
                "description": description,
                "url": article.get("url"),
                "source": article.get("source", {}).get("name", "Unknown"),
                "publish_date": article.get("publishedAt", ""),
                "embed_text": f"{title}. {description}"
            })
            
    return cleaned_articles
