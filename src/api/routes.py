import os
import time
import shutil
import logging
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
from src.services.legal_pipeline import LegalPipeline
from src.services.fir_processor import FIRProcessor

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Indian Legal Advisor API",
    description="AI-powered legal advisory system for Indian law",
    version="1.0.0"
)

# Initialize pipeline
pipeline = None


class LegalQueryRequest(BaseModel):
    """Request model for legal query"""
    query: str
    domain_threshold: Optional[float] = 0.3


@app.on_event("startup")
async def startup_event():
    """Initialize pipeline on startup"""
    global pipeline
    print("[API] Initializing Legal Pipeline...")
    pipeline = LegalPipeline()
    print("[API] \u2713 Pipeline ready")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Indian Legal Advisor"}


@app.get("/topics")
async def get_available_topics():
    """Get list of available legal topics"""
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    
    topics = pipeline.get_available_topics()
    return {"topics": topics}


@app.post("/api/analyze", response_model=dict)
async def analyze_legal_query(request: LegalQueryRequest):
    """
    Analyze a legal query and provide legal advice.
    
    Pipeline:
    1. Validate it's a legal query
    2. Classify into legal topic
    3. Predict relevant statutes
    4. Retrieve matching precedents from FAISS
    5. Generate legal advice via Qwen3:8B
    
    Returns complete legal analysis with statutes, precedents, and advice.
    """
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    
    # Validate input
    if not request.query or len(request.query.strip()) < 10:
        raise HTTPException(
            status_code=400, 
            detail="Query must be at least 10 characters"
        )
    
    try:
        # Run complete pipeline
        result = pipeline.analyze(
            request.query, 
            domain_threshold=request.domain_threshold
        )
        
        return result
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing query: {str(e)}"
        )


