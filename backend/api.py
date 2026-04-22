import os
import requests
import feedparser
from typing import List, Dict, Any
from datetime import datetime, timedelta
from difflib import SequenceMatcher
import hashlib
from functools import lru_cache
from ml import query_local_database

# ================================
# API CONFIG
# ================================
NEWS_API_KEY = os.environ.get("NEWSAPI_KEY", "")
NEWS_API_URL = "https://newsapi.org/v2/everything"

NEWS_API_AI_KEY = os.environ.get("NEWSAPI_AI_KEY", "")
NEWS_API_AI_URL = "https://newsapi.ai/api/v1/article/getArticles"


# =====================================================
# RSS FETCH (broad fallback)
# =====================================================
def fetch_rss_news(query: str, max_articles: int = 50):
    RSS_FEEDS = [
        # --- Major / Global ---
        "http://rss.cnn.com/rss/edition.rss",
        "https://feeds.bbci.co.uk/news/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
        "https://feeds.washingtonpost.com/rss/world",
        "https://www.theguardian.com/world/rss",
        "https://www.reuters.com/rssFeed/worldNews",
        "https://feeds.npr.org/1001/rss.xml",

        # --- Business ---
        "https://feeds.bloomberg.com/markets/news.rss",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "https://feeds.marketwatch.com/marketwatch/topstories/",
        "https://www.ft.com/?format=rss",

        # --- Tech ---
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
        "https://www.wired.com/feed/rss",
        "https://arstechnica.com/feed/",

        # --- International ---
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://rss.dw.com/xml/rss-en-all",
        "https://www.france24.com/en/rss",

        # --- Science / Misc ---
        "https://www.sciencedaily.com/rss/top.xml",
        "https://feeds.nature.com/nature/rss/current",
        "https://www.espn.com/espn/rss/news"
    ]

    def normalize(text):
        return text.lower().strip()

    def hash_item(title, link):
        return hashlib.md5(f"{title}{link}".encode()).hexdigest()

    def is_recent(published_parsed, hours=24):
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
            response = requests.get(feed_url, timeout=5)
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

            if query.lower() not in (title + description).lower():
                continue

            if not is_recent(published_parsed):
                continue

            uid_hash = hash_item(normalize(title), link)
            if uid_hash in seen_hashes:
                continue
            seen_hashes.add(uid_hash)

            article = {
                "id": link,
                "title": title,
                "description": description,
                "url": link,
                "source": feed.feed.get("title", "RSS"),
                "publish_date": entry.get("published", ""),
                "embed_text": f"{title}. {description}"
            }

            if any(is_similar(article["title"], a["title"]) for a in articles[-10:]):
                continue

            articles.append(article)

            if len(articles) >= max_articles:
                return articles

    return articles



# =====================================================
# NEWSAPI.AI (PRIMARY - FULL TEXT)
# =====================================================
@lru_cache(maxsize=32)
def fetch_newsapi_ai(query: str, page_size: int = 50) -> List[Dict[str, Any]]:
    if not NEWS_API_AI_KEY:
        raise ValueError("NEWSAPI_AI_KEY not set")

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

    response = requests.post(NEWS_API_AI_URL, json=payload, timeout=5)

    if response.status_code != 200:
        raise Exception(f"NewsAPI.ai Error {response.status_code}")

    data = response.json()
    articles = data.get("articles", {}).get("results", [])

    cleaned_articles = []

    for idx, article in enumerate(articles):
        title = article.get("title") or ""
        body = article.get("body") or ""

        if len(title.split()) > 3 or len(body.split()) > 10:
            uid = article.get("uri") or f"ai-{idx}-{title[:10]}"
            source = article.get("source", {}).get("title", "Unknown")

            cleaned_articles.append({
                "id": uid,
                "title": title,
                "description": body[:300],
                "body": body,
                "url": article.get("url"),
                "source": source,
                "publish_date": article.get("dateTimePub", ""),
                "embed_text": f"{title}. {body}"
            })

    return cleaned_articles


# =====================================================
# DAILY GRADIENT (UNCHANGED)
# =====================================================
@lru_cache(maxsize=32)
def fetch_daily_gradient(page_size: int = 100) -> List[Dict[str, Any]]:
    if not NEWS_API_AI_KEY:
        raise ValueError("NEWS_API_AI_KEY not set")

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

    response = requests.post(NEWS_API_AI_URL, json=payload, timeout=5)

    if response.status_code != 200:
        raise Exception(f"NewsAPI.ai Error {response.status_code}")

    data = response.json()
    articles = data.get("articles", {}).get("results", [])

    cleaned_articles = []

    for idx, article in enumerate(articles):
        title = article.get("title") or ""
        body = article.get("body") or ""

        if len(title.split()) > 3 or len(body.split()) > 10:
            uid = article.get("uri") or f"daily-{idx}-{title[:10]}"
            source = article.get("source", {}).get("title", "Unknown")

            cleaned_articles.append({
                "id": uid,
                "title": title,
                "body": body,
                "url": article.get("url"),
                "source": source,
                "publish_date": article.get("dateTimePub", ""),
                "embed_text": f"{title}. {body}"
            })

    return cleaned_articles


# =====================================================
# MAIN PIPELINE
# =====================================================
def fetch_news(query: str, page_size: int = 50):
    """
    Pipeline:
    1. NewsAPI.ai (best quality)
    2. NewsAPI
    3. RSS
    4. Vector DB
    """

    # --- 1. NewsAPI.ai ---
    try:
        print("[FETCH] Trying NewsAPI.ai...")
        articles = fetch_newsapi_ai(query, page_size)
        if articles:
            return articles
    except Exception as e:
        print(f"[FETCH] NewsAPI.ai failed: {e}")


    # --- 3. RSS ---
    try:
        print("[FETCH] Falling back to RSS...")
        articles = fetch_rss_news(query, page_size)
        if articles:
            return articles
    except Exception as e:
        print(f"[FETCH] RSS failed: {e}")

    # --- 4. Vector DB ---
    print("[FETCH] Falling back to vector DB...")
    articles = query_local_database(query, n_results=page_size)

    if articles:
        return articles

    raise Exception("All sources failed")