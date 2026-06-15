import requests
import json
import time
import logging
from typing import Dict, List, Optional, Tuple
from src.utils.logger import LegalAdvisorLogger

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
                    return True
        except Exception as e:
            logger.warning("[LLM_ERROR] 'ollama list' check failed: %s", str(e))

        return False

    def _verify_ollama_connection(self) -> bool:
        """
        Verify Ollama server is running and model exists.
        """
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
        response_text = self._attempt_with_retries(prompt, temperature)
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
        
        # Budgeting to keep prompt size strictly under 3000 characters
        summary = fir_details.get('incident_summary') or fir_details.get('incident_description') or "No incident summary."
        if len(summary) > 500:
            summary = summary[:470] + "... [TRUNCATED]"

        ipc_sects = fir_details.get('ipc_sections') or []
        if isinstance(ipc_sects, str):
            ipc_sects = [ipc_sects]
        bns_sects = fir_details.get('bns_sections') or []
        if isinstance(bns_sects, str):
            bns_sects = [bns_sects]
            
        sections_str = ", ".join(ipc_sects + bns_sects)
        if len(sections_str) > 150:
            sections_str = sections_str[:140] + "... [TRUNCATED]"

        # Format statutes
        statutes_compact = []
        for stat in statutes[:3]:  # Top 3 statutes max
            code = stat.get("code", "")
            title = stat.get("title", "")
            desc = stat.get("description", "")
            if len(desc) > 120:
                desc = desc[:115] + "... [TRUNCATED]"
            statutes_compact.append({
                "code": code,
                "title": title,
                "desc": desc
            })
            
        # Format precedents
        precedents_compact = ""
        for idx, prec in enumerate(precedents[:2], 1):  # Top 2 precedents max
            case_name = prec.get('case_name', 'Unknown')
            facts = prec.get('facts', '')
            if len(facts) > 120:
                facts = facts[:115] + "... [TRUNCATED]"
            holding = prec.get('holding', '')
            if len(holding) > 100:
                holding = holding[:95] + "... [TRUNCATED]"
            precedents_compact += f"\n{idx}. Case: {case_name}\nFacts: {facts}\nHolding: {holding}\n"

        prompt = f"""You are an Indian legal advisor.

DO NOT think.
DO NOT explain your reasoning.
DO NOT use chain of thought.
DO NOT generate internal analysis.

Return only the final answer.

Format response in Markdown exactly as:

### 1. Case Summary
...

### 2. Applicable IPC/BNS Sections
...

### 3. Legal Interpretation
...

### 4. Potential Punishments
...

### 5. Relevant Precedents
...

### 6. Rights of Complainant
...

### 7. Rights of Accused
...

### 8. Recommended Next Steps
...

### 9. Legal Risks
...

### 10. Disclaimer
...

Maximum 250 words.

=== FIR DETAILS ===
- FIR Number: {fir_details.get('fir_number', 'Not found')}
- Police Station: {fir_details.get('police_station', 'Not found')}
- Complainant: {fir_details.get('complainant', 'Not found')}
- Accused: {fir_details.get('accused', 'Not found')}
- Nature of Offence: {fir_details.get('nature_of_offence', 'Not found')}
- Location: {fir_details.get('location', 'Not found')}
- Date: {fir_details.get('date_of_incident') or fir_details.get('date', 'Not found')}
- Sections: {sections_str}
- Incident Summary: {summary}

=== APPLICABLE STATUTES ===
{json.dumps(statutes_compact, indent=1)}

=== SIMILAR PRECEDENTS ===
{precedents_compact}
"""
        max_prompt_chars = 3000
        if len(prompt) > max_prompt_chars:
            logger.warning("[LLM_WARN] Prompt length (%d) exceeds limit. Safety truncating to %d characters.", len(prompt), max_prompt_chars)
            prompt = prompt[:2800] + "\n\n[TRUNCATED TO FIT LIMIT]\n=== GENERATE RESPONSE ==="
            
        start_time = time.time()
        response_text = self._attempt_with_retries(prompt, temperature=0.2, timeout=self.timeout)
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

    def _attempt_with_retries(self, prompt: str, temperature: float, timeout: Optional[int] = None) -> Optional[str]:
        """
        Attempt generation with retry logic and exponential backoff.
        """
        if "qwen" in self.model.lower():
            if not prompt.startswith("/no_think"):
                prompt = "/no_think\n" + prompt

        req_timeout = timeout or self.timeout
        
        max_attempts = 3  # Attempt 1, Attempt 2, Attempt 3
        for attempt in range(max_attempts):
            try:
                # Check model availability first
                if not self._check_model_in_ollama():
                    raise ValueError(f"Ollama model '{self.model}' is missing or Ollama is offline.")

                req_start_time = time.time()
                start_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(req_start_time))
                
                prompt_len = len(prompt)
                prompt_preview = prompt[:100].replace('\n', ' ')
                logger.info(f"[QWEN_REQUEST] Start Time={start_time_str} | Attempt={attempt + 1}/{max_attempts} | Prompt Length={prompt_len} chars")
                logger.info(f"[QWEN_REQUEST] Prompt Preview: {prompt_preview}...")

                http_response = requests.post(
                    self.generate_endpoint,
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "system": "You are an Indian legal assistant. Respond directly. Do not think step-by-step. Do not explain reasoning. Provide concise legal advice.",
                        "stream": False,
                        "options": {
                            "temperature": 0.2,
                            "num_predict": 300,
                            "top_p": 0.9
                        }
                    },
                    timeout=req_timeout,
                )
                
                req_end_time = time.time()
                end_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(req_end_time))
                actual_duration = req_end_time - req_start_time
                logger.info(f"[QWEN_REQUEST] End Time={end_time_str} | Actual Duration={actual_duration:.3f} seconds")

                # Log Qwen Raw Response
                logger.info(f"[RAW_QWEN_RESPONSE] {http_response.text}")

                if http_response.status_code == 200:
                    response = http_response.json()
                    logger.info(f"RAW_QWEN_RESPONSE={response}")
                    
                    answer = ""
                    if isinstance(response, dict):
                        answer = (
                            response.get("message", {}).get("content")
                            or response.get("response")
                            or response.get("generated_text")
                            or response.get("text")
                            or ""
                        )
                    
                    # If response is empty but thinking contains text, use thinking as fallback
                    if (not answer or not answer.strip()) and isinstance(response, dict):
                        thinking_content = response.get("thinking", "")
                        if thinking_content and thinking_content.strip():
                            answer = thinking_content
                    
                    # Detect empty responses and raise exception
                    if answer is None or not isinstance(answer, str) or len(answer.strip()) == 0:
                        raise ValueError("Ollama returned an empty response, whitespace only, or None.")
                    
                    # Strip whitespace
                    answer = answer.strip()
                    
                    # Remove thinking tags/markers
                    if "</think>" in answer:
                        answer = answer.split("</think>")[-1].strip()
                    if "...done thinking." in answer:
                        answer = answer.split("...done thinking.")[-1].strip()
                        
                    # Add parser
                    if "...done thinking." in answer:
                        answer = answer.split("...done thinking.")[-1].strip()
                        
                    # Detect if parsed answer becomes empty after stripping
                    if len(answer.strip()) == 0:
                        raise ValueError("Parsed answer is empty after removing thinking block.")

                    # Log parsed answer
                    logger.info(f"PARSED_QWEN_ANSWER={answer}")
                    logger.info(f"[PARSED_QWEN_ANSWER] {answer}")
                    
                    eval_count = response.get("eval_count", 0) if isinstance(response, dict) else 0
                    logger.info(f"[QWEN_OUTPUT_LENGTH] {len(answer)}")
                    logger.info(f"[QWEN_RESPONSE] Tokens returned (eval_count)={eval_count}")
                    
                    # Return parsed answer
                    return answer
                else:
                    logger.error("[LLM_ERROR] HTTP %d: %s", http_response.status_code, http_response.text[:200])
                    raise ValueError(f"Ollama returned HTTP {http_response.status_code}")

            except (requests.exceptions.Timeout, 
                    requests.exceptions.ConnectionError,
                    requests.exceptions.ReadTimeout,
                    requests.exceptions.ConnectTimeout,
                    requests.exceptions.RequestException,
                    ValueError) as e:
                logger.warning("[LLM_RETRY] Attempt %d failed: %s", attempt + 1, str(e))
                if attempt < max_attempts - 1:
                    sleep_time = 2 ** attempt
                    logger.info(f"Retrying in {sleep_time}s (exponential backoff)...")
                    time.sleep(sleep_time)
                else:
                    logger.error("[LLM_ERROR] Max retries exhausted due to exception: %s", str(e))

            except Exception as e:
                logger.error("[LLM_ERROR] Unexpected error: %s", str(e))
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
        Build professionally structured prompt for legal reasoning.
        """
        formatted_topic = topic.replace("_", " ").title()

        statute_text = "APPLICABLE STATUTES AND LEGAL PROVISIONS:\n"
        if statutes:
            for i, statute in enumerate(statutes, 1):
                code = statute.get("code", "Statute")
                title = statute.get("title", "No title")
                description = statute.get("description", "No description")
                penalties = statute.get("penalties", "Not specified")

                statute_text += f"\n{i}. {code}: {title}\n"
                statute_text += f"   Definition/Scope: {description}\n"
                statute_text += f"   Enforcement/Penalties: {penalties}\n"
        else:
            statute_text += "\n[Note: Limited statutory coverage for this topic in database]\n"

        precedent_text = "\nRELEVANT LEGAL PRECEDENTS:\n"
        if precedents:
            for i, case in enumerate(precedents, 1):
                case_name = case.get("case_name", "Case Name Unknown")
                year = case.get("year", "Year Unknown")
                court = case.get("court", "Court Unknown")
                facts = case.get("facts", "Facts not available")
                holding = case.get("holding", "Holding not available")

                precedent_text += f"\n{i}. {case_name} ({year})\n"
                precedent_text += f"   Court: {court}\n"
                precedent_text += f"   Case Facts: {facts}\n"
                precedent_text += f"   Legal Principle Established: {holding}\n"
        else:
            precedent_text += "\n[Note: No precedents found for this topic in database]\n"

        prompt = f"""You are a professional Indian legal advisor. Analyze the following query using ONLY the provided statutes and precedents.

