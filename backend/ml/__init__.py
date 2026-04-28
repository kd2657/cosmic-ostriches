import os
import warnings
from threading import Lock
from typing import Any, Dict, List, Optional

import numpy as np
from google import genai
from transformers import logging as transformers_logging

from model_manager import ModelManager
from .clustering import CustomKMeans, _get_cluster_labels
from .db import collection
from .dimensionality import CustomPCA, _get_reduced_embeddings
from .global_metrics import compute_global_divergence, compute_source_divergence
from .gradient import farthest_point_sampling, maximal_marginal_relevance, process_daily_gradient

# Suppress noisy model-loading warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="sklearn.*")
warnings.filterwarnings("ignore", category=UserWarning, module="umap.*")
warnings.filterwarnings("ignore", module="transformers.*")
transformers_logging.set_verbosity_error()

# Singleton model manager — created immediately, but models load in background
model_manager = ModelManager()

# UMAP relies on Numba's workqueue threading layer in this environment, which
# can abort the process if multiple FastAPI threads enter it concurrently.
_cluster_pipeline_lock = Lock()

# Sentiment/Narrative Logic Constants
TONE_NEUTRAL_THRESHOLD = 0.10
STABILITY_MIXED_THRESHOLD = 0.03
STABILITY_POLARIZED_THRESHOLD = 0.15


def _get_model():
    """Proxy for the singleton model manager's vectorizer."""
    if not model_manager.model:
        # If not loaded yet, force synchronous load (safe due to singleton)
        model_manager.initialize()
    return model_manager.model


def _get_summarizer():
    """Proxy for the singleton model manager's local NLP pipeline."""
    return model_manager.summarizer


def _classify_cluster_tone(mean_polarity: float) -> str:
    if mean_polarity > TONE_NEUTRAL_THRESHOLD:
        return "Positive"
    if mean_polarity < -TONE_NEUTRAL_THRESHOLD:
        return "Negative"
    return "Neutral"


def _classify_cluster_stability(variance: float) -> str:
    if variance < STABILITY_MIXED_THRESHOLD:
        return "Stable"
    if variance < STABILITY_POLARIZED_THRESHOLD:
        return "Mixed"
    return "Highly Polarized"


def _compute_cluster_sentiment_stats(cluster_polarities: Dict[int, List[float]]) -> Dict[str, Dict[str, Any]]:
    stats = {}
    for cluster_id, polarities in cluster_polarities.items():
        if cluster_id == -1 or not polarities:
            continue

        mean_polarity = float(np.mean(polarities))
        variance = float(np.var(polarities))
        stats[str(cluster_id)] = {
            "tone": _classify_cluster_tone(mean_polarity),
            "stability": _classify_cluster_stability(variance),
            "mean_polarity": round(mean_polarity, 3),
            "polarity_variance": round(variance, 3),
            "article_count": len(polarities),
        }

    return stats

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
        embeddings = _get_model().encode(texts_to_embed).tolist()
        
        ids = [a["id"] for a in new_articles]
        metadatas = [{
            "title": a.get("title") or "",
            "url": a.get("url") or "",
            "source": a.get("source") or "",
            "country": a.get("country") or "",
            "body": a.get("body") or "",
            "category": a.get("category") or "General",
            "publish_date": a.get("publish_date") or ""
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
        
    query_embedding = _get_model().encode([query_text]).tolist()
    
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
                "body": meta.get("body", ""),
                "url": meta.get("url", ""),
                "source": meta.get("source", ""),
                "category": meta.get("category", "General"),
                "publish_date": meta.get("publish_date", ""),
                "embed_text": f"{meta.get('title', '')}. {meta.get('body', '') or meta.get('description', '')}"
            })
            
    return articles

