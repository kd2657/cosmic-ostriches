from __future__ import annotations

import numpy as np
from typing import List, Dict, Any, Optional
from sentence_transformers import util

# Reuse your existing embedding model
from ml import _get_model


class ArticleRecommender:
    """
    Embedding-based user preference model.

    Learns a preference vector from liked/disliked articles and
    scores new articles via cosine similarity.
    """

    def __init__(self):
        self.model = _get_model()
        self.profile_vector: Optional[np.ndarray] = None

    # -------------------------
    # TRAINING
    # -------------------------
    def fit(
        self,
        liked_articles: List[Dict[str, Any]],
        disliked_articles: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        Build user preference vector.

        If disliked_articles is provided:
            profile = mean(liked) - mean(disliked)
        Else:
            profile = mean(liked)
        """

        if not liked_articles:
            self.profile_vector = None
            return

        liked_texts = [a["embed_text"] for a in liked_articles]
        liked_embs = self.model.encode(liked_texts)

        if disliked_articles:
            disliked_texts = [a["embed_text"] for a in disliked_articles]
            disliked_embs = self.model.encode(disliked_texts)

            self.profile_vector = np.mean(liked_embs, axis=0) - np.mean(disliked_embs, axis=0)
        else:
            self.profile_vector = np.mean(liked_embs, axis=0)



    # -------------------------
    # SCORING
    # -------------------------
    def score(self, article: Dict[str, Any]) -> float:
        """
        Score a single article using cosine similarity.
        """
        if self.profile_vector is None:
            return 0.0

        emb = self.model.encode([article["embed_text"]])[0]
        similarity = util.cos_sim(emb, self.profile_vector)

        return float(similarity)

    def score_batch(self, articles: List[Dict[str, Any]]) -> List[float]:
        """
        Efficient batch scoring.
        """
        if self.profile_vector is None or not articles:
            return [0.0] * len(articles)

        texts = [a["embed_text"] for a in articles]
        embs = self.model.encode(texts)

        scores = util.cos_sim(embs, self.profile_vector).squeeze()

        return [float(s) for s in scores]

    # -------------------------
    # RANKING
    # -------------------------
    def rank(
        self,
        articles: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        if not articles:
            return []

        scores = self.score_batch(articles)

        ranked = []
        for article, sim_score in zip(articles, scores):
            ranked.append({
                **article,
                "enjoyment_score": round(float(sim_score), 6)
            })

        ranked_sorted = sorted(ranked, key=lambda x: x["enjoyment_score"], reverse=True)

        return ranked_sorted


# -------------------------
# HELPER FUNCTIONS
# -------------------------

def rank_articles_for_user(
    articles: List[Dict[str, Any]],
    liked_articles: List[Dict[str, Any]],
    disliked_articles: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Convenience wrapper for one-off ranking.
    """

    recommender = ArticleRecommender()
    recommender.fit(liked_articles, disliked_articles)

    return recommender.rank(articles)



def build_user_profile_vector(
    liked_articles: List[Dict[str, Any]],
    disliked_articles: Optional[List[Dict[str, Any]]] = None,
) -> Optional[np.ndarray]:
    """
    If you want to persist user profiles in DB later.
    """

    model = _get_model()

    if not liked_articles:
        return None

    liked_embs = model.encode([a["embed_text"] for a in liked_articles])

    if disliked_articles:
        disliked_embs = model.encode([a["embed_text"] for a in disliked_articles])
        return np.mean(liked_embs, axis=0) - np.mean(disliked_embs, axis=0)

    return np.mean(liked_embs, axis=0)