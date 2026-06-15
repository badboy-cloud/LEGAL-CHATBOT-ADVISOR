import json
import numpy as np
from pathlib import Path
from typing import Tuple, Dict, List
from src.ml.inlegalbert_engine import InLegalBERTEngine
from src.utils.logger import LegalAdvisorLogger


class LegalTopicClassifier:
    """
    Hybrid topic classifier combining embedding similarity and keyword matching.
    Scoring: 0.6 * embedding_similarity + 0.4 * keyword_score
    """

    def __init__(self, inlegalbert_engine: InLegalBERTEngine = None, data_dir: str = "data"):
        """
        Initialize topic classifier

        Args:
            inlegalbert_engine: Initialized InLegalBERT engine
            data_dir: Directory containing topic_mapping.json
        """
        if inlegalbert_engine is None:
            from src.ml.inlegalbert_engine import InLegalBERTEngine
            inlegalbert_engine = InLegalBERTEngine()
        self.engine = inlegalbert_engine
        self.data_dir = Path(data_dir)

        # Load topic mapping with keywords
        topic_file = self.data_dir / "topic_mapping.json"
        with open(topic_file, "r") as f:
            self.topic_mapping = json.load(f)

        # Create embedding representations for each topic
        self.topic_embeddings = self._create_topic_embeddings()

        # Extract keywords for keyword matching
        self.topic_keywords = {
            topic: data["keywords"] for topic, data in self.topic_mapping.items()
        }

        print(f"Topic classifier initialized with {len(self.topic_mapping)} topics")

    def _create_topic_embeddings(self) -> Dict[str, np.ndarray]:
        """
        Create embedding representations for each topic using keywords and description

        Returns:
            Dictionary mapping topic to its embedding
        """
        topic_embeddings = {}

        for topic, data in self.topic_mapping.items():
            # Combine keywords and description for embedding
            text = data["description"]
            keywords_text = " ".join(data["keywords"][:5])  # Top 5 keywords
            combined_text = f"{text}. Key terms: {keywords_text}"

            embedding = self.engine.encode(combined_text)
            topic_embeddings[topic] = embedding[0]  # Single embedding for topic

        return topic_embeddings

    def _keyword_score(self, query: str) -> Dict[str, float]:
        """
        Compute keyword matching score for each topic
        
        Args:
            query: User query
            
        Returns:
            Dictionary mapping topic to keyword score (0-1)
        """
        query_lower = query.lower()
        keyword_scores = {}

        for topic, keywords in self.topic_keywords.items():
            # Count keyword matches
            matches = sum(1 for keyword in keywords if keyword.lower() in query_lower)

            # Proportional scoring (1 match = 0.6, 2 matches = 0.85, >=3 matches = 1.0)
            if matches == 0:
                score = 0.0
            elif matches == 1:
                score = 0.6
            elif matches == 2:
                score = 0.85
            else:
                score = 1.0
            keyword_scores[topic] = score

        return keyword_scores

    def _embedding_similarity_score(self, query: str) -> Dict[str, float]:
        """
        Compute embedding similarity score for each topic

        Args:
            query: User query

        Returns:
            Dictionary mapping topic to similarity score (0-1)
        """
        query_embedding = self.engine.encode(query)[0]

        similarity_scores = {}
        for topic, topic_emb in self.topic_embeddings.items():
            # Compute cosine similarity (both vectors are normalized)
            similarity = float(np.dot(query_embedding, topic_emb))
            similarity_scores[topic] = similarity

        return similarity_scores

    def classify(self, query: str, top_k: int = 1) -> Tuple[str, float, Dict]:
        """
        Classify query to legal topic using hybrid scoring

        Scoring: 0.6 * embedding_similarity + 0.4 * keyword_score
                 + keyword boost if matching keywords are found.

        Args:
            query: User query
            top_k: Return top-k topics

        Returns:
            Tuple of (top_topic, confidence, scores_dict)
        """
        # Get scores from both methods
        embedding_scores = self._embedding_similarity_score(query)
        keyword_scores = self._keyword_score(query)
        query_lower = query.lower()

        # Hybrid scoring: 60% embedding, 40% keyword + keyword boost
        hybrid_scores = {}
        for topic in self.topic_mapping.keys():
            hybrid_score = (
                0.6 * embedding_scores[topic] + 0.4 * keyword_scores[topic]
            )
            
            # Boost logic: if there is an exact keyword match in the query,
            # give a bonus score to that topic before sorting.
            matches = sum(1 for keyword in self.topic_keywords[topic] if keyword.lower() in query_lower)
            if matches > 0:
                boost = min(0.15 * matches, 0.3)
                hybrid_score += boost

            hybrid_scores[topic] = hybrid_score

        # Sort by score
        sorted_topics = sorted(
            hybrid_scores.items(), key=lambda x: x[1], reverse=True
        )

        top_topic, top_confidence = sorted_topics[0]

        # Ensure confidence is in valid range
        top_confidence = max(0.0, min(1.0, top_confidence))

        # Log classification
        LegalAdvisorLogger.log_topic_classification(query, top_topic, top_confidence)

        # Return detailed scores for debugging
        scores_detail = {
            "embedding_scores": embedding_scores,
            "keyword_scores": keyword_scores,
            "hybrid_scores": hybrid_scores,
            "top_k_results": [
                {"topic": t, "confidence": float(s)} for t, s in sorted_topics[:top_k]
            ],
        }

        return top_topic, top_confidence, scores_detail

    def is_legal_query(self, query: str, threshold: float = 0.35) -> bool:
        """
        Determine if query is legal-related based on hybrid score

        Args:
            query: User query
            threshold: Minimum confidence threshold

        Returns:
            True if query is legal-related, False otherwise
        """
        _, confidence, _ = self.classify(query)
        return confidence >= threshold


if __name__ == "__main__":
    from src.ml.inlegalbert_engine import InLegalBERTEngine

    # Initialize
    engine = InLegalBERTEngine()
    classifier = LegalTopicClassifier(engine)

    # Test queries
    test_queries = [
        "False allegations damaged my reputation",
        "Forced overtime without compensation",
        "My property is being trespassed",
        "Hacking into bank accounts",
        "Divorce and custody",
        "How are computers made?",  # Non-legal
        "Dowry demands from family",
    ]

    for query in test_queries:
        topic, confidence, _ = classifier.classify(query)
        print(
            f"Query: {query[:40]}... | Topic: {topic} | Confidence: {confidence:.4f}"
        )
