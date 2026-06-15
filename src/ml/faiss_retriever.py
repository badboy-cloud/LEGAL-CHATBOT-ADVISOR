import json
import numpy as np
import faiss
from pathlib import Path
from typing import List, Dict, Tuple
from src.ml.inlegalbert_engine import InLegalBERTEngine
from src.utils.logger import LegalAdvisorLogger


class FAISSRetriever:
    """
    Topic-aware FAISS retrieval for legal precedents.
    Ensures retrieved cases match the identified legal topic.
    """

    def __init__(self, inlegalbert_engine: InLegalBERTEngine, data_dir: str = "data"):
        """
        Initialize FAISS retriever

        Args:
            inlegalbert_engine: InLegalBERT engine for embeddings
            data_dir: Directory containing precedents.json and vector index
        """
        self.engine = inlegalbert_engine
        self.data_dir = Path(data_dir)

        # Load precedents database
        precedents_file = self.data_dir / "precedents.json"
        with open(precedents_file, "r") as f:
            self.precedents_db = json.load(f)

        # Build FAISS index
        self.index, self.case_map = self._build_faiss_index()
        print(f"FAISS retriever initialized with {len(self.case_map)} precedents")

    def _build_faiss_index(self) -> Tuple[faiss.IndexFlatL2, Dict]:
        """
        Build FAISS index from precedent texts.
        Stores embeddings and maintains mapping between index and cases.
        """
        embeddings_list = []
        case_map = {}
        idx = 0

        for topic, cases in self.precedents_db.items():
            for case in cases:
                # Use case facts and holding for embedding
                case_text = f"{case.get('case_name', '')}. {case.get('facts', '')}. {case.get('holding', '')}"

                embedding = self.engine.encode(case_text)[0]
                embeddings_list.append(embedding.astype(np.float32))

                case_map[idx] = {
                    "case_id": case.get("case_id", ""),
                    "case_name": case.get("case_name", ""),
                    "topic": topic,
                    "year": case.get("year", ""),
                    "court": case.get("court", ""),
                    "facts": case.get("facts", ""),
                    "holding": case.get("holding", ""),
                    "judgment": case.get("judgment", ""),
                    "principle": case.get("principle", ""),
                    "applicable_law": case.get("applicable_law", ""),
                }

                idx += 1

        # Create FAISS index
        embeddings_array = np.array(embeddings_list, dtype=np.float32)

        # L2 distance index
        index = faiss.IndexFlatL2(embeddings_array.shape[1])
        index.add(embeddings_array)

        return index, case_map

    def retrieve(
        self,
        query: str,
        topic: str,
        top_k: int = 3,
        threshold: float = 0.65,
    ) -> Dict:
        """
        Retrieve top-k precedents matching query and topic.

        Args:
            query: User query
            topic: Identified legal topic
            top_k: Number of top precedents to retrieve
            threshold: Minimum similarity threshold

        Returns:
            Dictionary with retrieved precedents and similarity scores
        """
        # Get query embedding
        query_embedding = self.engine.encode(query)[0].astype(np.float32)

        # Retrieve top-k*2 candidates (to account for topic filtering)
        distances, indices = self.index.search(
            np.array([query_embedding], dtype=np.float32), top_k * 3
        )

        # Map predicted topic to database topics in precedents.json
        topic_lower = topic.lower()
        topic_db_map = {
            "cyber_law": ["cyber_law", "cybercrime"],
            "criminal_law": ["criminal_law", "murder", "assault", "theft", "dowry", "harassment", "fraud"],
            "family_law": ["family_law", "dowry"],
            "labour_employment": ["labour_employment"],
            "property_law": ["property_law", "tenancy"],
            "contract_law": ["contract_law", "contract"],
            "civil_law": ["civil_law"],
            "consumer_law": ["consumer_law"],
            "constitutional_law": ["constitutional_law"],
            "defamation": ["defamation"]
        }
        allowed_db_topics = topic_db_map.get(topic_lower, [topic_lower])

        # Filter by topic and threshold
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            case_info = self.case_map[idx]

            # Convert L2 distance to similarity (0-1)
            # For L2: smaller is better, convert to similarity
            similarity = 1.0 / (1.0 + distance)

            # Topic filtering: only retrieve same-topic cases
            if case_info["topic"].lower() not in allowed_db_topics:
                continue

            if similarity < threshold:
                continue

            results.append(
                {
                    "case_id": case_info["case_id"],
                    "case_name": case_info["case_name"],
                    "topic": case_info["topic"],
                    "year": case_info["year"],
                    "court": case_info["court"],
                    "facts": case_info["facts"],
                    "holding": case_info["holding"],
                    "judgment": case_info["judgment"],
                    "principle": case_info["principle"],
                    "applicable_law": case_info["applicable_law"],
                    "similarity": float(similarity),
                }
            )

            if len(results) >= top_k:
                break

        # Log retrieval
        avg_similarity = (
            np.mean([r["similarity"] for r in results]) if results else 0.0
        )
        LegalAdvisorLogger.log_retrieval(topic, len(results), avg_similarity, 0.0)

        return {
            "topic": topic,
            "retrieved_count": len(results),
            "precedents": results,
        }

    def retrieve_all_topics(self, query: str, top_k: int = 3) -> Dict:
        """
        Retrieve precedents from all topics (fallback if no topic-specific matches).

        Args:
            query: User query
            top_k: Number of top precedents per topic

        Returns:
            Dictionary with precedents grouped by topic
        """
        query_embedding = self.engine.encode(query)[0].astype(np.float32)

        distances, indices = self.index.search(
            np.array([query_embedding], dtype=np.float32), len(self.case_map)
        )

        # Group by topic
        results_by_topic = {}
        for idx, distance in zip(indices[0], distances[0]):
            case_info = self.case_map[idx]
            topic = case_info["topic"]

            if topic not in results_by_topic:
                results_by_topic[topic] = []

            similarity = 1.0 / (1.0 + distance)
            results_by_topic[topic].append(
                {
                    "case_id": case_info["case_id"],
                    "case_name": case_info["case_name"],
                    "similarity": float(similarity),
                }
            )

        # Keep only top_k per topic
        for topic in results_by_topic:
            results_by_topic[topic] = results_by_topic[topic][:top_k]

        return results_by_topic


if __name__ == "__main__":
    from src.ml.inlegalbert_engine import InLegalBERTEngine

    engine = InLegalBERTEngine()
    retriever = FAISSRetriever(engine)

    # Test retrieval
    test_queries = [
        ("defamation", "False allegations damaged my reputation"),
        ("labour_employment", "I was forced to work overtime without pay"),
        ("property_law", "My neighbor is encroaching on my property"),
    ]

    for topic, query in test_queries:
        print(f"\nQuery: {query}")
        result = retriever.retrieve(query, topic, top_k=2)
        print(f"Retrieved {result['retrieved_count']} precedents:")
        for case in result["precedents"]:
            print(f"  - {case['case_name']} ({case['similarity']:.4f})")
