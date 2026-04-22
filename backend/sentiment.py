from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from threading import Lock
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

from transformers import pipeline
from transformers.pipelines.base import Pipeline

DEFAULT_SENTIMENT_MODEL = os.environ.get(
    "SENTIMENT_MODEL",
    "cardiffnlp/twitter-roberta-base-sentiment-latest",
)
STRONG_SENTIMENT_THRESHOLD = float(os.environ.get("SENTIMENT_STRONG_THRESHOLD", "0.25"))


@dataclass(frozen=True)
class SentimentResult:
    text: str
    label: str
    sentiment: str
    confidence: float
    polarity: float
    scores: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SentimentClassifier:
    """
    Reusable sentiment classifier for article text, headlines, and summaries.

    Example:
        classifier = SentimentClassifier()
        result = classifier.classify("Markets rally after inflation cools.")
        batch = classifier.classify_batch(["Stocks rise.", "Layoffs expand."])
    """

    def __init__(
        self,
        model_name: str = DEFAULT_SENTIMENT_MODEL,
        batch_size: int = 16,
        max_length: int = 512,
        device: Optional[int] = None,
        pipeline_instance: Optional[Pipeline] = None,
    ) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self.max_length = max_length
        self._lock = Lock()
        self._pipeline = pipeline_instance or pipeline(
            task="sentiment-analysis",
            model=model_name,
            tokenizer=model_name,
            device=device,
        )

    def classify(self, text: str) -> SentimentResult:
        return self.classify_batch([text])[0]

    def classify_batch(self, texts: Sequence[str]) -> List[SentimentResult]:
        prepared_texts = [self._prepare_text(text) for text in texts]
        if not prepared_texts:
            return []

        chunk_texts: List[str] = []
        chunk_indexes: List[int] = []
        chunk_weights: List[float] = []

        for index, text in enumerate(prepared_texts):
            for chunk_index, chunk in enumerate(self._chunk_text(text)):
                chunk_texts.append(chunk)
                chunk_indexes.append(index)
                chunk_weights.append(1.5 if chunk_index == 0 else 1.0)

        raw_results = self._run_pipeline(chunk_texts)
        scored_chunks: List[List[tuple[float, Dict[str, float]]]] = [
            [] for _ in prepared_texts
        ]

        for doc_index, weight, raw_result in zip(chunk_indexes, chunk_weights, raw_results):
            scored_chunks[doc_index].append((weight, self._scores_from_raw(raw_result)))

        return [
            self._build_result(text, chunks)
            for text, chunks in zip(prepared_texts, scored_chunks)
        ]

    def classify_many(
        self, texts: Iterable[str], chunk_size: Optional[int] = None
    ) -> List[SentimentResult]:
        batch_limit = chunk_size or self.batch_size
        buffered_texts: List[str] = []
        results: List[SentimentResult] = []

        for text in texts:
            buffered_texts.append(text)
            if len(buffered_texts) >= batch_limit:
                results.extend(self.classify_batch(buffered_texts))
                buffered_texts.clear()

        if buffered_texts:
            results.extend(self.classify_batch(buffered_texts))

        return results

    def classify_records(
        self,
        records: Sequence[Dict[str, Any]],
        text_key: str = "text",
        output_key: str = "sentiment",
    ) -> List[Dict[str, Any]]:
        texts = [self._prepare_text(self._extract_record_text(record, text_key)) for record in records]
        results = self.classify_batch(texts)

        enriched_records: List[Dict[str, Any]] = []
        for record, result in zip(records, results):
            enriched_record = dict(record)
            enriched_record[output_key] = result.to_dict()
            enriched_records.append(enriched_record)

        return enriched_records

    def _run_pipeline(self, texts: Sequence[str]) -> List[List[Dict[str, Union[str, float]]]]:
        # The lock keeps model inference predictable if the classifier is shared
        # across request handlers or background jobs.
        with self._lock:
            outputs = self._pipeline(
                list(texts),
                batch_size=self.batch_size,
                truncation=True,
                max_length=self.max_length,
                top_k=None,
            )

        if not isinstance(outputs, list):
            raise TypeError("Unexpected sentiment pipeline output type.")

        normalized_outputs: List[List[Dict[str, Union[str, float]]]] = []
        for item in outputs:
            if isinstance(item, dict):
                normalized_outputs.append([item])
            else:
                normalized_outputs.append(item)

        return normalized_outputs

    def _build_result(
        self,
        text: str,
        scored_chunks: List[tuple[float, Dict[str, float]]],
    ) -> SentimentResult:
        if not scored_chunks:
            raise ValueError("Sentiment model returned no scores.")

        scores = self._weighted_average_scores(scored_chunks)
        polarity = self._calculate_polarity(scores)
        sentiment, label = self._bucket_sentiment(polarity)
        confidence = max(scores.values())

        return SentimentResult(
            text=text,
            label=label,
            sentiment=sentiment,
            confidence=round(confidence, 6),
            polarity=round(polarity, 6),
            scores=scores,
        )

    def _extract_record_text(self, record: Dict[str, Any], text_key: str) -> str:
        value = record.get(text_key)
        if value is None:
            raise KeyError(f"Record is missing required text key: {text_key}")
        return self._prepare_text(value)

    def _prepare_text(self, text: Any) -> str:
        if not isinstance(text, str):
            raise TypeError("Sentiment input must be a string.")

        normalized_text = " ".join(text.split())
        if not normalized_text:
            raise ValueError("Sentiment input cannot be empty.")

        return normalized_text

    def _chunk_text(self, text: str, words_per_chunk: int = 140, max_chunks: int = 6) -> List[str]:
        words = text.split()
        if len(words) <= words_per_chunk:
            return [text]

        chunks = [
            " ".join(words[index:index + words_per_chunk])
            for index in range(0, len(words), words_per_chunk)
        ]
        return chunks[:max_chunks]

    def _scores_from_raw(
        self,
        raw_result: List[Dict[str, Union[str, float]]],
    ) -> Dict[str, float]:
        if not raw_result:
            raise ValueError("Sentiment model returned no scores.")

        return {
            self._normalize_label(str(item["label"])): round(float(item["score"]), 6)
            for item in raw_result
        }

    def _weighted_average_scores(
        self,
        scored_chunks: List[tuple[float, Dict[str, float]]],
    ) -> Dict[str, float]:
        labels = {
            label
            for _, scores in scored_chunks
            for label in scores
        }
        total_weight = sum(weight for weight, _ in scored_chunks)

        return {
            label: round(
                sum(weight * scores.get(label, 0.0) for weight, scores in scored_chunks) / total_weight,
                6,
            )
            for label in labels
        }

    def _normalize_label(self, label: str) -> str:
        normalized = label.strip().lower().replace("-", "_")
        label_aliases = {
            "label_0": "negative",
            "0": "negative",
            "neg": "negative",
            "neu": "neutral",
            "label_2": "positive",
            "2": "positive",
            "pos": "positive",
        }

        if normalized in ("label_1", "1"):
            if "cardiffnlp/twitter_roberta_base_sentiment" in self.model_name.replace("-", "_"):
                return "neutral"
            return "positive"

        return label_aliases.get(normalized, normalized)

    def _calculate_polarity(self, scores: Dict[str, float]) -> float:
        positive_score = scores.get("positive", 0.0)
        negative_score = scores.get("negative", 0.0)

        if "positive" in scores or "negative" in scores:
            return max(-1.0, min(1.0, positive_score - negative_score))

        label, confidence = max(scores.items(), key=lambda item: item[1])
        return -confidence if label == "negative" else confidence

    def _bucket_sentiment(self, polarity: float) -> tuple[str, str]:
        if polarity >= STRONG_SENTIMENT_THRESHOLD:
            return "positive", "Positive"
        if polarity >= 0:
            return "slightly_positive", "Slightly Positive"
        if polarity > -STRONG_SENTIMENT_THRESHOLD:
            return "slightly_negative", "Slightly Negative"
        return "negative", "Negative"