=== LEGAL TOPIC ===
{formatted_topic}

=== USER QUERY ===
{query}

{statute_text}
{precedent_text}

=== ANALYSIS REQUIREMENTS ===
Your response MUST:

1. LEGAL ANALYSIS:
   - Explain how applicable statutes relate to the user's situation
   - Reference the specific sections and their requirements
   - Connect case law (precedents) to the current facts

2. PRACTICAL GUIDANCE:
   - Provide actionable steps based on the applicable law
   - Explain available legal remedies and procedures
   - Clarify timelines and important considerations

3. CRITICAL CONSTRAINTS:
   - ONLY reference the statutes and precedents provided above
   - DO NOT invent laws, sections, or cases
   - If situation is not covered, state clearly: "This specific scenario is not addressed in available database resources"
   - Always note limitations of database coverage

4. MANDATORY DISCLAIMER:
   - Include a clear legal disclaimer at the end
   - State this is for informational purposes only
   - Recommend consulting a qualified lawyer for specific guidance

=== RESPONSE FORMAT ===
Structure your response as:

[LEGAL ANALYSIS]
Explain applicable laws and precedents...

[PRACTICAL GUIDANCE]
Steps the user should consider...

[RELEVANT CASE LAW]
How precedents apply...

[DISCLAIMER]
Legal disclaimer statement...

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
