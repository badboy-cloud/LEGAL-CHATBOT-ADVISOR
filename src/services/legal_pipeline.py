import time
import logging
from typing import Dict
from src.ml.inlegalbert_engine import InLegalBERTEngine
from src.ml.legal_topic_classifier import LegalTopicClassifier
from src.ml.statute_predictor import StatutePredictor
from src.ml.faiss_retriever import FAISSRetriever
from src.ml.llm_engine import LLMEngine
from src.utils.logger import LegalAdvisorLogger

logger = logging.getLogger(__name__)


class LegalPipeline:
    """
    Complete legal advisory pipeline orchestrating all components:
    1. Topic Classification
    2. Statute Prediction
    3. FAISS Precedent Retrieval
    4. Qwen3 Reasoning
    """

    def __init__(self):
        """Initialize all pipeline components"""
        print("[PIPELINE] Initializing Legal Advisory Pipeline...")

        self.inlegalbert = InLegalBERTEngine()
        self.classifier = LegalTopicClassifier(self.inlegalbert)
        self.statute_predictor = StatutePredictor()
        self.retriever = FAISSRetriever(self.inlegalbert)
        self.llm = LLMEngine(timeout=600)

        print("[PIPELINE] [OK] All components initialized")

    def analyze(self, query: str, domain_threshold: float = 0.3) -> Dict:
        """
        Complete legal analysis pipeline for text queries.
        """
        pipeline_start = time.time()

        # Log query
        LegalAdvisorLogger.log_query(query)

        # Domain validation
        if not self.classifier.is_legal_query(query, threshold=domain_threshold):
            LegalAdvisorLogger.log_domain_rejection(query)
            return {
                "status": "error",
                "message": "Please ask questions related to Indian legal matters only.",
                "query": query,
            }

        # Topic classification
        topic, confidence, topic_scores = self.classifier.classify(query)

        # Statute prediction
        statute_result = self.statute_predictor.predict(topic)
        statutes = statute_result.get("statutes", [])

        # Format statutes for LLM
        formatted_statutes = []
        for statute_code in statutes:
            statute_details = statute_result["details"].get(statute_code, {})
            formatted_statutes.append(
                {
                    "code": statute_code,
                    "title": statute_details.get("title", ""),
                    "description": statute_details.get("section", ""),
                    "penalties": statute_details.get("penalties", ""),
                }
            )

        # FAISS retrieval (topic-aware)
        retrieval_result = self.retriever.retrieve(
            query, topic, top_k=3, threshold=0.65
        )
        precedents = retrieval_result.get("precedents", [])

        # LLM legal reasoning
        llm_result = self.llm.generate_legal_advice(
            query, topic, formatted_statutes, precedents, temperature=0.3
        )

        total_time = time.time() - pipeline_start
        LegalAdvisorLogger.log_pipeline_complete(total_time, query)

        result = {
            "status": llm_result.get("status", "success"),
            "query": query,
            "topic": {
                "name": topic,
                "confidence": float(confidence),
            },
            "statutes": {
                "list": statutes,
                "details": formatted_statutes,
            },
            "precedents": precedents,
            "legal_advice": llm_result.get("advice", ""),
            "llm_metadata": {
                "source": llm_result.get("source", "unknown"),
                "success": llm_result.get("success", False),
                "llm_time_seconds": llm_result.get("llm_time", 0.0),
            },
            "performance": {
                "total_time_seconds": round(total_time, 3),
                "retrieved_precedents": len(precedents),
            },
        }

        return result

    def analyze_fir_text(self, fir_details: dict, domain_threshold: float = 0.3) -> dict:
        """
        Complete legal analysis pipeline for FIR document details.
        """
        pipeline_start = time.time()

        # Use the incident summary, description, or nature of offence to classify topic
        query = fir_details.get("incident_summary", "")
        if not query or len(query.strip()) < 10:
            query = fir_details.get("incident_description", "")
        if not query or len(query.strip()) < 10:
            query = fir_details.get("nature_of_offence", "")
        if not query or len(query.strip()) < 10:
            # Fallback if both are empty/too short
            query = f"Incident of crime at police station {fir_details.get('police_station', '')}"

        # Topic classification
        t_classify_start = time.time()
        topic, confidence, topic_scores = self.classifier.classify(query)
        t_classify = time.time() - t_classify_start
        logger.info(f"[TIMING] InLegalBERT Time: {t_classify:.3f} seconds")

        # Statute prediction
        t_statutes_start = time.time()
        statute_result = self.statute_predictor.predict(topic)
        statutes = statute_result.get("statutes", [])

        # Format statutes
        formatted_statutes = []
        for statute_code in statutes:
            statute_details = statute_result["details"].get(statute_code, {})
            formatted_statutes.append(
                {
                    "code": statute_code,
                    "title": statute_details.get("title", ""),
                    "description": statute_details.get("section", ""),
                    "penalties": statute_details.get("penalties", ""),
                }
            )
        t_statutes = time.time() - t_statutes_start
        logger.info(f"[TIMING] Statute prediction took {t_statutes:.3f} seconds")

        # FAISS retrieval (topic-aware)
        t_retrieval_start = time.time()
        retrieval_result = self.retriever.retrieve(
            query, topic, top_k=3, threshold=0.60
        )
        precedents = retrieval_result.get("precedents", [])
        t_retrieval = time.time() - t_retrieval_start
        logger.info(f"[TIMING] FAISS Retrieval Time: {t_retrieval:.3f} seconds")

        # Qwen3 Legal Analysis
        t_gen_start = time.time()
        try:
            analysis_result = self.llm.analyze_fir_legal_issues(
                fir_details=fir_details,
                topic=topic,
                statutes=formatted_statutes,
                precedents=precedents
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error during Qwen Legal Analysis: {e}")
            analysis_result = {
                "legal_advice": "Legal analysis could not be generated. Please review FIR details manually.",
                "risk_level": "Medium",
                "success": True,
                "llm_time": time.time() - t_gen_start
            }
        t_gen = time.time() - t_gen_start
        logger.info(f"[TIMING] Qwen Generation Time: {t_gen:.3f} seconds")

        total_time = time.time() - pipeline_start
        logger.info(f"[TIMING] Total Pipeline Time: {total_time:.3f} seconds")

        return {
            "status": analysis_result.get("status", "success"),
            "fir_summary": fir_details.get("incident_summary") or fir_details.get("incident_description", "No incident description"),
            "fir_number": fir_details.get("fir_number", "Unknown"),
            "police_station": fir_details.get("police_station", "Unknown"),
            "complainant": fir_details.get("complainant", "Unknown"),
            "accused": fir_details.get("accused", "Unknown"),
            "sections": statutes,
            "topic": topic,
            "precedents": precedents,
            "legal_advice": analysis_result.get("legal_advice", ""),
            "risk_level": analysis_result.get("risk_level", "Medium"),
            "performance": {
                "total_time_seconds": round(total_time, 3),
                "classification_time_seconds": round(t_classify, 3),
                "statute_prediction_time_seconds": round(t_statutes, 3),
                "retrieval_time_seconds": round(t_retrieval, 3),
                "generation_time_seconds": round(t_gen, 3),
                "retrieved_precedents": len(precedents)
            }
        }

    def get_available_topics(self) -> list:
        """Get list of available legal topics"""
        return self.statute_predictor.get_topics()
