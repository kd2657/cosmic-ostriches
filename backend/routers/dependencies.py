from ml import model_manager

# Sentiment classifier is pre-loaded by ModelManager during boot sequence
def get_sentiment_classifier():
    if model_manager.sentiment is None:
        # Fallback in case a request hits before background thread finishes Stage 4
        from sentiment import SentimentClassifier
        model_manager.sentiment = SentimentClassifier()
    return model_manager.sentiment

def attach_article_sentiment(articles):
    sentiment_inputs = []
    sentiment_indexes = []

    for index, article in enumerate(articles):
        title = (article.get("title") or "").strip()
        description = (article.get("description") or "").strip()
        body = (article.get("body") or "").strip()
        combined_text = " ".join(part for part in [title, description, body] if part).strip()

        if not combined_text:
            article["sentiment"] = None
            continue

        sentiment_inputs.append(combined_text)
        sentiment_indexes.append(index)

    if not sentiment_inputs:
        return articles

    results = get_sentiment_classifier().classify_batch(sentiment_inputs)
    for index, result in zip(sentiment_indexes, results):
        articles[index]["sentiment"] = result.to_dict()

    return articles
