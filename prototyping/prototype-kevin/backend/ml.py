import os
import chromadb
from umap import UMAP
from sentence_transformers import SentenceTransformer, util
from sklearn.cluster import KMeans, HDBSCAN
from sklearn.mixture import GaussianMixture
from transformers import pipeline
from typing import List, Dict, Any, Optional
import numpy as np
import warnings

warnings.filterwarnings("ignore", category=FutureWarning, module="sklearn.*")
warnings.filterwarnings("ignore", category=UserWarning, module="umap.*")
warnings.filterwarnings("ignore", module="transformers.*")

# Load the vectorizer model
# all-MiniLM-L6-v2 is selected to balance performance with low compute 
print("Loading model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

print("Loading LLM summarization pipeline (Offline NLP)...")
summarizer = pipeline("text-generation", model="distilgpt2")

# Initialize ChromaDB persistent client locally
CHROMA_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")
os.makedirs(CHROMA_PATH, exist_ok=True)
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma_client.get_or_create_collection(name="news_narratives")

def vectorize_and_store(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Takes cleaned articles, checks if they exist in ChromaDB, 
    embeds them if not, and stores them. Returns the full local metadata bundle.
    """
    if not articles:
        return []

    stored_ids = collection.get(ids=[a["id"] for a in articles])["ids"]
    new_articles = [a for a in articles if a["id"] not in stored_ids]

    if new_articles:
        texts_to_embed = [a["embed_text"] for a in new_articles]
        embeddings = model.encode(texts_to_embed).tolist()
        
        ids = [a["id"] for a in new_articles]
        metadatas = [{
            "title": a["title"],
            "url": a.get("url", ""),
            "source": a.get("source", ""),
            "description": a.get("description", ""),
            "publish_date": a.get("publish_date", "")
        } for a in new_articles]
        
        collection.add(
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas,
            documents=texts_to_embed
        )

    return articles

def fetch_vectors(article_ids: List[str]):
    """Fetch stored embeddings directly from ChromaDB."""
    return collection.get(ids=article_ids, include=["embeddings", "metadatas"])

def query_local_database(query_text: str, n_results: int = 50) -> List[Dict[str, Any]]:
    """
    Fallback method: Embeds the search query and searches the local ChromaDB 
    for the semantically closest existing articles when the API fails.
    """
    if collection.count() == 0:
        return []
        
    query_embedding = model.encode([query_text]).tolist()
    
    # Query ChromaDB (returns Dict of lists)
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=min(n_results, collection.count())
    )
    
    articles = []
    if results and results["ids"] and len(results["ids"]) > 0:
        ids_list = results["ids"][0]
        metadatas_list = results["metadatas"][0]
        
        for i, uid in enumerate(ids_list):
            meta = metadatas_list[i]
            articles.append({
                "id": uid,
                "title": meta.get("title", "Unknown"),
                "description": meta.get("description", ""),
                "url": meta.get("url", ""),
                "source": meta.get("source", ""),
                "publish_date": meta.get("publish_date", ""),
                "embed_text": f"{meta.get('title', '')}. {meta.get('description', '')}"
            })
            
    return articles

def compute_similarity_scores(query: str, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Calculates cosine similarity matching-percentages between vector states."""
    if not articles:
        return []
    
    # Do not force convert to PyTorch tensor here so numpy can bridge them safely
    query_emb = model.encode(query)
    
    ids = [a["id"] for a in articles]
    data = collection.get(ids=ids, include=["embeddings"])
    
    if data.get("embeddings") is None or len(data["embeddings"]) == 0:
        for a in articles:
            a["match_score"] = 0
        return articles
        
    # Cast explicitly to float32 to match the model's 32-bit dimension typing
    doc_embs = np.array(data["embeddings"], dtype=np.float32)
    cosine_scores = util.cos_sim(query_emb, doc_embs)[0]
    
    for idx, a in enumerate(articles):
        score = float(cosine_scores[idx]) * 100
        a["match_score"] = round(max(0, min(100, score)), 1)
        
    articles.sort(key=lambda x: x["match_score"], reverse=True)
    return articles

def process_batch_cluster(
    articles: List[Dict[str, Any]], 
    method: str = "hdbscan", 
    cluster_k: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Fetches embeddings, performs UMAP dimensionality reduction to 2D for the UI,
    and applies the chosen clustering algorithm.
    """
    if not articles:
        return []
    
    # Retrieve
    ids = [a["id"] for a in articles]
    data = collection.get(ids=ids, include=["embeddings", "metadatas"])
    
    if data.get("embeddings") is None or len(data["embeddings"]) == 0:
        return []
    
    embeddings = np.array(data["embeddings"])
    
    # Clustering
    labels = []
    if method == "kmeans" and cluster_k:
        k = min(cluster_k, len(embeddings))
        kmeans = KMeans(n_clusters=k, random_state=42)
        labels = kmeans.fit_predict(embeddings)
    elif method == "gmm" and cluster_k:
        k = min(cluster_k, len(embeddings))
        gmm = GaussianMixture(n_components=k, random_state=42)
        labels = gmm.fit_predict(embeddings)
    else:
        # Fallback to HDBSCAN
        # Works well when k is unknown. minimum cluster size determines sensitivity.
        min_cluster = min(len(embeddings), 5)
        if len(embeddings) < 5:
            labels = [0] * len(embeddings) # not enough data to cluster
        else:
            hdb = HDBSCAN(min_cluster_size=min_cluster)
            labels = hdb.fit_predict(embeddings)

    # UMAP Reduction for 2D Plotting
    # Needs a few points to work properly (n_neighbors=15 default). 
    n_neighbors = min(15, len(embeddings) - 1)
    if n_neighbors < 2:
        reduced_embeddings = np.zeros((len(embeddings), 2))
    else:
        reducer = UMAP(n_neighbors=n_neighbors, min_dist=0.1, n_components=2, random_state=42)
        reduced_embeddings = reducer.fit_transform(embeddings)

    # Build response points
    results = []
    cluster_titles = {}
    for idx, article_id in enumerate(ids):
        meta = data["metadatas"][idx]
        cluster_id = int(labels[idx])
        
        # Accumulate titles for AI summary
        if cluster_id not in cluster_titles:
            cluster_titles[cluster_id] = []
        cluster_titles[cluster_id].append(meta.get("title", ""))
            
        results.append({
            "id": article_id,
            "title": meta.get("title", "Unknown"),
            "url": meta.get("url", ""),
            "source": meta.get("source", ""),
            "description": meta.get("description", ""),
            "cluster": cluster_id,
            "x": float(reduced_embeddings[idx][0]),
            "y": float(reduced_embeddings[idx][1])
        })
        
    # Generate Narratives using local LLM
    summaries = {}
    for cluster_id, titles in cluster_titles.items():
        if cluster_id == -1:
            summaries[str(cluster_id)] = "Unclustered noise and outlier narratives."
            continue
            
        # Join top 5 titles 
        top_titles_str = ". ".join(titles[:5])
        prompt = f"Summarize the main common theme of these news headlines in one short sentence:\n{top_titles_str}\n\nSummary:"
        
        try:
            # Text-generation kwargs optimized for standard causallms
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                out = summarizer(
                    prompt, 
                    max_new_tokens=25, 
                    max_length=None,
                    temperature=0.3, 
                    do_sample=True,
                    return_full_text=False,
                    pad_token_id=50256 # distilgpt2 eos token id
                )
            generated = out[0]["generated_text"].strip()
            if "\n" in generated: 
                generated = generated.split("\n")[0]
            summaries[str(cluster_id)] = generated
        except Exception as e:
            summaries[str(cluster_id)] = "Narrative summary unavailable."
            
    return {"points": results, "summaries": summaries}
