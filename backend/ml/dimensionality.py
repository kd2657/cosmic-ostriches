import numpy as np
from typing import Optional
from sklearn.manifold import TSNE
from umap import UMAP

class CustomPCA:
    """
    From-scratch PCA implementation using numpy SVD.
    Centers the data, computes the covariance matrix, and projects onto 
    the top n_components principal axes via eigendecomposition.
    Mathematically equivalent to sklearn PCA at this scale.
    """
    def __init__(self, n_components: int = 2):
        self.n_components = n_components
        self.components_ = None
        self.mean_ = None
        
    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        # Step 1: Center the data
        self.mean_ = np.mean(X, axis=0)
        X_centered = X - self.mean_
        
        # Step 2: SVD decomposition (numerically more stable than direct eigen on covariance)
        # U: left singular vectors (sample projections)
        # S: singular values
        # Vt: right singular vectors (principal axes / components)
        _, _, Vt = np.linalg.svd(X_centered, full_matrices=False)
        
        # Step 3: Store top n_components principal axes and project
        self.components_ = Vt[:self.n_components]
        return X_centered @ self.components_.T


def _get_reduced_embeddings(embeddings: np.ndarray, dim_reduction: str) -> np.ndarray:
    """Internal helper for 2D dimensionality reduction."""
    if dim_reduction == "tsne" and len(embeddings) > 1:
        perplexity = min(30, max(1, len(embeddings) - 1))
        reducer = TSNE(n_components=2, perplexity=perplexity, random_state=42, init='pca', learning_rate='auto')
        return reducer.fit_transform(embeddings)
    elif dim_reduction == "pca":
        return CustomPCA(n_components=2).fit_transform(embeddings)
    else:
        n_neighbors = min(15, len(embeddings) - 1)
        if n_neighbors < 2:
            return np.zeros((len(embeddings), 2))
        return UMAP(n_neighbors=n_neighbors, min_dist=0.1, n_components=2, random_state=42).fit_transform(embeddings)

