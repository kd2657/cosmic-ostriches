from __future__ import annotations

from dataclasses import asdict, dataclass
from threading import Lock
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

from transformers import pipeline
from transformers.pipelines.base import Pipeline

DEFAULT_SENTIMENT_MODEL = "distilbert-base-uncased-finetuned-sst-2-english"


@dataclass(frozen=True)
class SentimentResult:
    text: str
    label: str
    sentiment: str
    confidence: float
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
        prepared_text = self._prepare_text(text)
        raw_result = self._run_pipeline([prepared_text])[0]
        return self._build_result(prepared_text, raw_result)

    def classify_batch(self, texts: Sequence[str]) -> List[SentimentResult]:
        prepared_texts = [self._prepare_text(text) for text in texts]
        if not prepared_texts:
            return []

        raw_results = self._run_pipeline(prepared_texts)
        return [
            self._build_result(text, raw_result)
            for text, raw_result in zip(prepared_texts, raw_results)
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
        raw_result: List[Dict[str, Union[str, float]]],
    ) -> SentimentResult:
        if not raw_result:
            raise ValueError("Sentiment model returned no scores.")

        scores = {
            self._normalize_label(str(item["label"])): round(float(item["score"]), 6)
            for item in raw_result
        }
        label, confidence = max(scores.items(), key=lambda item: item[1])

        return SentimentResult(
            text=text,
            label=label.upper(),
            sentiment=label,
            confidence=round(confidence, 6),
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

    def _normalize_label(self, label: str) -> str:
        return label.strip().lower()
