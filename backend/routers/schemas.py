from typing import Optional

from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str
    algorithm: Optional[str] = "hdbscan"  # "hdbscan", "kmeans", "gmm", "agglomerative", "affinity"
    k: Optional[int] = None
    dim_reduction: str = "umap"
    force_local: Optional[bool] = False
    use_sentiment: Optional[bool] = False
    include_bodies: Optional[bool] = False
    parameterize_query: Optional[bool] = False


class ArticleRequest(BaseModel):
    query: str
    force_local: Optional[bool] = False
    use_sentiment: Optional[bool] = False
    include_bodies: Optional[bool] = False
    parameterize_query: Optional[bool] = False


class VoteRequest(BaseModel):
    article_id: str
    vote: Optional[str] = None  # "up", "down", or null (cleared)
