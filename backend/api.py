import os
import requests
import feedparser
from typing import List, Dict, Any

NEWS_API_KEY = os.environ.get("NEWSAPI_KEY", "")
NEWS_API_URL = "https://newsapi.org/v2/everything"
def fetch_rss_news(query: str, max_articles: int = 50):
    RSS_FEEDS = [
        "http://rss.cnn.com/rss/edition.rss",
        "https://feeds.bbci.co.uk/news/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml"
    ]
    
    articles = []
    
    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        
        for entry in feed.entries:
            title = entry.get("title", "")
            description = entry.get("summary", "")
            
            # Simple query filter
            if query.lower() not in (title + description).lower():
                continue
                
            uid = entry.get("link", title)
            
            articles.append({
                "id": uid,
                "title": title,
                "description": description,
                "url": entry.get("link"),
                "source": feed.feed.get("title", "RSS"),
                "publish_date": entry.get("published", ""),
                "embed_text": f"{title}. {description}"
            })
            
            if len(articles) >= max_articles:
                return articles
                
    return articles
def fetch_newsapi(query: str, page_size: int = 50) -> List[Dict[str, Any]]:
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
def fetch_news(query: str, page_size: int = 50):
    
    # Try NewsAPI first
    try:
        return fetch_newsapi(query, page_size)
    except Exception:
        pass
    
    # Fallback to RSS
    rss_articles = fetch_rss_news(query, page_size)
    
    if rss_articles:
        return rss_articles
        
    raise Exception("All news sources failed")