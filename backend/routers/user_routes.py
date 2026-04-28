from fastapi import APIRouter, HTTPException, Request, Response

from api import fetch_daily_gradient as fetch_daily_articles
from logger import log_request
from ml import query_local_database, vectorize_and_store
from recommender import rank_articles_for_user
from session import get_session_id, get_user_articles, record_vote
from .schemas import VoteRequest

user_router = APIRouter()

@user_router.post("/api/vote")
@log_request
def vote(payload: dict, request: Request, response: Response):
    article_id = payload.get("article_id")
    vote_type = payload.get("vote")

    if not article_id or vote_type not in ("up", "down", None):
        raise HTTPException(status_code=400, detail="Invalid input")

    session_id = get_session_id(request, response)
    
    try:
        record_vote(session_id, article_id, vote_type)
    except Exception as e:
        print(f"Vote recording failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to register your vote. Please try again.")

    return {"status": "ok"}

def _get_recommendation_candidates(liked_articles: list) -> list:
    """Helper to fetch recent and semantic candidates for recommendations."""
    RECENT_K = 50
    SEMANTIC_K = 50

    # 1. Fetch recent articles
    recent = fetch_daily_articles(page_size=RECENT_K)
    recent = vectorize_and_store(recent) if recent else []

    # 2. Build semantic query
    if liked_articles:
        profile_query = " ".join([
            (a.get("title", "") + " " + (a.get("description") or ""))[:200]
            for a in liked_articles[:5]
        ])
    else:
        profile_query = "news"

    # 3. Retrieve semantically similar articles
    semantic = query_local_database(profile_query, n_results=SEMANTIC_K)

    # 4. Merge + deduplicate
    seen_ids = set()
    combined = []
    for article in recent + semantic:
        aid = article.get("id")
        if aid and aid not in seen_ids:
            seen_ids.add(aid)
            combined.append(article)
    
    return combined


@user_router.get("/api/recommend")
@log_request
def recommend(request: Request, response: Response):
    try:
        session_id = get_session_id(request, response)
        liked, disliked = get_user_articles(session_id)

        # 1. Fetch Candidates
        candidates = _get_recommendation_candidates(liked)
        if not candidates:
            return {"status": "success", "articles": []}

        # 2. Cold Start (no user data) — return recency-ordered candidates
        if not liked:
            return {"status": "success", "articles": candidates[:20]}

        # 3. Personalized Ranking — pure embedding similarity, no sentiment
        ranked = rank_articles_for_user(
            articles=candidates,
            liked_articles=liked,
            disliked_articles=disliked,
            use_sentiment=False
        )

        return {"status": "success", "articles": ranked[:20]}
    except Exception as e:
        print(f"Recommendation engine error: {e}")
        raise HTTPException(status_code=500, detail="Recommendation engine is temporarily unavailable.")