@app.post("/api/analyze-fir", response_model=dict)
async def analyze_fir_endpoint(file: UploadFile = File(...)):
    """
    Upload and analyze an FIR document (PDF, JPG, JPEG, PNG).
    """
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
        
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".jpg", ".jpeg", ".png"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {ext}. Only PDF, JPG, JPEG, PNG are supported."
        )
        
    # Save UploadFile to a temporary file
    temp_dir = os.path.join(os.getcwd(), "temp_uploads")
    os.makedirs(temp_dir, exist_ok=True)
    
    # Generate a unique temp file path
    temp_file_name = f"temp_{int(time.time())}_{file.filename}"
    temp_file_path = os.path.join(temp_dir, temp_file_name)
    
    current_stage = "File Upload / Initialization"
    extracted_text = ""
    fir_details = {}
    ocr_time = 0.0
    extraction_time = 0.0
    t_classify = 0.0
    t_statutes = 0.0
    t_retrieval = 0.0
    t_gen = 0.0
    total_time = 0.0
    
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 1. Process file to extract and clean text
        current_stage = "OCR / Text Extraction"
        logger.info(f"[PIPELINE_STAGE] {current_stage}")
        t_ocr_start = time.time()
        extracted_text = FIRProcessor.process_file(temp_file_path)
        ocr_time = time.time() - t_ocr_start
        logger.info(f"[TIMING] OCR Time: {ocr_time:.3f} seconds")
        
        if not extracted_text.strip():
            raise ValueError("Could not extract any text from the document. Please ensure the document contains readable text.")
            
    except Exception as outer_e:
        # OCR failed completely - we cannot proceed without raw text
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error during {current_stage}: {str(outer_e)}"
        )

    # Any failure after this point should return a partial success JSON instead of raising HTTP 500
    try:
        # 2. Extract structured fields using LLM
        current_stage = "FIR Metadata Extraction"
        logger.info(f"[PIPELINE_STAGE] {current_stage}")
        t_extract_start = time.time()
        fir_details = pipeline.llm.extract_fir_details(extracted_text)
        extraction_time = time.time() - t_extract_start
        logger.info(f"[TIMING] Regex Extraction Time: {extraction_time:.3f} seconds")
        
        # 3. Analyze using the pipeline
        current_stage = "Pipeline Analysis & Precedent Retrieval"
        logger.info(f"[PIPELINE_STAGE] {current_stage}")
        analysis_result = pipeline.analyze_fir_text(fir_details)
        
        # Extract timings from pipeline
        perf = analysis_result.get("performance", {})
        t_classify = perf.get("classification_time_seconds", 0.0)
        t_statutes = perf.get("statute_prediction_time_seconds", 0.0)
        t_retrieval = perf.get("retrieval_time_seconds", 0.0)
        t_gen = perf.get("generation_time_seconds", 0.0)
        total_time = perf.get("total_time_seconds", 0.0)
        
        # Build performance metrics dictionary
        total_pipeline_time = round(ocr_time + extraction_time + total_time, 3)
        performance_metrics = {
            "ocr_time_seconds": round(ocr_time, 3),
            "regex_extraction_time_seconds": round(extraction_time, 3),
            "inlegalbert_time_seconds": round(t_classify, 3),
            "statute_prediction_time_seconds": round(t_statutes, 3),
            "faiss_retrieval_time_seconds": round(t_retrieval, 3),
            "qwen_generation_time_seconds": round(t_gen, 3),
            "total_pipeline_time_seconds": total_pipeline_time,
            # Compatibility keys
            "total_time_seconds": total_pipeline_time,
            "classification_time_seconds": round(t_classify, 3),
            "retrieval_time_seconds": round(t_retrieval, 3),
            "generation_time_seconds": round(t_gen, 3),
            "metadata_extraction_time_seconds": round(extraction_time, 3),
            "retrieved_precedents": perf.get("retrieved_precedents", 0),
            "current_stage": "Completed"
        }
        
        analysis_result["performance"] = performance_metrics
        analysis_result["extracted_text"] = extracted_text
        
        # Log the times as requested
        logger.info(f"=== TIMING METRICS ===")
        logger.info(f"OCR Time: {ocr_time:.3f} sec")
        logger.info(f"Regex Extraction Time: {extraction_time:.3f} sec")
        logger.info(f"InLegalBERT Time: {t_classify:.3f} sec")
        logger.info(f"Statute Prediction Time: {t_statutes:.3f} sec")
        logger.info(f"FAISS Retrieval Time: {t_retrieval:.3f} sec")
        logger.info(f"Qwen Generation Time: {t_gen:.3f} sec")
        logger.info(f"Total Pipeline Time: {total_pipeline_time:.3f} sec")
        
        # If Qwen fails inside the pipeline (returns fallback warning or empty)
        legal_adv = analysis_result.get("legal_advice", "")
        if not legal_adv or not legal_adv.strip() or analysis_result.get("status") == "partial_success":
            current_stage = "Legal Advice Generation (Qwen Failed)"
            logger.info(f"[PIPELINE_STAGE] {current_stage}")
            analysis_result["status"] = "partial_success"
            analysis_result["performance"]["current_stage"] = current_stage
        else:
            current_stage = "Completed"
            logger.info(f"[PIPELINE_STAGE] {current_stage}")
            analysis_result["status"] = "success"
            analysis_result["performance"]["current_stage"] = current_stage
            
        logger.info(f"[API_RESPONSE_STATUS] {analysis_result.get('status')}")
        return analysis_result
        
    except Exception as inner_e:
        # Step 2 (Metadata Extraction) or Step 3 (Analysis / Qwen generation) failed, return extracted details instead of throwing
        print(f"[API_WARN] Processing stopped at stage: {current_stage} ({inner_e}). Returning fallback response.")
        
        # Ensure we have some default details if metadata extraction failed or was incomplete
        if not fir_details:
            fir_details = {
                "fir_number": "Not extracted",
                "police_station": "Not extracted",
                "complainant": "Not extracted",
                "accused": "Not extracted",
                "ipc_sections": [],
                "bns_sections": [],
                "incident_summary": extracted_text[:300] + "..." if len(extracted_text) > 300 else extracted_text,
                "date_of_incident": "Not extracted",
                "location": "Not extracted",
                "nature_of_offence": "Not extracted"
            }
            
        # Retrieve precedents and statutes if possible, or fallback manually
        try:
            query = fir_details.get("incident_summary", "")
            if not query or len(query.strip()) < 10:
                query = f"Incident of crime at police station {fir_details.get('police_station', '')}"
            topic, confidence, _ = pipeline.classifier.classify(query)
            statute_result = pipeline.statute_predictor.predict(topic)
            statutes = statute_result.get("statutes", [])
            
            retrieval_result = pipeline.retriever.retrieve(query, topic, top_k=3, threshold=0.60)
            precedents = retrieval_result.get("precedents", [])
        except Exception as fallback_e:
            print(f"[API_WARN] Secondary classification/retrieval failed during fallback: {fallback_e}")
            topic = "Unknown"
            statutes = []
            precedents = []
            
        fallback_advice = f"""### Qwen generated no final answer. Showing fallback legal analysis.
We successfully processed the document up to the stage of **{current_stage}**, but a subsequent AI generation step failed or timed out.

Here are the details and matched resources we could extract:

**Extracted FIR Details:**
- **FIR Number:** {fir_details.get('fir_number', 'Not found')}
- **Police Station:** {fir_details.get('police_station', 'Not found')}
- **Complainant:** {fir_details.get('complainant', 'Not found')}
- **Accused:** {fir_details.get('accused', 'Not found')}
- **Date:** {fir_details.get('date_of_incident') or fir_details.get('date', 'Not found')}
- **Location:** {fir_details.get('location', 'Not found')}
- **Nature of Offence:** {fir_details.get('nature_of_offence', 'Not found')}
- **Incident Summary:** {fir_details.get('incident_summary', 'Not found')}

**Matched Legal Topic:** {topic.replace('_', ' ').title()}

**Matched Statutes:**
{', '.join(statutes) if statutes else 'No specific statutes matched.'}

Please consult a qualified legal professional for personal legal advice.
"""
        total_pipeline_time = round(ocr_time + extraction_time, 3)
        logger.info("[API_RESPONSE_STATUS] partial_success")
        return {
            "status": "partial_success",
            "fir_summary": fir_details.get("incident_summary", "No incident summary"),
            "fir_number": fir_details.get("fir_number", "Unknown"),
            "police_station": fir_details.get("police_station", "Unknown"),
            "complainant": fir_details.get("complainant", "Unknown"),
            "accused": fir_details.get("accused", "Unknown"),
            "sections": statutes,
            "topic": topic,
            "precedents": precedents,
            "legal_advice": fallback_advice,
            "risk_level": "Medium",
            "extracted_text": extracted_text,
            "performance": {
                "ocr_time_seconds": round(ocr_time, 3),
                "regex_extraction_time_seconds": round(extraction_time, 3),
                "inlegalbert_time_seconds": 0.0,
                "statute_prediction_time_seconds": 0.0,
                "faiss_retrieval_time_seconds": 0.0,
                "qwen_generation_time_seconds": 0.0,
                "total_pipeline_time_seconds": total_pipeline_time,
                # Compatibility
                "total_time_seconds": total_pipeline_time,
                "classification_time_seconds": 0.0,
                "retrieval_time_seconds": 0.0,
                "generation_time_seconds": 0.0,
                "metadata_extraction_time_seconds": round(extraction_time, 3),
                "retrieved_precedents": len(precedents),
                "current_stage": current_stage,
                "error_detail": str(inner_e)
            }
        }
    finally:
        # Clean up temp file
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                pass


@app.get("/")
async def root():
    """Root endpoint with API documentation"""
    return {
        "name": "Indian Legal Advisor API",
        "version": "1.0.0",
        "description": "AI-powered legal advisory system for Indian law",
        "endpoints": {
            "health": "/health",
            "topics": "/topics",
            "analyze": "/api/analyze (POST)",
            "analyze-fir": "/api/analyze-fir (POST)"
        },
        "example_query": {
            "query": "I was forced to work overtime without compensation"
        }
    }


@app.get("/api/health")
async def api_health_check():
    """Health check endpoint returning flat JSON status."""
    return {"status": "healthy"}


@app.get("/api/test-qwen")
async def api_test_qwen():
    """Test endpoint to query Qwen directly with a basic legal prompt."""
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    
    prompt = "What is IPC 420? Answer in 3 sentences."
    start_time = time.time()
    response_text = pipeline.llm._attempt_with_retries(prompt, temperature=0.2)
    time_taken = time.time() - start_time
    
    if response_text:
        return {
            "success": True,
            "response": response_text,
            "time_taken": round(time_taken, 2)
        }
    else:
        return {
            "success": False,
            "response": "Qwen generated no response.",
            "time_taken": round(time_taken, 2)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
