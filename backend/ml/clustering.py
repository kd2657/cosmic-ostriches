import numpy as np
from typing import Optional
from sklearn.cluster import AffinityPropagation, AgglomerativeClustering, HDBSCAN
from sklearn.mixture import GaussianMixture

class CustomKMeans:
    def __init__(self, n_clusters=8, max_iter=100, random_state=None):
        self.n_clusters = n_clusters
        self.max_iter = max_iter
        if random_state is not None:
            np.random.seed(random_state)
            
    def fit_predict(self, X):
        if len(X) <= self.n_clusters:
            return np.arange(len(X))
        indices = np.random.choice(X.shape[0], self.n_clusters, replace=False)
        centroids = X[indices].copy()
        
        labels = np.zeros(X.shape[0])
        for _ in range(self.max_iter):
            # Form computationally clean 3D broadcast matrix for bulk Euclidean vector distance comparison
            distances = np.linalg.norm(X[:, np.newaxis] - centroids, axis=2)
            new_labels = np.argmin(distances, axis=1)
            
            if np.array_equal(labels, new_labels):
                break
            labels = new_labels
            
            for k in range(self.n_clusters):
                if np.sum(labels == k) > 0:
                    centroids[k] = np.mean(X[labels == k], axis=0)
                    
        return labels


def _get_cluster_labels(embeddings: np.ndarray, method: str, cluster_k: Optional[int]) -> np.ndarray:
    """Internal helper to apply clustering algorithm."""
    if method == "kmeans" and cluster_k:
        k = min(cluster_k, len(embeddings))
        return CustomKMeans(n_clusters=k, random_state=42).fit_predict(embeddings)
    elif method == "gmm" and cluster_k:
        k = min(cluster_k, len(embeddings))
        return GaussianMixture(n_components=k, random_state=42).fit_predict(embeddings)
    elif method == "agglomerative":
        k = min(cluster_k, len(embeddings)) if cluster_k else None
        agg = AgglomerativeClustering(n_clusters=k) if k else AgglomerativeClustering(n_clusters=None, distance_threshold=0.5)
        return agg.fit_predict(embeddings)
    elif method == "affinity":
        return AffinityPropagation(random_state=42).fit_predict(embeddings)
    else:
        min_cluster = min(len(embeddings), 3)
        if len(embeddings) < 3:
            return np.zeros(len(embeddings), dtype=int)
        return HDBSCAN(min_cluster_size=min_cluster, min_samples=2).fit_predict(embeddings)

