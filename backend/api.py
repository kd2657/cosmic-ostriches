import os
import requests
import feedparser
import hashlib
import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import List, Dict, Any
from functools import lru_cache
from bs4 import BeautifulSoup

NEWS_API_AI_KEY = os.environ.get("NEWSAPI_AI_KEY", "")
NEWS_API_AI_URL = "https://newsapi.ai/api/v1/article/getArticles"

# =====================================================
# RSS FETCH (Broad Fallback)
# =====================================================

# Global session for connection pooling
_http_session = requests.Session()
_http_session.headers.update({"User-Agent": "Mozilla/5.0 (The Local Minima; Narrative Synthesis)"})

def _fetch_full_body_text(url: str) -> str:
    """
    Scrapes the full text body from a news URL using a simple heuristic.
    """
    try:
        response = _http_session.get(url, timeout=5)
        if response.status_code != 200:
            return ""
        
        soup = BeautifulSoup(response.content, "lxml")
        
        # Remove script and style elements
        for script_or_style in soup(["script", "style", "nav", "footer", "header"]):
            script_or_style.decompose()
        
        # Heuristic: Find all <p> tags and join them
        # Most major news sites wrap content in <p> tags
        paragraphs = soup.find_all("p")
        text = " ".join([p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 20])
        
        # Basic cleanup: remove excessive whitespace
        import re
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    except Exception:
        return ""

def fetch_rss_news(query: str, max_articles: int = 50) -> List[Dict[str, Any]]:
    """
    Broad fallback that scrapes major RSS feeds for query matches.
    """
    RSS_FEEDS = [
        "http://rss.cnn.com/rss/edition.rss",
        "https://feeds.bbci.co.uk/news/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
        "https://feeds.washingtonpost.com/rss/world",
        "https://www.theguardian.com/world/rss",
        "https://www.reuters.com/rssFeed/worldNews",
        "https://feeds.npr.org/1001/rss.xml",
        "https://feeds.bloomberg.com/markets/news.rss",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
        "https://www.wired.com/feed/rss",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://rss.dw.com/xml/rss-en-all",
        "https://www.france24.com/en/rss",
    ]

    def normalize(text):
        return text.lower().strip()

    def hash_item(title, link):
        return hashlib.md5(f"{title}{link}".encode()).hexdigest()

    def is_recent(published_parsed, hours=48):
        if not published_parsed:
            return True
        published = datetime(*published_parsed[:6])
        return datetime.utcnow() - published < timedelta(hours=hours)

    def is_similar(a, b, threshold=0.85):
        return SequenceMatcher(None, a, b).ratio() > threshold

    seen_hashes = set()
    articles = []

    for feed_url in RSS_FEEDS:
        try:
            response = _http_session.get(feed_url, timeout=5)
            feed = feedparser.parse(response.content)
        except Exception:
            continue

        for entry in feed.entries:
            title = entry.get("title", "")
            description = entry.get("summary", "")
            link = entry.get("link", "")
            published_parsed = entry.get("published_parsed", None)

            if not title or not link:
                continue

            # Filtering based on query
            if query.lower() not in (title + description).lower():
                continue

            if not is_recent(published_parsed):
                continue

            uid_hash = hash_item(normalize(title), link)
            if uid_hash in seen_hashes:
                continue
            seen_hashes.add(uid_hash)

            # Scrape full body text for compatibility with NewsAPI.ai results
            body = _fetch_full_body_text(link)
            if not body or len(body.split()) < 20:
                body = description # Fallback to summary if scrape fails

            article = {
                "id": link,
                "title": title,
                "body": body,
                "category": "RSS",
                "url": link,
                "source": feed.feed.get("title", "RSS"),
                "country": None,
                "publish_date": entry.get("published", ""),
                "embed_text": f"{title}. {body}"
            }

            # Avoid very similar headlines in the same batch
            if any(is_similar(article["title"], a["title"]) for a in articles[-10:]):
                continue

            articles.append(article)
            if len(articles) >= max_articles:
                return articles

    return articles


@lru_cache(maxsize=32)
def fetch_news(query: str, page_size: int = 50) -> List[Dict[str, Any]]:
    """
    Primary news pipeline: NewsAPI.ai -> (RSS + Local DB Fallback).
    """
    try:
        # 1. Try Primary (NewsAPI.ai)
        articles = fetch_newsapi_ai(query, page_size)
        if articles:
            return articles
    except Exception as e:
        if "NEWSAPI_AI_KEY" in str(e):
            print(f"[API] NewsAPI.ai key missing; proceeding with fallbacks.")
        else:
            print(f"[API] NewsAPI.ai failed: {e}")

    # 2. Hybrid Fallback: RSS + Local DB
    # We don't import query_local_database here to avoid circular imports,
    # so we'll expect the caller to handle the local DB merge or we return 
    # a signal that we are in fallback mode.
    # Actually, let's keep fetch_news returning live articles, 
    # and merge them in the orchestrator.
    
    try:
        print(f"[API] Attempting RSS fallback for: {query}")
        return fetch_rss_news(query, page_size)
    except Exception as e:
        print(f"[API] RSS failed: {e}")
        return []

@lru_cache(maxsize=32)
def fetch_newsapi_ai(query: str, page_size: int = 50) -> List[Dict[str, Any]]:
    """
    Fetches FULL BODY news articles from NewsAPI.ai (Event Registry) based on a query.
    If the API keys are not supplied or the request fails, it will attempt
    to gracefully fall back or raise an exception to the frontend.
    """
    if not NEWS_API_AI_KEY:
        return []

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

    try:
        response = requests.post(NEWS_API_AI_URL, json=payload, timeout=10)
        
        if response.status_code != 200:
            error_msg = response.json().get("error", "Unknown error from NewsAPI.ai")
            raise Exception(f"NewsAPI.ai Error ({response.status_code}): {error_msg}")

        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"[API] Network error when contacting NewsAPI.ai: {e}")
        raise Exception(f"Failed to connect to NewsAPI.ai. The service might be down or timed out. Error: {e}")
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
def fetch_daily_gradient(page_size: int = 100) -> List[Dict[str, Any]]:
    """
    Fetches the latest top headlines for the daily gradient via NewsAPI.ai.
    """
    if not NEWS_API_AI_KEY:
        return []

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

    try:
        response = requests.post(NEWS_API_AI_URL, json=payload, timeout=10)
        
        if response.status_code != 200:
            error_msg = response.json().get("error", "Unknown error from NewsAPI.ai")
            raise Exception(f"NewsAPI.ai Error ({response.status_code}): {error_msg}")

        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"[API] Network error when contacting NewsAPI.ai for daily gradient: {e}")
        raise Exception(f"Failed to connect to NewsAPI.ai for daily gradient. Error: {e}")
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
            
    return cleaned_articles
