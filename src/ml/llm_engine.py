import requests
import json
import time
import logging
import sys
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from src.utils.logger import LegalAdvisorLogger

# Fix Windows console encoding: Qwen responses may contain unicode characters
# (e.g. ₹) that crash print() on Windows cp1252 codec.
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(errors='replace')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Module level cache for Ollama model verification
_OLLAMA_MODEL_VERIFIED = False


class LLMEngine:
    """
    Qwen3:8B via Ollama for legal reasoning and advice.
    """

    def __init__(
        self,
        model: str = "qwen3:8b",
        ollama_url: str = "http://localhost:11434",
        timeout: int = 300,
        max_retries: int = 2,
    ):
        """
        Initialize LLM engine.
        """
        self.model = model
        self.ollama_url = ollama_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.tags_endpoint = f"{ollama_url}/api/tags"
        self.generate_endpoint = f"{ollama_url}/api/generate"

        logger.info("[LLM_INIT] Engine initialized with model=%s, timeout=%d", model, timeout)
        self._verify_ollama_connection()

    def _check_model_in_ollama(self) -> bool:
        """
        Auto-check model availability via API and CLI.
        """
        global _OLLAMA_MODEL_VERIFIED
        if _OLLAMA_MODEL_VERIFIED:
            return True

        # Try HTTP tags API first
        try:
            logger.info("[LLM_REQUEST] Checking Ollama connection at %s", self.ollama_url)
            response = requests.get(self.tags_endpoint, timeout=5)
            if response.status_code == 200:
                tags_data = response.json()
                available_models = [m.get("name", "") for m in tags_data.get("models", [])]
                logger.info("[LLM_RESPONSE] Available models from API: %s", available_models)
                if any(self.model in name or name in self.model for name in available_models):
                    logger.info("[LLM_RESPONSE] Model %s verified via HTTP API", self.model)
                    _OLLAMA_MODEL_VERIFIED = True
                    return True
        except Exception as e:
            logger.warning("[LLM_ERROR] Ollama HTTP connection failed: %s", str(e))

        # Fallback to running "ollama list" command
        try:
            import subprocess
            logger.info("[LLM_REQUEST] Attempting fallback command: 'ollama list'")
            res = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                logger.info("[LLM_RESPONSE] 'ollama list' output: %s", res.stdout)
                if self.model in res.stdout:
                    logger.info("[LLM_RESPONSE] Model %s verified via CLI", self.model)
                    _OLLAMA_MODEL_VERIFIED = True
                    return True
        except Exception as e:
            logger.warning("[LLM_ERROR] 'ollama list' check failed: %s", str(e))

        return False

    def _verify_ollama_connection(self) -> bool:
        """
        Verify Ollama server is running and model exists.
        """
        global _OLLAMA_MODEL_VERIFIED
        if _OLLAMA_MODEL_VERIFIED:
            return True
        return self._check_model_in_ollama()

    def generate_legal_advice(
        self,
        query: str,
        topic: str,
        statutes: List[Dict],
        precedents: List[Dict],
        temperature: float = 0.3,
    ) -> Dict[str, any]:
        """
        Generate legal advice using Qwen3 with full context grounding.
        """
        logger.info("[LLM_REQUEST] New request: query_len=%d, topic=%s", len(query), topic)

        # Verify model before attempting generation
        if not self._verify_ollama_connection():
            logger.warning("[LLM_ERROR] Model validation failed, using fallback")
            fallback_advice = self._generate_fallback_advice(query, topic, statutes, precedents)
            status = "partial_success"
            print("FINAL_QWEN_ANSWER =", fallback_advice)
            print("FINAL_STATUS =", status)
            return {
                "status": status,
                "advice": fallback_advice,
                "source": "fallback",
                "llm_time": 0.0,
                "success": False,
            }

        prompt = self._build_prompt(query, topic, statutes, precedents)
        start_time = time.time()
        # Enforce options/limits: num_predict=384, top_p=0.9, temperature=0.2
        response_text = self._attempt_with_retries(
            prompt=prompt,
            temperature=0.2,
            min_words=None,
            check_completeness=False
        )
        llm_time = time.time() - start_time

        if response_text:
            logger.info("[LLM_RESPONSE] Success: response_len=%d, time=%.2f", len(response_text), llm_time)
            LegalAdvisorLogger.log_llm_call(topic, llm_time, len(response_text))
            status = "success"
            print("FINAL_QWEN_ANSWER =", response_text)
            print("FINAL_STATUS =", status)
            return {
                "status": status,
                "advice": response_text,
                "source": "qwen3",
                "llm_time": llm_time,
                "success": True,
            }
        else:
            logger.warning("[LLM_ERROR] All retries exhausted, using fallback")
            fallback_advice = self._generate_fallback_advice(query, topic, statutes, precedents)
            status = "partial_success"
            print("FINAL_QWEN_ANSWER =", fallback_advice)
            print("FINAL_STATUS =", status)
            return {
                "status": status,
                "advice": fallback_advice,
                "source": "fallback",
                "llm_time": llm_time,
                "success": False,
            }

    def extract_fir_details(self, text: str) -> Dict[str, any]:
        """
        Extract structured details from FIR text using Regex-based parser.
        No LLM is used in this stage.
        """
        start_time = time.time()
        from src.utils.fir_parser import RegexFIRParser
        parsed = RegexFIRParser.parse(text)
        elapsed = time.time() - start_time
        logger.info("[TIMING] Regex Extraction took %.3f seconds", elapsed)

        # Context Window Protection (Priority 4)
        MAX_FIR_CHARS = 12000
        if len(text) > MAX_FIR_CHARS:
            logger.info(f"[CONTEXT_PROTECTION] FIR text length ({len(text)} chars) exceeds {MAX_FIR_CHARS}. Generating summary first...")
            
            # Generate summary of the FIR using LLM
            summary_prompt = f"""You are a professional legal expert. Summarize the following long FIR text into a clear, detailed, and concise narrative. 
Focus on:
1. The chronological order of key events.
2. The specific criminal actions and allegations.
3. The names and roles of the accused and victims.
4. Any items, money, or digital assets stolen, seized, or defrauded.

FIR text (truncated for summary):
{text[:15000]}
"""
            # Use _attempt_with_retries to get the summary
            summary = self._attempt_with_retries(
                prompt=summary_prompt,
                temperature=0.2,
                system_prompt="You are a professional legal expert. Summarize the provided FIR text clearly and concisely. Do not explain your thinking."
            )
            
            if summary:
                logger.info(f"[CONTEXT_PROTECTION] Generated FIR Summary ({len(summary)} chars)")
                # Pass summary + extracted metadata to Qwen
                parsed["incident_summary"] = summary
                metadata_summary = f"""SUMMARY:
{summary}

EXTRACTED METADATA:
- FIR Number: {parsed.get('fir_number', 'N/A')}
- Police Station: {parsed.get('police_station', 'N/A')}
- Complainant: {parsed.get('complainant', 'N/A')}
- Accused: {parsed.get('accused', 'N/A')}
- Nature of Offence: {parsed.get('nature_of_offence', 'N/A')}
- Location: {parsed.get('location', 'N/A')}
- Sections Charged: {', '.join(parsed.get('legal_sections', []) + parsed.get('crpc_sections', []))}
"""
                parsed["raw_text"] = metadata_summary
            else:
                logger.warning("[CONTEXT_PROTECTION] Summary generation failed, falling back to truncated raw text")
                parsed["raw_text"] = text[:MAX_FIR_CHARS]
                
        return parsed

    def analyze_fir_legal_issues(
        self,
        fir_details: Dict[str, any],
        topic: str,
        statutes: List[Dict],
        precedents: List[Dict]
    ) -> Dict[str, any]:
        """
        Generate detailed FIR legal analysis using Qwen3.
        """
        logger.info("[LLM_REQUEST] Running FIR Legal Analysis, topic=%s", topic)
        
        # Budgeting to keep prompt size strictly under 1200 characters
        summary = fir_details.get('incident_summary') or fir_details.get('incident_description') or "No incident summary."
        if len(summary) > 200:
            summary = summary[:190] + "... [TRUNCATED]"

        ipc_sects = fir_details.get('ipc_sections') or []
        if isinstance(ipc_sects, str):
            ipc_sects = [ipc_sects]
        bns_sects = fir_details.get('bns_sections') or []
        if isinstance(bns_sects, str):
            bns_sects = [bns_sects]
            
        sections_str = ", ".join(ipc_sects + bns_sects)
        if len(sections_str) > 80:
            sections_str = sections_str[:75] + "... [TRUNCATED]"

        # Format statutes
        statutes_compact = ", ".join([s.get("code", "") for s in statutes[:3]])
            
        # Format precedents
        precedents_compact = ", ".join([p.get('case_name', 'Unknown') for p in precedents[:2]])

        prompt = f"""You are an Indian legal advisor. Analyze this FIR:
FIR: {fir_details.get('fir_number', 'N/A')} | PS: {fir_details.get('police_station', 'N/A')} | Complainant: {fir_details.get('complainant', 'N/A')} | Accused: {fir_details.get('accused', 'N/A')}
Sections: {sections_str}
Summary: {summary}
Topic: {topic}
Statutes: {statutes_compact}
Precedents: {precedents_compact}

Output EXACTLY this format (150-250 words total, max 300 words, no extra text):
### Case Summary
[Summary of the incident]

### Legal Issues
[Key legal questions]

### Applicable Laws
[Relevant statutes/precedents]

### Recommendations
[Next steps/remedies]

### Disclaimer
This is for informational purposes only. Consult a lawyer.
=== GENERATE RESPONSE ===
"""
        max_prompt_chars = 1200
        if len(prompt) > max_prompt_chars:
            prompt = prompt[:1150] + "\n=== GENERATE RESPONSE ==="
            
        start_time = time.time()
        # Enforce 0.2 temperature, no word checks, completeness validation disabled
        response_text = self._attempt_with_retries(
            prompt=prompt, 
            temperature=0.2, 
            timeout=self.timeout,
            min_words=None,
            check_completeness=False
        )
        elapsed = time.time() - start_time
        
        logger.info("[TIMING] Qwen generation took %.3f seconds", elapsed)
        
        # Validate Qwen output
        if response_text is None or not response_text.strip():
            logger.error("[LLM_ERROR] Qwen generation failed, timed out, or returned empty.")
            fallback_advice = self._generate_fallback_advice(
                query=summary,
                topic=topic,
                statutes=statutes,
                precedents=precedents
            )
            status = "partial_success"
            print("FINAL_QWEN_ANSWER =", fallback_advice)
            print("FINAL_STATUS =", status)
            return {
                "status": status,
                "legal_advice": fallback_advice,
                "risk_level": "Medium",
                "success": True,
                "llm_time": elapsed
            }
            
        # Determine Risk Level by looking for keywords in the output
        risk_level = "Medium"
        lower_text = response_text.lower()
        if "risk level: high" in lower_text or "high risk" in lower_text or "risk assessment: high" in lower_text:
            risk_level = "High"
        elif "risk level: low" in lower_text or "low risk" in lower_text or "risk assessment: low" in lower_text:
            risk_level = "Low"
            
        status = "success"
        print("FINAL_QWEN_ANSWER =", response_text)
        print("FINAL_STATUS =", status)
        return {
            "status": status,
            "legal_advice": response_text,
            "risk_level": risk_level,
            "success": True,
            "llm_time": elapsed
        }

    def _is_response_incomplete(self, text: str) -> bool:
        """
        Check if the generated response is incomplete or truncated.
        """
        if not text or not text.strip():
            return True
            
        text_stripped = text.strip()
        
        # Check if response ends with specific words/phrases (case-insensitive)
        incomplete_endings = [
            "case", "ipc", "legal", "recommendations:", "i need", 
            "first", "recommendation", "okay, let's", "let's"
        ]
        
        # Normalize text to lowercase and strip trailing non-alphanumeric/non-colon chars for suffix check
        import re
        normalized_end = re.sub(r'[^a-zA-Z0-9\s:]', '', text_stripped).lower().strip()
        
        for ending in incomplete_endings:
            clean_ending = re.sub(r'[^a-zA-Z0-9\s:]', '', ending).lower().strip()
            if normalized_end.endswith(clean_ending):
                logger.warning(f"[INCOMPLETE_CHECK] Response ends with incomplete word/phrase: '{ending}'")
                return True
                
        # Check if the response ends in a dangling sentence (missing terminal punctuation)
        if not re.search(r'[.!?`*_"\'\)\}\]]$', text_stripped):
            logger.warning("[INCOMPLETE_CHECK] Response does not end with sentence-terminating punctuation.")
            return True
            
        # Check if all required sections are present (case-insensitive)
        required_sections = [
            "case summary",
            "legal issues",
            "applicable laws",
            "potential consequences",
            "recommendations"
        ]
        
        lower_text = text_stripped.lower()
        section_matches = {
            "case summary": ["case summary"],
            "legal issues": ["legal issues", "key legal issues"],
            "applicable laws": ["applicable laws", "potential offences", "relevant legal principles", "applicable statutes"],
            "potential consequences": ["potential consequences", "possible legal consequences", "consequences"],
            "recommendations": ["recommendations", "recommended next steps", "recommendation"]
        }
        
        for section, patterns in section_matches.items():
            if not any(pat in lower_text for pat in patterns):
                logger.warning(f"[INCOMPLETE_CHECK] Missing required section: '{section}'")
                return True
                
        return False

    def _attempt_with_retries(
        self,
        prompt: str,
        temperature: float,
        timeout: Optional[int] = None,
        min_words: Optional[int] = None,
        check_completeness: bool = False,
        check_json: bool = False,
        system_prompt: Optional[str] = None,
        num_predict: Optional[int] = None
    ) -> Optional[str]:
        """
        Attempt generation with retry logic, exponential backoff, completeness checks, and minimum word count constraint.
        """
        if "qwen" in self.model.lower():
            if not prompt.startswith("/no_think"):
                prompt = "/no_think\n" + prompt

        req_timeout = timeout or self.timeout
        max_attempts = 4  # Initial attempt + 3 retries (total 4)
        
        if system_prompt is None:
            system_prompt = "You are a professional Indian legal advisor. Provide a comprehensive, detailed legal analysis and report. Answer all sections thoroughly. Do not explain your reasoning or internal thinking."

        # Default prediction tokens length
        pred_tokens = num_predict or (768 if check_json else 384)

        for attempt in range(max_attempts):
            try:
                # Check model availability first
                if not self._check_model_in_ollama():
                    raise ValueError(f"Ollama model '{self.model}' is missing or Ollama is offline.")

                req_start_time = time.time()
                start_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(req_start_time))
                
                logger.info(f"[QWEN_REQUEST] Start Time={start_time_str} | Attempt={attempt + 1}/{max_attempts} | Prompt Length={len(prompt)} chars")

                # We can also support streaming collection dynamically. If stream=True is requested:
                stream_enabled = False  # Set to True if we want streaming
                
                if stream_enabled:
                    http_response = requests.post(
                        self.generate_endpoint,
                        json={
                            "model": self.model,
                            "prompt": prompt,
                            "system": system_prompt,
                            "stream": True,
                            "think": False,
                            "options": {
                                "temperature": temperature,
                                "num_predict": pred_tokens,
                                "top_p": 0.9
                            }
                        },
                        timeout=req_timeout,
                        stream=True
                    )
                    
                    req_end_time = time.time()
                    actual_duration = req_end_time - req_start_time
                    logger.info(f"[QWEN_REQUEST] Attempt {attempt + 1} completed in {actual_duration:.3f} seconds")

                    if http_response.status_code == 200:
                        answer = ""
                        for line in http_response.iter_lines():
                            if line:
                                chunk = json.loads(line.decode('utf-8'))
                                if "message" in chunk and "content" in chunk["message"]:
                                    answer += chunk["message"]["content"]
                                elif "response" in chunk:
                                    answer += chunk["response"]
                                elif "generated_text" in chunk:
                                    answer += chunk["generated_text"]
                                elif "text" in chunk:
                                    answer += chunk["text"]
                    else:
                        raise ValueError(f"Ollama returned HTTP {http_response.status_code}: {http_response.text[:200]}")
                else:
                    # Non-streaming call (default)
                    http_response = requests.post(
                        self.generate_endpoint,
                        json={
                            "model": self.model,
                            "prompt": prompt,
                            "system": system_prompt,
                            "stream": False,
                            "think": False,
                            "options": {
                                "temperature": temperature,
                                "num_predict": pred_tokens,
                                "top_p": 0.9
                            }
                        },
                        timeout=req_timeout,
                    )
                    
                    req_end_time = time.time()
                    actual_duration = req_end_time - req_start_time
                    logger.info(f"[QWEN_REQUEST] Attempt {attempt + 1} completed in {actual_duration:.3f} seconds")

                    if http_response.status_code == 200:
                        response = http_response.json()
                        answer = ""
                        if isinstance(response, dict):
                            answer = (
                                response.get("message", {}).get("content")
                                or response.get("response")
                                or response.get("generated_text")
                                or response.get("text")
                                or ""
                            )
                        
                        if (not answer or not answer.strip()) and isinstance(response, dict):
                            thinking_content = response.get("thinking", "")
                            if thinking_content and thinking_content.strip():
                                answer = thinking_content
                    else:
                        raise ValueError(f"Ollama returned HTTP {http_response.status_code}: {http_response.text[:200]}")

                if answer is None or not isinstance(answer, str) or len(answer.strip()) == 0:
                    raise ValueError("Ollama returned an empty response.")
                
                # Priority 1: Debug raw model output
                print("=" * 100)
                print("RAW RESPONSE FROM OLLAMA")
                print(repr(answer))
                print("=" * 100)

                answer = answer.strip()
                
                # Clean up <think>...</think> tags if any remain (Priority 6)
                import re
                answer = re.sub(r'<think>[\s\S]*?</think>', '', answer).strip()
                answer = re.sub(r'<think>[\s\S]*?$', '', answer).strip()
                
                if "...done thinking." in answer:
                    answer = answer.split("...done thinking.")[-1].strip()
                    
                if len(answer.strip()) == 0:
                    raise ValueError("Parsed answer is empty after removing thinking block.")
                
                # Check for chain-of-thought phrases (Priority 6) - DO NOT retry
                lower_answer = answer.lower()
                cot_detected = False
                for phrase in ["okay, let's", "first,", "i need to", "need to determine", "the user asks"]:
                    if phrase in lower_answer[:150]:
                        cot_detected = True
                        logger.warning(f"[COT_CHECK] Chain of thought detected in first 150 chars: '{phrase}'")
                        break
                        
                # Check minimum word count constraint - DO NOT retry
                if min_words is not None:
                    word_count = len(answer.split())
                    if word_count < min_words:
                        logger.warning(f"[LENGTH_CHECK] Response length ({word_count} words) is below minimum of {min_words} words.")
                        
                # Check completeness (Priority 7) - DO NOT retry
                if check_completeness:
                    if self._is_response_incomplete(answer):
                        logger.warning("[INCOMPLETE_CHECK] Response appears to be incomplete or truncated.")
                        
                # Validate JSON (Priority 6 check_json) - DO NOT retry
                if check_json:
                    try:
                        cleaned_json = answer.strip()
                        if cleaned_json.startswith("```"):
                            lines = cleaned_json.split("\n")
                            if lines[0].startswith("```"):
                                lines = lines[1:]
                            if lines[-1].startswith("```"):
                                lines = lines[:-1]
                            cleaned_json = "\n".join(lines).strip()
                        json.loads(cleaned_json)
                    except Exception as json_err:
                        logger.warning(f"[JSON_CHECK] Response is not valid JSON: {str(json_err)}")

                # Log metrics (Priority 9)
                word_count = len(answer.split())
                response_len = len(answer)
                token_estimate = int(word_count * 1.3)
                logger.info(f"[QWEN_SUCCESS] Validation succeeded on Attempt {attempt + 1}!")
                logger.info(f"  - Generation Time: {actual_duration:.3f} seconds")
                logger.info(f"  - Word Count: {word_count}")
                logger.info(f"  - Token Estimate: {token_estimate}")
                logger.info(f"  - Response Length: {response_len} characters")
                logger.info(f"  - Retry Count: {attempt}")
                
                return answer

            except (requests.exceptions.Timeout, 
                    requests.exceptions.ConnectionError,
                    requests.exceptions.ReadTimeout,
                    requests.exceptions.ConnectTimeout,
                    requests.exceptions.RequestException,
                    ValueError) as e:
                global _OLLAMA_MODEL_VERIFIED
                _OLLAMA_MODEL_VERIFIED = False
                logger.warning("[LLM_RETRY] Attempt %d failed: %s", attempt + 1, str(e))
                if attempt < max_attempts - 1:
                    sleep_time = 2 ** attempt
                    logger.info(f"Retrying in {sleep_time}s (exponential backoff)...")
                    time.sleep(sleep_time)
                else:
                    logger.error("[LLM_ERROR] Max retries exhausted due to exception: %s", str(e))

            except Exception as e:
                _OLLAMA_MODEL_VERIFIED = False
                logger.error("[LLM_ERROR] Unexpected error on attempt %d: %s", attempt + 1, str(e))
                if attempt < max_attempts - 1:
                    sleep_time = 2 ** attempt
                    logger.info(f"Retrying in {sleep_time}s (exponential backoff)...")
                    time.sleep(sleep_time)
                else:
                    return None

        return None

    def _build_prompt(
        self, query: str, topic: str, statutes: List[Dict], precedents: List[Dict]
    ) -> str:
        """
        Build a concise prompt for legal reasoning under 1200 chars.
        """
        statutes_str = ", ".join([f"{s.get('code', '')}: {s.get('title', '')}" for s in statutes[:3]])
        precedents_str = ", ".join([f"{p.get('case_name', '')} ({p.get('year', '')})" for p in precedents[:2]])

        prompt = f"""You are a professional Indian legal advisor. Analyze the following:
Query: {query[:350]}
Topic: {topic.replace("_", " ").title()}
Statutes: {statutes_str}
Precedents: {precedents_str}

Output EXACTLY this format (150-250 words total, max 300 words, no extra text):
### Case Summary
[Case facts/background]

### Legal Issues
[Key legal questions]

### Applicable Laws
[Relevant statutes & precedents]

### Recommendations
[Actionable next steps]

### Disclaimer
This is for informational purposes only. Consult a lawyer.
=== GENERATE RESPONSE ===
"""
        return prompt

    def _generate_fallback_advice(
        self, query: str, topic: str, statutes: List[Dict], precedents: List[Dict]
    ) -> str:
        """
        Generate fallback advice when Qwen3 is unavailable.
        """
        formatted_topic = topic.replace("_", " ").title()

        advice = f"""Qwen generated no final answer. Showing fallback legal analysis.

You asked a question regarding: {formatted_topic}

Based on our local database, here is the relevant statutory and precedent data:

---
"""
        if statutes:
            advice += "\nAPPLICABLE STATUTES:\n"
            for statute in statutes:
                advice += f"- {statute.get('code')}: {statute.get('title')}\n  Definition: {statute.get('description')}\n  Penalties: {statute.get('penalties')}\n"

        if precedents:
            advice += "\nRELEVANT CASE PRECEDENTS:\n"
            for case in precedents:
                advice += f"- Case: {case.get('case_name')} ({case.get('year')})\n  Court: {case.get('court')}\n  Established Principle: {case.get('holding')}\n"

        advice += """
---
[DISCLAIMER]
This information is provided from our database as a fallback. It is for informational purposes only and does not constitute formal legal advice. Please consult a qualified legal professional to discuss the particulars of your case."""
        return advice

    def analyze_fir_timeline_and_risk(self, text: str) -> Dict[str, any]:
        """
        Query Qwen3:8B to get a chronological timeline of events and legal risk assessment parameters.
        """
        prompt = f"""/no_think You are a professional legal document parser. Extract a chronological timeline of events and a legal risk assessment from the following FIR text.
Return ONLY a valid JSON object. DO NOT explain your reasoning. DO NOT wrap the output in markdown block.

Expected Output Format:
{{
  "timeline": [
    {{"date": "18 Jul 2025", "event": "Fraudulent phone call received"}},
    {{"date": "20 Jul 2025", "event": "Unauthorized transactions detected"}}
  ],
  "risk": {{
    "severity": "High",
    "financial_risk": "High",
    "criminal_exposure": "Medium",
    "complexity": "Medium",
    "evidence_strength": "High"
  }}
}}

For all risk fields, choose exactly one level from: Low, Medium, High, Critical.

FIR Text:
{text[:2500]}
"""
        import json
        logger.info("[QWEN_REQUEST] Generating timeline and risk from FIR text...")
        timeline_system_prompt = "You are a professional legal document parser. Extract structured details from the FIR text and return ONLY a valid JSON object. Do not include any reasoning, conversation, or markdown wrapping."
        response_text = self._attempt_with_retries(
            prompt=prompt, 
            temperature=0.1, 
            timeout=self.timeout,
            check_json=True,
            system_prompt=timeline_system_prompt
        )
        
        default_res = {
            "timeline": [
                {"date": "Registration Date", "event": "FIR registered with police station"}
            ],
            "risk": {
                "severity": "Medium",
                "financial_risk": "Medium",
                "criminal_exposure": "Medium",
                "complexity": "Medium",
                "evidence_strength": "Medium"
            }
        }
        
        if not response_text:
            return default_res
            
        try:
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                cleaned = "\n".join(lines).strip()
                
            parsed = json.loads(cleaned)
            if "timeline" in parsed and "risk" in parsed:
                # Chronological timeline sorting helper
                def parse_timeline_date(date_str):
                    for fmt in ("%d %b %Y", "%d %B %Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                        try:
                            clean_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str).strip()
                            return datetime.strptime(clean_str, fmt)
                        except ValueError:
                            continue
                    return datetime.max
                
                # datetime imported at top

                try:
                    parsed["timeline"].sort(key=lambda x: parse_timeline_date(x.get("date", "")))
                except Exception as sort_e:
                    logger.error(f"Error sorting timeline list: {sort_e}")
                return parsed
        except Exception as e:
            logger.error(f"[LLM_ERROR] Failed to parse Qwen timeline/risk JSON: {e}. Raw response: {response_text}")
            
        return default_res

    def chat_with_fir_context(self, text: str, history: List[Dict], question: str) -> str:
        """
        Respond to user questions regarding the uploaded FIR using Qwen3:8B.
        """
        hist_str = ""
        for msg in history[-5:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            hist_str += f"{role.upper()}: {content}\n"
            
        prompt = f"""/no_think You are a professional Indian legal advisor assisting a user with an uploaded FIR document.
Answer the user's question clearly, directly, and professionally using the FIR context and chat history below.
DO NOT think. DO NOT explain your reasoning. Keep the response under 180 words.

FIR Context:
{text[:3000]}

Chat History:
{hist_str}

User Question: {question}
"""
        chat_system_prompt = "You are a professional Indian legal advisor assisting a user with an uploaded FIR document. Answer the user's question clearly, directly, and professionally using the FIR context and chat history. Keep it concise."
        response_text = self._attempt_with_retries(
            prompt=prompt, 
            temperature=0.3, 
            timeout=self.timeout,
            system_prompt=chat_system_prompt
        )
        return response_text or "I apologize, but I was unable to process your question at this time. Please check your connection to Ollama."

    def analyze_legal_notice_doc(self, text: str) -> Dict[str, any]:
        """
        Query Qwen3:8B to analyze and explain the uploaded legal notice document in plain language.
        """
        prompt = f"""/no_think You are a professional legal document interpreter. Analyze the following notice document text and extract the required details:
Notice Text:
{text[:3000]}

Analyze the notice and generate a valid JSON response. You must replace the placeholders in the JSON with your actual legal analysis based on the notice text. Do not return the placeholder words verbatim.

Required JSON format:
{{
  "sender": "<extract sender name if possible, otherwise 'Not identified'>",
  "recipient": "<extract recipient name if possible, otherwise 'Not identified'>",
  "advocate": "<extract advocate name if possible, otherwise 'None'>",
  "notice_date": "<extract notice date if possible, otherwise 'Not specified'>",
  "response_deadline": "<extract response deadline if possible, otherwise 'Not specified'>",
  "notice_summary": "<Write a detailed summary of the notice claims/allegations>",
  "key_allegations": ["<claim 1>", "<claim 2>", ...],
  "legal_provisions": [
    {{
      "section": "<cited section, e.g. Section 138 of NI Act>",
      "explanation": "<layman explanation of cited section>"
    }}
  ],
  "required_actions": ["<required action 1>", ...],
  "possible_consequences": "<consequences if notice is ignored>",
  "ai_explanation": "<Provide a concise, plain-English overview explaining what this notice is about and its severity>",
  "recommendations": ["<recommended action 1>", ...]
}}
"""
        import json
        logger.info("[QWEN_REQUEST] Analyzing legal notice doc...")
        notice_system_prompt = "You are a professional legal document interpreter. Analyze the notice text and return ONLY a valid JSON object matching the requested schema. Do not include any formatting, reasoning, or extra text."
        response_text = self._attempt_with_retries(
            prompt=prompt, 
            temperature=0.1, 
            timeout=self.timeout,
            check_json=True,
            system_prompt=notice_system_prompt
        )
        
        default_res = {
            "sender": "Not identified",
            "recipient": "Not identified",
            "advocate": "None",
            "notice_date": "Not specified",
            "response_deadline": "Not specified",
            "notice_summary": "No summary available.",
            "key_allegations": [],
            "legal_provisions": [],
            "required_actions": [],
            "possible_consequences": "Failing to respond may lead to legal actions as stated in the notice.",
            "ai_explanation": "No explanation available.",
            "recommendations": [
                "Read the notice carefully.",
                "Preserve relevant documents.",
                "Consider consulting a qualified advocate before responding."
            ]
        }
        
        if not response_text:
            return default_res
            
        try:
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                if lines[0].startswith("```json") or lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                cleaned = "\n".join(lines).strip()
            
            parsed = json.loads(cleaned)
            return parsed
        except Exception as e:
            logger.error(f"[LLM_ERROR] Failed to parse Qwen notice analysis JSON: {e}. Raw response: {response_text}")
            
        return default_res

