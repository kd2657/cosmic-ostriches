from __future__ import annotations

import uuid
from threading import Lock
from typing import Dict, Set, Tuple, List, Optional

from fastapi import Request, Response

# Import your existing function
from ml import get_article_by_id, get_articles_by_ids


# -------------------------
# GLOBAL SESSION STORE
# -------------------------

# session_id -> {"liked": set(), "disliked": set()}
_SESSION_STORE: Dict[str, Dict[str, Set[str]]] = {}
_SESSION_LOCK = Lock()


# -------------------------
# SESSION MANAGEMENT
# -------------------------

def get_session_id(request: Request, response: Response) -> str:
    """
    Retrieve or create a session ID using cookies.
    """
    session_id = request.cookies.get("session_id")

    if not session_id:
        session_id = str(uuid.uuid4())
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            samesite="lax"
        )

    return session_id


def _get_or_create_session(session_id: str) -> Dict[str, Set[str]]:
    """
    Internal helper to safely initialize session storage.
    """
    with _SESSION_LOCK:
        if session_id not in _SESSION_STORE:
            _SESSION_STORE[session_id] = {
                "liked": set(),
                "disliked": set()
            }
        return _SESSION_STORE[session_id]


# -------------------------
# VOTING LOGIC
# -------------------------

def record_vote(session_id: str, article_id: str, vote: Optional[str]) -> None:
    """
    Record an upvote or downvote for an article.

    vote: "up" or "down"
    """
    if vote not in ("up", "down", None):
        raise ValueError("vote must be 'up', 'down', or None")

    session = _get_or_create_session(session_id)

    with _SESSION_LOCK:
        if vote == "up":
            session["liked"].add(article_id)
            session["disliked"].discard(article_id)

        elif vote == "down":
            session["disliked"].add(article_id)
            session["liked"].discard(article_id)

        elif vote is None:
            # 🔥 THIS IS THE MISSING PIECE
            session["liked"].discard(article_id)
            session["disliked"].discard(article_id)


def get_session_votes(session_id: str) -> Dict[str, List[str]]:

    """
    Returns current session votes (for debugging or UI state).
    """
    session = _get_or_create_session(session_id)

    return {
        "liked": list(session["liked"]),
        "disliked": list(session["disliked"])
    }


# -------------------------
# RECOMMENDER INTEGRATION
# -------------------------

def get_user_articles(session_id: str) -> Tuple[List[dict], List[dict]]:
    """
    Convert stored article IDs into full article objects
    for the recommender system.
    """
    session = _get_or_create_session(session_id)

    with _SESSION_LOCK:
        liked_ids = list(session["liked"])
        disliked_ids = list(session["disliked"])

    liked_articles = [_ensure_embed_text(a) for a in get_articles_by_ids(liked_ids)]
    disliked_articles = [_ensure_embed_text(a) for a in get_articles_by_ids(disliked_ids)]

    return liked_articles, disliked_articles



def _ensure_embed_text(article: dict) -> dict:
    """
    Guarantees that 'embed_text' exists (required by recommender).
    """
    if "embed_text" not in article:
        title = article.get("title", "")
        body = article.get("body", "") or article.get("description", "")
        article["embed_text"] = f"{title}. {body}"
    return article


# -------------------------
# OPTIONAL UTILITIES
# -------------------------

def clear_session(session_id: str) -> None:
    """
    Clears all stored preferences for a session.
    """
    with _SESSION_LOCK:
        if session_id in _SESSION_STORE:
            _SESSION_STORE[session_id] = {
                "liked": set(),
                "disliked": set()
            }


def delete_session(session_id: str) -> None:
    """
    Completely removes a session from memory.
    """
    with _SESSION_LOCK:
        _SESSION_STORE.pop(session_id, None)