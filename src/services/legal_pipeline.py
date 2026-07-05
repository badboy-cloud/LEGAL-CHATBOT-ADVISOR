import time
import logging
from typing import Dict
from src.ml.inlegalbert_engine import InLegalBERTEngine
from src.ml.legal_topic_classifier import LegalTopicClassifier
from src.ml.statute_predictor import StatutePredictor
from src.ml.faiss_retriever import FAISSRetriever
from src.ml.llm_engine import LLMEngine
from src.utils.logger import LegalAdvisorLogger
try:
    from src.utils.statute_explainer import get_explainer_details
except ImportError:
    try:
        from utils.statute_explainer import get_explainer_details
    except ImportError:
        get_explainer_details = None

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

        # Caching check (Priority 8)
        from src.utils.cache_manager import LegalAdvisorCache
        cached_res = LegalAdvisorCache.get("analyze", query)
        if cached_res:
            total_time = time.time() - pipeline_start
            cached_res["performance"]["total_time_seconds"] = round(total_time, 3)
            # Print timings (Priority 9)
            print("\n=== PERFORMANCE TIMINGS ===")
            print("Classification: 0.0 sec")
            print("FAISS Retrieval: 0.0 sec")
            print("LLM Generation: 0.0 sec")
            print(f"Total Pipeline Time: {total_time:.3f} sec\n")
            return cached_res

        t_classify_start = time.time()
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
        t_classify = time.time() - t_classify_start

        # Statute prediction
        t_statutes_start = time.time()
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
        t_statutes = time.time() - t_statutes_start

        # FAISS retrieval (topic-aware)
        t_retrieval_start = time.time()
        retrieval_result = self.retriever.retrieve(
            query, topic, top_k=3, threshold=0.65
        )
        precedents = retrieval_result.get("precedents", [])
        t_retrieval = time.time() - t_retrieval_start

        # LLM legal reasoning
        t_gen_start = time.time()
        llm_result = self.llm.generate_legal_advice(
            query, topic, formatted_statutes, precedents, temperature=0.3
        )
        t_gen = time.time() - t_gen_start

        total_time = time.time() - pipeline_start
        LegalAdvisorLogger.log_pipeline_complete(total_time, query)

        # Print performance timings (Priority 9)
        print("\n=== PERFORMANCE TIMINGS ===")
        print(f"Classification: {t_classify:.3f} sec")
        print(f"FAISS Retrieval: {t_retrieval:.3f} sec")
        print(f"LLM Generation: {t_gen:.3f} sec")
        print(f"Total Pipeline Time: {total_time:.3f} sec\n")

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
                "classification_time_seconds": round(t_classify, 3),
                "retrieval_time_seconds": round(t_retrieval, 3),
                "generation_time_seconds": round(t_gen, 3),
            },
        }

        # Cache response (Priority 8)
        LegalAdvisorCache.set("analyze", query, result)

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
            query = f"Incident of crime at police station {fir_details.get('police_station', '')}"

        # Cache check
        raw_fir_text = fir_details.get("raw_text") or query
        from src.utils.cache_manager import LegalAdvisorCache
        cached_res = LegalAdvisorCache.get("analyze-fir", raw_fir_text)
        if cached_res:
            total_time = time.time() - pipeline_start
            cached_res["performance"]["total_time_seconds"] = round(total_time, 3)
            # Print timings (Priority 9)
            print("\n=== PERFORMANCE TIMINGS ===")
            print("Classification: 0.0 sec")
            print("FAISS Retrieval: 0.0 sec")
            print("LLM Generation: 0.0 sec")
            print(f"Total Pipeline Time: {total_time:.3f} sec\n")
            return cached_res

        # Topic classification
        t_classify_start = time.time()
        topic, confidence, topic_scores = self.classifier.classify(query)
        t_classify = time.time() - t_classify_start

        # Extract legal sections from fir_details
        extracted_sections = fir_details.get("legal_sections", [])

        # Format statutes
        t_statutes_start = time.time()
        formatted_statutes = []
        for statute_code in extracted_sections:
            details = self.statute_predictor.get_statute_details(statute_code)
            if not details:
                clean_code = statute_code
                if "IPC " in statute_code:
                    clean_code = statute_code.replace("IPC ", "")
                elif "BNS " in statute_code:
                    clean_code = statute_code.replace("BNS ", "")
                details = self.statute_predictor.get_statute_details(clean_code)

            formatted_statutes.append(
                {
                    "code": statute_code,
                    "title": details.get("title", "Statutory Provision"),
                    "description": details.get("section", f"Section of {statute_code}"),
                    "penalties": details.get("penalties", "Penalties as prescribed by law"),
                }
            )
        statutes = extracted_sections
        t_statutes = time.time() - t_statutes_start

        # FAISS retrieval (topic-aware)
        t_retrieval_start = time.time()
        retrieval_result = self.retriever.retrieve(
            query, topic, top_k=3, threshold=0.60
        )
        precedents = retrieval_result.get("precedents", [])
        t_retrieval = time.time() - t_retrieval_start

        # Qwen3 Legal Analysis (exactly ONE LLM call)
        t_gen_start = time.time()
        try:
            analysis_result = self.llm.analyze_fir_legal_issues(
                fir_details=fir_details,
                topic=topic,
                statutes=formatted_statutes,
                precedents=precedents
            )
        except Exception as e:
            logger.error(f"Error during Qwen Legal Analysis: {e}")
            analysis_result = {
                "legal_advice": "Legal analysis could not be generated. Please review FIR details manually.",
                "risk_level": "Medium",
                "status": "partial_success"
            }
        t_gen = time.time() - t_gen_start

        # Programmatic Timeline and Risk Analysis (Guarantees 1 LLM call per request)
        timeline_events = []
        incident_date = fir_details.get("date_of_incident") or "Incident Date"
        reg_date = fir_details.get("date_of_registration") or "Registration Date"
        
        timeline_events.append({"date": incident_date, "event": "Occurrence of incident / offence"})
        
        # Add intermediate dates if any exist in fir_details.get("dates")
        other_dates = fir_details.get("dates", [])
        if isinstance(other_dates, list):
            for d in other_dates:
                if d and d != incident_date and d != reg_date and d not in [e["date"] for e in timeline_events]:
                    timeline_events.append({"date": d, "event": "Relevant date mentioned in FIR"})
                    
        timeline_events.append({"date": reg_date, "event": "FIR registered with police station"})
        
        # Determine risk assessment
        severity = analysis_result.get("risk_level", "Medium")
        critical_sections = ["302", "307", "376", "395", "420"]
        for sec in extracted_sections:
            if any(crit in sec for crit in critical_sections):
                severity = "High"
                break
                
        timeline_data = {
            "timeline": timeline_events,
            "risk": {
                "severity": severity,
                "financial_risk": "High" if "420" in "".join(extracted_sections) else "Medium",
                "criminal_exposure": "High" if severity == "High" else "Medium",
                "complexity": "Medium",
                "evidence_strength": "Medium"
            }
        }

        total_time = time.time() - pipeline_start

        # Print performance timings (Priority 9)
        ocr_time = fir_details.get("ocr_time", 0.0)
        print("\n=== PERFORMANCE TIMINGS ===")
        if ocr_time > 0:
            print(f"OCR: {ocr_time:.3f} sec")
        print(f"Classification: {t_classify:.3f} sec")
        print(f"FAISS Retrieval: {t_retrieval:.3f} sec")
        print(f"LLM Generation: {t_gen:.3f} sec")
        print(f"Total Pipeline Time: {total_time + ocr_time:.3f} sec\n")

        # Build statute explainer mappings
        statutes_explainers = {}
        for s in statutes:
            if get_explainer_details:
                statutes_explainers[s] = get_explainer_details(s)
            else:
                statutes_explainers[s] = {
                    "name": f"Section {s}",
                    "description": "Specific statutory provision under Indian penal code or relevant cyber acts.",
                    "punishment": "As prescribed by the magistrate court under applicable schedules.",
                    "cognizability": "Generally Cognizable",
                    "bailability": "Subject to judicial discretion (Check Code of Criminal Procedure schedule)"
                }

        # Merge risk levels to determine overall risk level
        risk_lvl = timeline_data.get("risk", {}).get("severity", analysis_result.get("risk_level", "Medium"))

        result = {
            "status": analysis_result.get("status", "success"),
            "fir_summary": fir_details.get("incident_summary") or fir_details.get("incident_description", "No incident description"),
            "fir_number": fir_details.get("fir_number", "Unknown"),
            "police_station": fir_details.get("police_station", "Unknown"),
            "complainant": fir_details.get("complainant", "Unknown"),
            "accused": fir_details.get("accused", "Unknown"),
            "witnesses": fir_details.get("witnesses_list", []),
            "witnesses_str": fir_details.get("witnesses", "None listed in FIR"),
            "sections": statutes,
            "legal_sections": statutes,
            "statutes_explainers": statutes_explainers,
            "crpc_sections": fir_details.get("crpc_sections", []),
            "officer_details": fir_details.get("officer_details", "Review Required"),
            "evidence_submitted": fir_details.get("evidence_submitted", "None explicitly listed"),
            "confidence_scores": fir_details.get("confidence_scores", {}),
            "review_required_fields": fir_details.get("review_required_fields", []),
            "timeline": timeline_data.get("timeline", []),
            "risk_assessment": timeline_data.get("risk", {}),
            "dates": fir_details.get("dates", []),
            "date_of_registration": fir_details.get("date_of_registration", "Review Required"),
            "date_of_incident": fir_details.get("date_of_incident", "Review Required"),
            "location": fir_details.get("location", "Not found"),
            "topic": topic,
            "precedents": precedents,
            "legal_advice": analysis_result.get("legal_advice", ""),
            "risk_level": risk_lvl,
            "performance": {
                "total_time_seconds": round(total_time, 3),
                "classification_time_seconds": round(t_classify, 3),
                "statute_prediction_time_seconds": round(t_statutes, 3),
                "retrieval_time_seconds": round(t_retrieval, 3),
                "generation_time_seconds": round(t_gen, 3),
                "timeline_time_seconds": 0.0,
                "retrieved_precedents": len(precedents)
            }
        }

        # Cache response
        LegalAdvisorCache.set("analyze-fir", raw_fir_text, result)

        return result

    def analyze_notice_text(self, extracted_text: str, ocr_time: float) -> dict:
        """
        Complete legal analysis pipeline for Legal Notice details (Priority 1 flow):
        Upload PDF/Image
        → OCR/Text Extraction (done, passed via ocr_time)
        → Notice Information Extraction (Regex, no LLM)
        → InLegalBERT Classification
        → FAISS Retrieval
        → Single Qwen Generation
        → Parse Output
        """
        pipeline_start = time.time()
        
        # 1. Notice Information Extraction (Regex)
        t_extract_start = time.time()
        import re
        notice_info = {
            "sender": "Not identified",
            "recipient": "Not identified",
            "advocate": "None",
            "notice_date": "Not specified",
            "response_deadline": "Not specified"
        }
        
        # Date regex
        date_patterns = [
            r"(?:date|dated|dt\.?)\s*[:\-]?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
            r"(?:date|dated|dt\.?)\s*[:\-]?\s*(\d{1,2}\s+[a-zA-Z]{3,10}\s+\d{4})",
            r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
            r"(\d{1,2}\s+[a-zA-Z]{3,10}\s+\d{4})"
        ]
        for pattern in date_patterns:
            match = re.search(pattern, extracted_text, re.IGNORECASE)
            if match:
                notice_info["notice_date"] = match.group(1).strip()
                break
                
        # Deadline regex
        deadline_patterns = [
            r"(\d+\s*days?)\s+(?:to\s+reply|for\s+reply|within\s+which)",
            r"(?:reply|respond|pay)\s+(?:within|in)\s+(\d+\s*days?)",
            r"within\s+(?:a\s+period\s+of\s+)?(\d+\s*days?)",
            r"limit\s+of\s+(\d+\s*days?)"
        ]
        for pattern in deadline_patterns:
            match = re.search(pattern, extracted_text, re.IGNORECASE)
            if match:
                notice_info["response_deadline"] = match.group(1).strip()
                break
                
        # Advocate regex
        advocate_patterns = [
            r"(?:advocate|counsel|pleader|solicitor|chamber of|law chambers)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})",
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s*,\s*(?:advocate|counsel|pleader|solicitor|co\.)",
        ]
        for pattern in advocate_patterns:
            match = re.search(pattern, extracted_text)
            if match:
                name = match.group(1).strip()
                if not any(w in name.lower() for w in ["court", "district", "supreme", "high", "notice", "legal", "plaintiff", "defendant", "respondent"]):
                    notice_info["advocate"] = name
                    break
                    
        # Sender/Recipient regex
        sender_match = re.search(r"(?:my client|instruction from|behalf of)\s+(?:mr\.?|m/s\.?|mrs\.?|ms\.?)?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})", extracted_text, re.IGNORECASE)
        if sender_match:
            notice_info["sender"] = sender_match.group(1).strip()
            
        recipient_match = re.search(r"(?:to|against|served upon)\s+(?:mr\.?|m/s\.?|mrs\.?|ms\.?)?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})", extracted_text, re.IGNORECASE)
        if recipient_match:
            notice_info["recipient"] = recipient_match.group(1).strip()
            
        notice_extract_time = time.time() - t_extract_start

        # 2. InLegalBERT Classification
        t_classify_start = time.time()
        topic, confidence, _ = self.classifier.classify(extracted_text[:3000])
        inlegalbert_time = time.time() - t_classify_start

        # Statutes prediction based on topic
        statute_result = self.statute_predictor.predict(topic)
        statutes = statute_result.get("statutes", [])

        # 3. FAISS Retrieval
        t_retrieval_start = time.time()
        retrieval_result = self.retriever.retrieve(
            extracted_text[:2000], topic, top_k=2, threshold=0.60
        )
        precedents = retrieval_result.get("precedents", [])
        faiss_time = time.time() - t_retrieval_start

        # 4. Single Qwen Generation
        t_gen_start = time.time()
        statutes_str = ", ".join(statutes[:3])
        precedents_str = ", ".join([p.get('case_name', '') for p in precedents[:2]])

        prompt = f"""You are a professional legal notice interpreter. Analyze this notice:
Notice Text: {extracted_text[:2000]}
Topic: {topic}
Statutes: {statutes_str}
Precedents: {precedents_str}

Return ONLY a valid JSON object matching this schema (no extra text or markdown wrapping):
{{
  "sender": "{notice_info['sender']}",
  "recipient": "{notice_info['recipient']}",
  "advocate": "{notice_info['advocate']}",
  "notice_date": "{notice_info['notice_date']}",
  "response_deadline": "{notice_info['response_deadline']}",
  "notice_summary": "Summary of notice claims/allegations",
  "key_allegations": ["allegation 1", "allegation 2"],
  "legal_provisions": [{{"section": "IPC Section X", "explanation": "Layman explanation"}}],
  "required_actions": ["demanded action 1"],
  "possible_consequences": "consequences if ignored",
  "ai_explanation": "concise plain-English overview of the notice",
  "recommendations": ["recommended action 1", "recommended action 2"]
}}
=== GENERATE RESPONSE ===
"""
        # Call Qwen exactly ONCE
        response_text = self.llm._attempt_with_retries(
            prompt=prompt,
            temperature=0.2,
            timeout=600,
            check_json=True
        )
        t_gen = time.time() - t_gen_start
        total_time = time.time() - pipeline_start

        # 5. Parse Output
        analysis = None
        if response_text:
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                if lines[0].startswith("```json") or lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                cleaned = "\n".join(lines).strip()
            
            # Find the JSON braces
            import json
            start_idx = cleaned.find("{")
            end_idx = cleaned.rfind("}")
            if start_idx != -1 and end_idx != -1:
                cleaned = cleaned[start_idx:end_idx+1]
                
            try:
                analysis = json.loads(cleaned)
            except Exception as e:
                logger.warning(f"JSON parsing failed: {e}. Trying to fix trailing commas.")
                try:
                    cleaned_relaxed = re.sub(r',\s*([\]}])', r'\1', cleaned)
                    analysis = json.loads(cleaned_relaxed)
                except Exception:
                    logger.error("Relaxed JSON parsing failed.")
                    analysis = None

        # Build fallback values for robustness (Priority 4 and 7)
        fallback_desc = f"An encroachment or dispute relating to {topic.replace('_', ' ').title()} has occurred."
        default_res = {
            "sender": notice_info["sender"],
            "recipient": notice_info["recipient"],
            "advocate": notice_info["advocate"],
            "notice_date": notice_info["notice_date"],
            "response_deadline": notice_info["response_deadline"],
            "notice_summary": fallback_desc,
            "key_allegations": ["Encroachment or illegal action without consent/permission"],
            "legal_provisions": [{"section": statutes[0] if statutes else "Relevant Statute", "explanation": "Statutory provisions protecting property or civil rights from illegal acts."}],
            "required_actions": ["Cease illegal activities or construction immediately", "Provide written response to notice sender"],
            "possible_consequences": "Failing to respond may result in legal actions (civil suit or police complaints).",
            "ai_explanation": response_text or fallback_desc,
            "recommendations": [
                "Read the notice carefully.",
                "Preserve all relevant documents.",
                "Consult a qualified advocate before responding."
            ]
        }

        if analysis and isinstance(analysis, dict):
            # Ensure all required keys exist and are populated
            for k, val in default_res.items():
                if k not in analysis or not analysis[k]:
                    analysis[k] = val
        else:
            # Fallback to the raw response
            analysis = default_res

        # Print detailed timings (Priority 6)
        print("\n=== PERFORMANCE TIMINGS ===")
        print(f"OCR: {ocr_time:.3f} sec")
        print(f"Notice Extraction: {notice_extract_time:.3f} sec")
        print(f"InLegalBERT: {inlegalbert_time:.3f} sec")
        print(f"FAISS: {faiss_time:.3f} sec")
        print(f"Qwen: {t_gen:.3f} sec")
        print(f"Total Pipeline Time: {total_time + ocr_time:.3f} sec\n")

        analysis["performance"] = {
            "ocr_time_seconds": round(ocr_time, 3),
            "notice_extraction_time_seconds": round(notice_extract_time, 3),
            "inlegalbert_time_seconds": round(inlegalbert_time, 3),
            "faiss_retrieval_time_seconds": round(faiss_time, 3),
            "qwen_generation_time_seconds": round(t_gen, 3),
            "total_pipeline_time_seconds": round(total_time + ocr_time, 3)
        }

        return analysis

    def get_available_topics(self) -> list:
        """Get list of available legal topics"""
        return self.statute_predictor.get_topics()
