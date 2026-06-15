import torch
import numpy as np
from transformers import AutoTokenizer, AutoModel
from typing import List, Union, Tuple
from src.ml.model_cache import get_inlegalbert_model


class InLegalBERTEngine:
    """
    InLegalBERT engine for legal text embeddings.
    Uses mean pooling with L2 normalization for cosine similarity.
    """

    def __init__(self, model_name: str = "law-ai/InLegalBERT"):
        """
        Initialize InLegalBERT model

        Args:
            model_name: HuggingFace model identifier
        """
        self.model_name = model_name
        self.model, self.tokenizer = get_inlegalbert_model()
        self.device = self.model.device
        print(f"InLegalBERTEngine initialized using cached model on {self.device}")

    def mean_pooling(self, model_output, attention_mask):
        """
        Mean Pooling - Take attention mask into account for proper averaging

        Args:
            model_output: Model output from forward pass
            attention_mask: Attention mask tensor

        Returns:
            Mean pooled embeddings
        """
        token_embeddings = model_output[0]  # First element of model output is token embeddings
        input_mask_expanded = (
            attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        )
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(
            input_mask_expanded.sum(1), min=1e-9
        )

    def normalize_embeddings(self, embeddings: torch.Tensor) -> np.ndarray:
        """
        L2 normalize embeddings for cosine similarity

        Args:
            embeddings: Unnormalized embeddings

        Returns:
            L2 normalized embeddings as numpy array
        """
        embeddings = embeddings.detach().cpu().numpy()
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized = embeddings / (norms + 1e-10)
        return normalized

    def encode(self, texts: Union[str, List[str]], batch_size: int = 32) -> np.ndarray:
        """
        Encode text(s) to embeddings

        Args:
            texts: Single text or list of texts
            batch_size: Batch size for processing

        Returns:
            Normalized embeddings as numpy array
        """
        if isinstance(texts, str):
            texts = [texts]

        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            encoded_input = self.tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            ).to(self.device)

            with torch.no_grad():
                model_output = self.model(**encoded_input)

            sentence_embeddings = self.mean_pooling(
                model_output, encoded_input["attention_mask"]
            )
            sentence_embeddings = self.normalize_embeddings(sentence_embeddings)
            all_embeddings.extend(sentence_embeddings)

        return np.array(all_embeddings)

    def cosine_similarity(
        self, embeddings1: np.ndarray, embeddings2: np.ndarray
    ) -> np.ndarray:
        """
        Compute cosine similarity between embeddings (already normalized)

        Args:
            embeddings1: First set of embeddings
            embeddings2: Second set of embeddings

        Returns:
            Cosine similarity scores
        """
        # Since embeddings are already L2 normalized, cosine similarity = dot product
        return np.dot(embeddings1, embeddings2.T)

    def semantic_similarity_score(self, text1: str, text2: str) -> float:
        """
        Compute semantic similarity between two texts

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0-1)
        """
        emb1 = self.encode(text1)
        emb2 = self.encode(text2)
        similarity = self.cosine_similarity(emb1, emb2)[0][0]
        return float(similarity)

    def batch_semantic_similarity(
        self, query: str, documents: List[str]
    ) -> Tuple[np.ndarray, List[float]]:
        """
        Compute similarity between query and multiple documents

        Args:
            query: Query text
            documents: List of document texts

        Returns:
            Tuple of (normalized document embeddings, similarity scores)
        """
        query_emb = self.encode(query)
        doc_embs = self.encode(documents)

        similarities = self.cosine_similarity(query_emb, doc_embs)[0]
        return doc_embs, similarities.tolist()


if __name__ == "__main__":
    # Test the engine
    engine = InLegalBERTEngine()

    # Test single text encoding
    text = "This is a case about defamation and false allegations"
    embedding = engine.encode(text)
    print(f"Embedding shape: {embedding.shape}")
    print(f"Embedding sample: {embedding[0][:10]}")

    # Test similarity
    text1 = "False allegations damage reputation"
    text2 = "Defamation is a serious offense under IPC 499"
    similarity = engine.semantic_similarity_score(text1, text2)
    print(f"Similarity between texts: {similarity:.4f}")

    # Test batch similarity
    query = "What is defamation?"
    docs = [
        "Defamation is making false statements",
        "Contract law deals with agreements",
        "Slander damages reputation",
    ]
    doc_embs, sims = engine.batch_semantic_similarity(query, docs)
    for doc, sim in zip(docs, sims):
        print(f"'{doc}' -> Similarity: {sim:.4f}")
