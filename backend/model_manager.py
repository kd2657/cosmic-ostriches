"""
ModelManager: Background model initialization with status reporting.

Manages the lifecycle of ML models (SentenceTransformer, DistilGPT2) with
real-time progress reporting for frontend boot sequences. Models are loaded
in a background thread so the FastAPI server can accept requests immediately.
"""

import time
import os
from threading import Lock, Thread
from sentence_transformers import SentenceTransformer
from transformers import pipeline


class ModelManager:
    """
    Manages ML model lifecycle with status reporting for frontend boot sequences.
    Models are loaded in a background thread so the API can start immediately.
    """

    STAGES = [
        {"id": "chroma", "label": "CONNECTING TO VECTOR DATABASE", "pct": 10},
        {"id": "vectorizer", "label": "LOADING SENTENCETRANSFORMER MODEL (all-MiniLM-L6-v2)", "pct": 25},
        {"id": "summarizer", "label": "INITIALIZING NLP SUMMARIZATION PIPELINE (Falconsai T5-Small)", "pct": 45},
        {"id": "sentiment", "label": "LOADING SENTIMENT ANALYSIS MODEL (Roberta)", "pct": 65},
        {"id": "cross_encoder", "label": "LOADING CROSS-ENCODER RANKING MODEL", "pct": 85},
        {"id": "ner", "label": "LOADING NER PARAMETERIZATION MODEL", "pct": 95},
        {"id": "ready", "label": "ALL SYSTEMS ONLINE // WELCOME TO THE LOCAL MINIMA", "pct": 100}
    ]

    def __init__(self):
        self.model = None
        self.summarizer = None
        self.sentiment = None
        self.cross_encoder = None
        self.ner = None
        self._ready = False
        self._current_stage = 0
        self._stage_label = "Waiting for initialization..."
        self._pct = 0
        self._error = None
        self._lock = Lock()

    @property
    def ready(self):
        return self._ready

    def get_status(self):
        return {
            "ready": self._ready,
            "stage": self._current_stage,
            "total_stages": len(self.STAGES),
            "label": self._stage_label,
            "pct": self._pct,
            "error": self._error,
            "api_key_valid": bool(os.getenv("NEWSAPI_AI_KEY"))
        }

    def _set_stage(self, index: int):
        stage = self.STAGES[index]
        self._current_stage = index
        self._stage_label = stage["label"]
        self._pct = stage["pct"]
        print(f"[ModelManager] Stage {index + 1}/{len(self.STAGES)}: {stage['label']}")

    def initialize(self):
        """Load all models sequentially with status updates."""
        try:
            # Stage 0: ChromaDB (already done at module level, but report it)
            self._set_stage(0)
            time.sleep(0.3)  # Brief pause so the frontend can poll

            # Stage 1: SentenceTransformer vectorizer
            self._set_stage(1)
            self.model = SentenceTransformer("all-MiniLM-L6-v2")

            # Stage 2: DistilGPT2 summarizer
            self._set_stage(2)
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
            self.summarizer = {
                "model": AutoModelForSeq2SeqLM.from_pretrained("Falconsai/text_summarization"),
                "tokenizer": AutoTokenizer.from_pretrained("Falconsai/text_summarization")
            }

            # Stage 3: Sentiment Classifier
            self._set_stage(3)
            # Importing locally to avoid circular dependency if any
            from sentiment import SentimentClassifier
            self.sentiment = SentimentClassifier()

            # Stage 4: Cross Encoder
            self._set_stage(4)
            from sentence_transformers import CrossEncoder
            self.cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

            # Stage 5: NER Pipeline
            self._set_stage(5)
            self.ner = pipeline("ner", model="dslim/bert-base-NER", aggregation_strategy="simple")

            # Stage 6: Ready
            self._set_stage(6)
            self._ready = True

        except Exception as e:
            self._error = str(e)
            print(f"[ModelManager] FATAL: {e}")

    def start_background_init(self):
        """Kick off model loading in a daemon thread."""
        thread = Thread(target=self.initialize, daemon=True)
        thread.start()
