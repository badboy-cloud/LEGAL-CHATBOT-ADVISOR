import logging
import json
from datetime import datetime
from pathlib import Path

# Create logs directory
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Configure logging
log_file = logs_dir / f"legal_advisor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class LegalAdvisorLogger:
    """Centralized logging for legal advisor pipeline"""

    @staticmethod
    def log_query(query: str):
        """Log user query"""
        logger.info(f"[QUERY] {query}")

    @staticmethod
    def log_topic_classification(query: str, topic: str, confidence: float):
        """Log topic classification results"""
        logger.info(f"[TOPIC_CLASSIFICATION] Query: {query[:50]}... | Topic: {topic} | Confidence: {confidence:.4f}")

    @staticmethod
    def log_statute_prediction(topic: str, statutes: list):
        """Log predicted statutes"""
        logger.info(f"[STATUTE_PREDICTION] Topic: {topic} | Statutes: {', '.join(statutes)}")

    @staticmethod
    def log_retrieval(topic: str, retrieved_count: int, avg_similarity: float, retrieval_time: float):
        """Log FAISS retrieval results"""
        logger.info(
            f"[RETRIEVAL] Topic: {topic} | Retrieved: {retrieved_count} | "
            f"Avg Similarity: {avg_similarity:.4f} | Time: {retrieval_time:.3f}s"
        )

    @staticmethod
    def log_llm_call(topic: str, llm_time: float, response_length: int):
        """Log LLM (Qwen3) call results"""
        logger.info(f"[LLM_CALL] Topic: {topic} | Time: {llm_time:.3f}s | Response Length: {response_length}")

    @staticmethod
    def log_error(component: str, error: str):
        """Log error with component info"""
        logger.error(f"[ERROR_{component}] {error}")

    @staticmethod
    def log_pipeline_complete(total_time: float, query: str):
        """Log successful pipeline completion"""
        logger.info(f"[PIPELINE_COMPLETE] Query: {query[:50]}... | Total Time: {total_time:.3f}s")

    @staticmethod
    def log_domain_rejection(query: str):
        """Log domain restriction rejection"""
        logger.warning(f"[DOMAIN_REJECTION] Non-legal query: {query[:50]}...")

    @staticmethod
    def log_detailed_result(result_data: dict):
        """Log detailed result as JSON"""
        logger.info(f"[DETAILED_RESULT] {json.dumps(result_data, indent=2)}")


if __name__ == "__main__":
    logger.info("Logger initialized successfully")