def compute_similarity_scores(query: str, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Calculates cosine similarity matching-percentages between vector states."""
    if not articles:
        return []
    
    cross_encoder = model_manager.cross_encoder
    
    # 1. Format pairs for the Cross-Encoder: (Query, Article Text)
    pairs = [[query, a.get("embed_text", f"{a.get('title', '')}. {a.get('body', '')}")] for a in articles]
    
    # 2. Predict relevance scores
    scores = cross_encoder.predict(pairs)
    
    # 3. Apply sigmoid to convert logits to a 0-100% confidence scale
    for idx, a in enumerate(articles):
        score = 1.0 / (1.0 + np.exp(-scores[idx])) 
        a["match_score"] = round(float(score) * 100, 1)
        
    articles.sort(key=lambda x: x["match_score"], reverse=True)
    return articles

def extract_query_parameters(query: str) -> Dict[str, Optional[str]]:
    if not query.strip():
        return {"location": None, "time": None}

    ner_pipeline = model_manager.ner
    entities = []
    if ner_pipeline:
        try:
            print(f"[ML] Running NER on query: {query}")
            entities = ner_pipeline(query)
        except Exception as e:
            print(f"[ML] NER extraction failed for query '{query}': {e}")
    
    locations = []
    for ent in entities:
        # Robustly handle different NER output formats (entity_group vs entity)
        label = ent.get("entity_group") or ent.get("entity") or ""
        if "LOC" in label:
            word = ent.get("word", "")
            if word:
                locations.append(word.replace("##", ""))
            
    time_keywords = ["today", "yesterday", "last week", "last month", "this week", "this month", "2023", "2024", "2025"]
    extracted_time = None
    for tk in time_keywords:
        if tk in query.lower():
            extracted_time = tk
            break
            
    loc_str = " ".join(locations) if locations else None
    
    return {
        "location": loc_str,
        "time": extracted_time
    }

def _generate_narrative_summaries(cluster_texts: Dict[int, List[str]], client: Optional[genai.Client], target_clusters: List[int]) -> tuple[Dict[str, Any], bool]:
    """Internal helper to generate summaries using Gemini, OpenAI, or local fallback."""
    summaries = {}
    cluster_strings = ""
    for cluster_id in cluster_texts:
        if cluster_id == -1:
            summaries["-1"] = "Unclustered noise and outlier narratives."
            continue
        if cluster_id in target_clusters:
            top_texts_str = "\n---\n".join(cluster_texts[cluster_id][:5])
            cluster_strings += f"Cluster {cluster_id}:\n{top_texts_str}\n\n"

    summary_generated = False
    used_local_fallback = False if client else True

    if client and target_clusters:
        try:
            prompt = (
                f"You are an analytical AI bot. Read the following sets of news reporting grouped by narrative. "
                f"Provide a short title and a strict 2-sentence summary for each narrative. "
                f"The first sentence should summarize the core narrative. "
                f"The second sentence MUST explicitly focus on what makes this particular narrative different from the others. "
                f"Avoid using the word 'cluster' in your response. "
                f"Return your response STRICTLY as a valid JSON object where each KEY is the plain narrative number as a string (e.g. \"0\", \"1\", \"2\") "
                f"and each VALUE is a nested object containing two string fields: \"title\" and \"summary\". "
                f"Ensure all text values are properly escaped and contain absolutely NO literal newlines. \n\n{cluster_strings}"
            )
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    temperature=0.3, max_output_tokens=8192, response_mime_type="application/json"
                )
            )
            import json
            json_text = response.text.strip()
            if "```json" in json_text: json_text = json_text.split("```json")[1].split("```")[0].strip()
            elif "```" in json_text: json_text = json_text.split("```")[1].split("```")[0].strip()
            elif "{" in json_text and "}" in json_text:
                json_text = json_text[json_text.find("{"):json_text.rfind("}")+1]
            
            batch_summaries = json.loads(json_text)
            for cid in target_clusters:
                summary = batch_summaries.get(str(cid)) or batch_summaries.get(f"Cluster {cid}") or batch_summaries.get(f"Narrative {cid}")
                summaries[str(cid)] = summary if summary else "Narrative summary unavailable."
            summary_generated = True
        except Exception as e:
            print(f"Gemini Error: {e}")

    if not summary_generated:
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and target_clusters:
            try:
                from openai import OpenAI
                import json
                openai_client = OpenAI(api_key=openai_key)
                prompt = (
                    f"You are an analytical AI bot. Read the following sets of news reporting grouped by narrative. "
                    f"Provide a short title and a strict 2-sentence summary for each narrative. "
                    f"The first sentence should summarize the core narrative. "
                    f"The second sentence MUST explicitly focus on what makes this particular narrative different from the others. "
                    f"Avoid using the word 'cluster' in your response. "
                    f"Return your response STRICTLY as a valid JSON object where each KEY is the plain narrative number as a string (e.g. \"0\", \"1\", \"2\") "
                    f"and each VALUE is a nested object containing two string fields: \"title\" and \"summary\". "
                    f"Ensure all text values are properly escaped and contain absolutely NO literal newlines. \n\n{cluster_strings}"
                )
                response = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=2048,
                    response_format={"type": "json_object"}
                )
                json_text = response.choices[0].message.content.strip()
                batch_summaries = json.loads(json_text)
                for cid in target_clusters:
                    summary = batch_summaries.get(str(cid)) or batch_summaries.get(f"Cluster {cid}") or batch_summaries.get(f"Narrative {cid}")
                    summaries[str(cid)] = summary if summary else "Narrative summary unavailable."
                summary_generated = True
                used_local_fallback = False
                print("Used OpenAI fallback for summaries.")
            except Exception as e:
                print(f"OpenAI Error: {e}")

    if not summary_generated:
        used_local_fallback = True
        summarizer = _get_summarizer()
        for cid in target_clusters:
            input_text = cluster_texts[cid][0][:500] if cluster_texts.get(cid) else "Global news."
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                inputs = summarizer["tokenizer"](f"summarize: {input_text}", return_tensors="pt", max_length=512, truncation=True)
                outputs = summarizer["model"].generate(**inputs, max_length=60, min_length=10, do_sample=False)
            generated = summarizer["tokenizer"].decode(outputs[0], skip_special_tokens=True).strip()
            summaries[str(cid)] = generated

    return summaries, used_local_fallback

def process_batch_cluster(
    articles: List[Dict[str, Any]], 
    method: str = "hdbscan", 
    cluster_k: Optional[int] = None,
    dim_reduction: str = "umap"
) -> Dict[str, Any]:
    """
    Fetches embeddings, performs UMAP dimensionality reduction to 2D for the UI,
    and applies the chosen clustering algorithm.
    """
    if not articles:
        return {"points": [], "summaries": {}, "nds_scores": {}, "cluster_sentiment": {}, "is_local_summary": False}
    
    # Retrieve
    ids = [a["id"] for a in articles]
    data = collection.get(ids=ids, include=["embeddings", "metadatas"])
    
    if data.get("embeddings") is None or len(data["embeddings"]) == 0:
        return {"points": [], "summaries": {}, "nds_scores": {}, "cluster_sentiment": {}, "is_local_summary": False}
    
    embeddings = np.array(data["embeddings"])

    with _cluster_pipeline_lock:
        labels = _get_cluster_labels(embeddings, method, cluster_k)
        reduced_embeddings = _get_reduced_embeddings(embeddings, dim_reduction)

    from models.metrics import compute_article_distances_from_center  # noqa: PLC0415
    article_distances = compute_article_distances_from_center(embeddings, np.array(labels))

    sentiment_by_id = {a.get("id"): a.get("sentiment") for a in articles}

    # Build response points
    results = []
    cluster_texts = {}
    cluster_polarities = {}
    
    gemini_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=gemini_key) if gemini_key else None
    
    for idx, article_id in enumerate(ids):
        meta = data["metadatas"][idx]
        cluster_id = int(labels[idx])
        sentiment = sentiment_by_id.get(article_id)
        
        if cluster_id not in cluster_texts:
            cluster_texts[cluster_id] = []
        if cluster_id not in cluster_polarities:
            cluster_polarities[cluster_id] = []

        if sentiment and sentiment.get("polarity") is not None:
            try:
                cluster_polarities[cluster_id].append(float(sentiment.get("polarity")))
            except (TypeError, ValueError):
                pass
            
        t, b = meta.get("title", ""), meta.get("body", "")
        chunk = b[:2500] if client else b[:200]
        cluster_texts[cluster_id].append(f"{t}: {chunk}" if b else t)
            
        results.append({
            "id": article_id,
            "title": meta.get("title", "Unknown"),
            "description": meta.get("description", ""),
            "url": meta.get("url", ""),
            "source": meta.get("source", ""),
            "body": meta.get("body", ""),
            "publish_date": meta.get("publish_date", ""),
            "sentiment": sentiment,
            "cluster": cluster_id,
            "x": float(reduced_embeddings[idx][0]),
            "y": float(reduced_embeddings[idx][1]),
            "distance_from_center": round(float(article_distances[idx]), 3) if cluster_id != -1 else 0.0
        })
        
    target_clusters = [cid for cid in cluster_texts if cid != -1]
    summaries, used_local_fallback = _generate_narrative_summaries(cluster_texts, client, target_clusters)
        
    from models.metrics import compute_narrative_diversity_score, compute_clustering_eval_metrics  # noqa: PLC0415
    nds_scores = compute_narrative_diversity_score(embeddings, np.array(labels))
    cluster_sentiment = _compute_cluster_sentiment_stats(cluster_polarities)
    
    eval_metrics = compute_clustering_eval_metrics(embeddings, np.array(labels), nds_scores)
            
    return {
        "points": results, 
        "summaries": summaries,
        "nds_scores": nds_scores,
        "cluster_sentiment": cluster_sentiment,
        "is_local_summary": used_local_fallback,
        "eval_metrics": eval_metrics
    }

def get_article_by_id(article_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single article by its explicit ID from ChromaDB."""
    results = collection.get(ids=[article_id], include=["metadatas"])
    if results and results["ids"] and len(results["ids"]) > 0:
        meta = results["metadatas"][0]
        return {
            "id": results["ids"][0],
            "title": meta.get("title", "Unknown"),
            "description": meta.get("description", ""),
            "url": meta.get("url", ""),
            "source": meta.get("source", ""),
            "body": meta.get("body", ""),
            "publish_date": meta.get("publish_date", ""),
            "category": meta.get("category", "General"),
            "country": meta.get("country", "")
        }
    return None

def get_articles_by_ids(article_ids: List[str]) -> List[Dict[str, Any]]:
    """Retrieve multiple articles by their explicit IDs from ChromaDB."""
    if not article_ids:
        return []
    results = collection.get(ids=article_ids, include=["metadatas"])
    articles = []
    if results and results["ids"]:
        for idx, uid in enumerate(results["ids"]):
            meta = results["metadatas"][idx]
            articles.append({
                "id": uid,
                "title": meta.get("title", "Unknown"),
                "description": meta.get("description", ""),
                "url": meta.get("url", ""),
                "source": meta.get("source", ""),
                "body": meta.get("body", ""),
                "publish_date": meta.get("publish_date", ""),
                "category": meta.get("category", "General"),
                "country": meta.get("country", "")
            })
    return articles


