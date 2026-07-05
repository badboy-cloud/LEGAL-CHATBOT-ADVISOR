import sys
from pathlib import Path

# Dynamically bootstrap project root to sys.path to prevent ModuleNotFoundError
current_file = Path(__file__).resolve()
root_dir = current_file.parent
while root_dir.parent != root_dir:
    if (root_dir / 'src').exists() or (root_dir / 'frontend').exists():
        break
    root_dir = root_dir.parent

for p in [root_dir, root_dir / 'src']:
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))

import os
import time
import shutil
import logging
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
from typing import Optional, List

from src.services.legal_pipeline import LegalPipeline
from src.services.fir_processor import FIRProcessor
from src.api.auth import get_current_user, require_admin, hash_password, verify_password, create_access_token
from src.utils.rate_limiter import check_rate_limit
from src.utils.db_manager import DBManager
from src.utils.malware_scanner import scan_file_for_malware
from src.utils.crypto_helper import encrypt_data, decrypt_data

logger = logging.getLogger(__name__)

# Initialize FastAPI app with rate limiting globally enforced
app = FastAPI(
    title="Indian Legal Advisor API",
    description="AI-powered legal advisory system for Indian law with enterprise-grade security",
    version="1.0.0",
    dependencies=[Depends(check_rate_limit)]
)

# Custom Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none';"
        # HSTS only applies to HTTPS deployments
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# Configure CORS (Restrict origins in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize pipeline
pipeline = None

try:
    from src.utils.statute_explainer import get_explainer_details
except ImportError:
    try:
        from utils.statute_explainer import get_explainer_details
    except ImportError:
        get_explainer_details = None

# --- REQUEST & RESPONSE SCHEMAS ---

class UserAuthRequest(BaseModel):
    username: str
    password: str
    role: Optional[str] = "User"

class LegalQueryRequest(BaseModel):
    query: str

class ChatFIRRequest(BaseModel):
    text: str
    question: str
    history: list = []

class UpdateRoleRequest(BaseModel):
    role: str

# --- STARTUP EVENT ---

@app.on_event("startup")
async def startup_event():
    """Initialize pipeline on startup"""
    global pipeline
    print("[API] Initializing Legal Pipeline...")
    pipeline = LegalPipeline()
    print("[API] [OK] Pipeline ready")

# --- UNPROTECTED ENDPOINTS ---

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Indian Legal Advisor"}

@app.get("/api/health")
async def api_health_check():
    """Health check endpoint returning flat JSON status."""
    return {"status": "healthy"}

@app.get("/")
async def root():
    """Root endpoint with API documentation info"""
    return {
        "name": "Indian Legal Advisor API",
        "version": "1.0.0",
        "description": "AI-powered legal advisory system for Indian law with enterprise-grade security",
        "endpoints": {
            "health": "/health",
            "login": "/api/login (POST)",
            "register": "/api/register (POST)",
            "topics": "/topics (GET - Protected)",
            "analyze": "/api/analyze (POST - Protected)",
            "analyze-fir": "/api/analyze-fir (POST - Protected)",
            "analyze-notice": "/api/analyze-notice (POST - Protected)"
        }
    }

# --- AUTHENTICATION ENDPOINTS ---

@app.post("/api/register", response_model=dict)
async def register_user(request: Request, auth_req: UserAuthRequest):
    """
    User registration endpoint.
    """
    start_time = time.time()
    ip = request.client.host if request.client else "unknown"
    
    username = auth_req.username.strip()
    password = auth_req.password.strip()
    role = auth_req.role.strip() if auth_req.role else "User"

    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters long.")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long.")
    if role not in ["User", "Admin"]:
        raise HTTPException(status_code=400, detail="Invalid role specified.")

    hashed = hash_password(password)
    success = DBManager.register_user(username, hashed, role)
    duration = time.time() - start_time
    
    DBManager.log_audit_event(
        username=username,
        role=role,
        ip_address=ip,
        action="User Registration",
        endpoint="/api/register",
        status="success" if success else "failed",
        processing_time=duration
    )
    
    if success:
        return {"success": True, "message": "User registered successfully."}
    raise HTTPException(status_code=400, detail="Username already exists.")

@app.post("/api/login", response_model=dict)
async def login_user(request: Request, auth_req: UserAuthRequest):
    """
    User authentication (login) endpoint. Generates a signed JWT bearer token.
    """
    start_time = time.time()
    ip = request.client.host if request.client else "unknown"
    
    username = auth_req.username.strip()
    password = auth_req.password.strip()
    
    user = DBManager.get_user_by_username(username)
    duration = time.time() - start_time
    
    if not user or not verify_password(password, user["password_hash"]):
        DBManager.log_audit_event(
            username=username,
            role="Unknown",
            ip_address=ip,
            action="User Login Attempt",
            endpoint="/api/login",
            status="unauthorized",
            processing_time=duration
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password."
        )
        
    # Generate Access Token
    token = create_access_token(user_id=user["id"], username=user["username"], role=user["role"])
    DBManager.log_audit_event(
        username=user["username"],
        role=user["role"],
        ip_address=ip,
        action="User Login Success",
        endpoint="/api/login",
        status="success",
        processing_time=duration
    )
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user["username"],
        "role": user["role"]
    }

# --- PROTECTED API ENDPOINTS ---

@app.get("/topics")
async def get_available_topics(request: Request, current_user: dict = Depends(get_current_user)):
    """Get list of available legal topics"""
    start_time = time.time()
    ip = request.client.host if request.client else "unknown"
    
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    
    topics = pipeline.get_available_topics()
    duration = time.time() - start_time
    
    DBManager.log_audit_event(
        username=current_user["username"],
        role=current_user["role"],
        ip_address=ip,
        action="Get Topics List",
        endpoint="/topics",
        status="success",
        processing_time=duration
    )
    return {"topics": topics}

@app.post("/api/analyze", response_model=dict)
async def analyze_legal_query(request: Request, query_req: LegalQueryRequest, current_user: dict = Depends(get_current_user)):
    """
    Analyze a legal query and provide Qwen-generated legal advice.
    """
    start_time = time.time()
    ip = request.client.host if request.client else "unknown"
    
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    
    if not query_req.query or len(query_req.query.strip()) < 10:
        raise HTTPException(
            status_code=400, 
            detail="Query must be at least 10 characters long"
        )
    
    try:
        DEFAULT_DOMAIN_THRESHOLD = 0.30
        result = pipeline.analyze(
            query_req.query, 
            domain_threshold=DEFAULT_DOMAIN_THRESHOLD
        )
        duration = time.time() - start_time
        
        DBManager.log_audit_event(
            username=current_user["username"],
            role=current_user["role"],
            ip_address=ip,
            action="Legal Query Advisory",
            endpoint="/api/analyze",
            status="success",
            processing_time=duration
        )
        return result
        
    except Exception as e:
        duration = time.time() - start_time
        DBManager.log_audit_event(
            username=current_user["username"],
            role=current_user["role"],
            ip_address=ip,
            action="Legal Query Advisory Error",
            endpoint="/api/analyze",
            status="error",
            processing_time=duration
        )
        logger.error(f"Error processing query: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing query: {str(e)}"
        )

@app.post("/api/analyze-fir", response_model=dict)
async def analyze_fir_endpoint(request: Request, file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """
    Upload, scan for malware, encrypt, and analyze an FIR document.
    """
    start_time = time.time()
    ip = request.client.host if request.client else "unknown"
    
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
        
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".jpg", ".jpeg", ".png"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {ext}. Only PDF, JPG, JPEG, PNG are supported."
        )

    # Secure uploads directory setup
    temp_dir = os.path.join(os.getcwd(), "temp_uploads")
    os.makedirs(temp_dir, exist_ok=True)
    
    # Generate unique filenames for security isolation
    temp_file_name = f"raw_{int(time.time())}_{file.filename}"
    temp_file_path = os.path.join(temp_dir, temp_file_name)
    decrypted_file_path = os.path.join(temp_dir, f"dec_{int(time.time())}_{file.filename}")
    
    try:
        # Save upload temporarily to run scanner
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 1. Malware Scanning
        is_clean, err_msg = scan_file_for_malware(temp_file_path)
        if not is_clean:
            raise HTTPException(status_code=400, detail=f"File validation failed: {err_msg}")
            
        # 2. AES-256 File Encryption & Storage
        with open(temp_file_path, "rb") as f:
            raw_bytes = f.read()
        encrypted_bytes = encrypt_data(raw_bytes)
        
        # Save the encrypted file securely on disk
        secure_uploads_dir = os.path.join(os.getcwd(), "data", "uploads")
        os.makedirs(secure_uploads_dir, exist_ok=True)
        secure_file_path = os.path.join(secure_uploads_dir, f"enc_fir_{int(time.time())}_{file.filename}")
        with open(secure_file_path, "wb") as f:
            f.write(encrypted_bytes)
            
        # Register document metadata in encrypted Database
        DBManager.add_document(
            filename=file.filename,
            file_path=secure_file_path,
            uploaded_by=current_user["id"],
            document_type="fir"
        )
        
        # 3. Decrypt temporarily for OCR extraction
        decrypted_bytes = decrypt_data(encrypted_bytes)
        with open(decrypted_file_path, "wb") as f:
            f.write(decrypted_bytes)
            
        # Run text extraction on the temporary decrypted copy
        t_ocr_start = time.time()
        extracted_text = FIRProcessor.process_file(decrypted_file_path)
        ocr_time = time.time() - t_ocr_start
        
        if not extracted_text.strip():
            raise ValueError("Could not extract readable text from the document.")

    except HTTPException:
        # Pass HTTPExceptions straight back
        raise
    except Exception as outer_e:
        duration = time.time() - start_time
        DBManager.log_audit_event(
            username=current_user["username"],
            role=current_user["role"],
            ip_address=ip,
            action="FIR Analysis Failure",
            endpoint="/api/analyze-fir",
            status="error",
            processing_time=duration
        )
        # Delete raw upload
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing FIR document: {str(outer_e)}"
        )
    finally:
        # Delete unencrypted raw upload from disk immediately
        if os.path.exists(temp_file_path):
            try: os.remove(temp_file_path)
            except Exception: pass
            
        # Clean up temporary decrypted OCR file
        if os.path.exists(decrypted_file_path):
            try: os.remove(decrypted_file_path)
            except Exception: pass

    # Run analysis using legal pipeline
    try:
        t_extract_start = time.time()
        fir_details = pipeline.llm.extract_fir_details(extracted_text)
        extraction_time = time.time() - t_extract_start
        
        fir_details["ocr_time"] = ocr_time
        analysis_result = pipeline.analyze_fir_text(fir_details)
        
        perf = analysis_result.get("performance", {})
        t_classify = perf.get("classification_time_seconds", 0.0)
        t_statutes = perf.get("statute_prediction_time_seconds", 0.0)
        t_retrieval = perf.get("retrieval_time_seconds", 0.0)
        t_gen = perf.get("generation_time_seconds", 0.0)
        total_time = perf.get("total_time_seconds", 0.0)
        
        total_pipeline_time = round(ocr_time + extraction_time + total_time, 3)
        analysis_result["performance"] = {
            "ocr_time_seconds": round(ocr_time, 3),
            "regex_extraction_time_seconds": round(extraction_time, 3),
            "inlegalbert_time_seconds": round(t_classify, 3),
            "statute_prediction_time_seconds": round(t_statutes, 3),
            "faiss_retrieval_time_seconds": round(t_retrieval, 3),
            "qwen_generation_time_seconds": round(t_gen, 3),
            "total_pipeline_time_seconds": total_pipeline_time
        }
        analysis_result["extracted_text"] = extracted_text
        analysis_result["status"] = "success"
        
        duration = time.time() - start_time
        DBManager.log_audit_event(
            username=current_user["username"],
            role=current_user["role"],
            ip_address=ip,
            action="FIR Document Analysis",
            endpoint="/api/analyze-fir",
            status="success",
            processing_time=duration
        )
        return analysis_result

    except Exception as inner_e:
        # Return partial success structured response on backend model issues
        duration = time.time() - start_time
        DBManager.log_audit_event(
            username=current_user["username"],
            role=current_user["role"],
            ip_address=ip,
            action="FIR Document Analysis Partial Success",
            endpoint="/api/analyze-fir",
            status="partial_success",
            processing_time=duration
        )
        fallback_advice = f"### Fallback advice - analysis stage interrupted ({inner_e})"
        return {
            "status": "partial_success",
            "fir_summary": fir_details.get("incident_summary", "No summary"),
            "fir_number": fir_details.get("fir_number", "Unknown"),
            "police_station": fir_details.get("police_station", "Unknown"),
            "complainant": fir_details.get("complainant", "Unknown"),
            "accused": fir_details.get("accused", "Unknown"),
            "witnesses": fir_details.get("witnesses_list", []),
            "witnesses_str": fir_details.get("witnesses", "None"),
            "sections": [],
            "legal_sections": [],
            "statutes_explainers": {},
            "crpc_sections": [],
            "officer_details": "Review Required",
            "evidence_submitted": "None",
            "timeline": [],
            "risk_assessment": {},
            "dates": [],
            "location": "Not found",
            "topic": "Unknown",
            "precedents": [],
            "legal_advice": fallback_advice,
            "extracted_text": extracted_text,
            "performance": {"total_pipeline_time_seconds": round(time.time() - start_time, 3)}
        }

@app.post("/api/chat-fir", response_model=dict)
async def chat_fir_endpoint(request: Request, chat_req: ChatFIRRequest, current_user: dict = Depends(get_current_user)):
    """
    Chat with the uploaded FIR using document context and chat history.
    """
    start_time = time.time()
    ip = request.client.host if request.client else "unknown"
    
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    try:
        response_text = pipeline.llm.chat_with_fir_context(
            text=chat_req.text,
            history=chat_req.history,
            question=chat_req.question
        )
        duration = time.time() - start_time
        
        DBManager.log_audit_event(
            username=current_user["username"],
            role=current_user["role"],
            ip_address=ip,
            action="FIR Interactive Chat",
            endpoint="/api/chat-fir",
            status="success",
            processing_time=duration
        )
        return {"response": response_text}
    except Exception as e:
        duration = time.time() - start_time
        DBManager.log_audit_event(
            username=current_user["username"],
            role=current_user["role"],
            ip_address=ip,
            action="FIR Interactive Chat Error",
            endpoint="/api/chat-fir",
            status="error",
            processing_time=duration
        )
        logger.error(f"Error in chat_fir_endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze-notice", response_model=dict)
async def analyze_notice_endpoint(request: Request, file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """
    Upload, scan for malware, encrypt, and analyze a legal notice document.
    """
    start_time = time.time()
    ip = request.client.host if request.client else "unknown"
    
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
        
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".jpg", ".jpeg", ".png"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {ext}. Only PDF, JPG, JPEG, PNG are supported."
        )
        
    temp_dir = os.path.join(os.getcwd(), "temp_uploads")
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_name = f"raw_notice_{int(time.time())}_{file.filename}"
    temp_file_path = os.path.join(temp_dir, temp_file_name)
    decrypted_file_path = os.path.join(temp_dir, f"dec_notice_{int(time.time())}_{file.filename}")
    
    try:
        # Save upload temporarily to run scanner
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 1. Malware Scanning
        is_clean, err_msg = scan_file_for_malware(temp_file_path)
        if not is_clean:
            raise HTTPException(status_code=400, detail=f"File validation failed: {err_msg}")
            
        # 2. AES-256 File Encryption & Storage
        with open(temp_file_path, "rb") as f:
            raw_bytes = f.read()
        encrypted_bytes = encrypt_data(raw_bytes)
        
        # Save the encrypted file securely on disk
        secure_uploads_dir = os.path.join(os.getcwd(), "data", "uploads")
        os.makedirs(secure_uploads_dir, exist_ok=True)
        secure_file_path = os.path.join(secure_uploads_dir, f"enc_notice_{int(time.time())}_{file.filename}")
        with open(secure_file_path, "wb") as f:
            f.write(encrypted_bytes)
            
        # Register document metadata in Database
        DBManager.add_document(
            filename=file.filename,
            file_path=secure_file_path,
            uploaded_by=current_user["id"],
            document_type="notice"
        )
        
        # 3. Decrypt temporarily for OCR extraction
        decrypted_bytes = decrypt_data(encrypted_bytes)
        with open(decrypted_file_path, "wb") as f:
            f.write(decrypted_bytes)
            
        # Run text extraction
        start_ocr = time.time()
        extracted_text = FIRProcessor.process_file(decrypted_file_path)
        ocr_time = time.time() - start_ocr
        
        if not extracted_text.strip():
            raise ValueError("Could not extract readable text from the document.")

    except HTTPException:
        raise
    except Exception as e:
        duration = time.time() - start_time
        DBManager.log_audit_event(
            username=current_user["username"],
            role=current_user["role"],
            ip_address=ip,
            action="Notice Analysis Failure",
            endpoint="/api/analyze-notice",
            status="error",
            processing_time=duration
        )
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Delete unencrypted uploads immediately
        if os.path.exists(temp_file_path):
            try: os.remove(temp_file_path)
            except Exception: pass
        if os.path.exists(decrypted_file_path):
            try: os.remove(decrypted_file_path)
            except Exception: pass

    # Run analysis using legal pipeline
    try:
        from src.utils.cache_manager import LegalAdvisorCache
        cached_res = LegalAdvisorCache.get("analyze-notice", extracted_text)
        if cached_res:
            duration = time.time() - start_time
            DBManager.log_audit_event(
                username=current_user["username"],
                role=current_user["role"],
                ip_address=ip,
                action="Notice Analysis Cache Hit",
                endpoint="/api/analyze-notice",
                status="success",
                processing_time=duration
            )
            return cached_res

        # Run analysis using pipeline
        analysis = pipeline.analyze_notice_text(extracted_text, ocr_time)
        analysis["extracted_text"] = extracted_text
        
        # Cache response
        LegalAdvisorCache.set("analyze-notice", extracted_text, analysis)
        
        duration = time.time() - start_time
        DBManager.log_audit_event(
            username=current_user["username"],
            role=current_user["role"],
            ip_address=ip,
            action="Notice Analysis Complete",
            endpoint="/api/analyze-notice",
            status="success",
            processing_time=duration
        )
        return analysis
        
    except Exception as e:
        duration = time.time() - start_time
        DBManager.log_audit_event(
            username=current_user["username"],
            role=current_user["role"],
            ip_address=ip,
            action="Notice Analysis Pipeline Error",
            endpoint="/api/analyze-notice",
            status="error",
            processing_time=duration
        )
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/test-qwen")
async def api_test_qwen(request: Request, current_user: dict = Depends(get_current_user)):
    """Test endpoint to query Qwen directly with a basic legal prompt."""
    start_time = time.time()
    ip = request.client.host if request.client else "unknown"
    
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    
    prompt = "What is IPC 420? Answer in 3 sentences."
    response_text = pipeline.llm._attempt_with_retries(prompt, temperature=0.2)
    duration = time.time() - start_time
    
    DBManager.log_audit_event(
        username=current_user["username"],
        role=current_user["role"],
        ip_address=ip,
        action="Direct Qwen Query Test",
        endpoint="/api/test-qwen",
        status="success" if response_text else "failed",
        processing_time=duration
    )
    
    if response_text:
        return {
            "success": True,
            "response": response_text,
            "time_taken": round(duration, 2)
        }
    else:
        return {
            "success": False,
            "response": "Qwen generated no response.",
            "time_taken": round(duration, 2)
        }

# --- ADMIN API ENDPOINTS (RESTRICTED TO ADMINS) ---

@app.get("/api/admin/users", response_model=List[dict])
async def admin_get_users(request: Request, current_user: dict = Depends(require_admin)):
    """
    Get all registered users. Admin role required.
    """
    start_time = time.time()
    ip = request.client.host if request.client else "unknown"
    
    users = DBManager.get_all_users()
    duration = time.time() - start_time
    
    DBManager.log_audit_event(
        username=current_user["username"],
        role=current_user["role"],
        ip_address=ip,
        action="Admin Fetch Users",
        endpoint="/api/admin/users",
        status="success",
        processing_time=duration
    )
    return users

@app.get("/api/admin/logs", response_model=List[dict])
async def admin_get_logs(request: Request, current_user: dict = Depends(require_admin)):
    """
    Get all system audit logs. Admin role required.
    """
    start_time = time.time()
    ip = request.client.host if request.client else "unknown"
    
    logs = DBManager.get_audit_logs()
    duration = time.time() - start_time
    
    DBManager.log_audit_event(
        username=current_user["username"],
        role=current_user["role"],
        ip_address=ip,
        action="Admin Fetch Audit Logs",
        endpoint="/api/admin/logs",
        status="success",
        processing_time=duration
    )
    return logs

@app.get("/api/admin/documents", response_model=List[dict])
async def admin_get_documents(request: Request, current_user: dict = Depends(require_admin)):
    """
    Get all uploaded documents. Admin role required.
    """
    start_time = time.time()
    ip = request.client.host if request.client else "unknown"
    
    docs = DBManager.get_all_documents()
    duration = time.time() - start_time
    
    DBManager.log_audit_event(
        username=current_user["username"],
        role=current_user["role"],
        ip_address=ip,
        action="Admin Fetch Uploaded Documents",
        endpoint="/api/admin/documents",
        status="success",
        processing_time=duration
    )
    return docs

@app.post("/api/admin/users/{user_id}/role", response_model=dict)
async def admin_update_user_role(request: Request, user_id: int, role_req: UpdateRoleRequest, current_user: dict = Depends(require_admin)):
    """
    Update a user's role. Admin role required.
    """
    start_time = time.time()
    ip = request.client.host if request.client else "unknown"
    
    new_role = role_req.role.strip()
    success = DBManager.update_user_role(user_id, new_role)
    duration = time.time() - start_time
    
    DBManager.log_audit_event(
        username=current_user["username"],
        role=current_user["role"],
        ip_address=ip,
        action=f"Admin Update User {user_id} Role to {new_role}",
        endpoint=f"/api/admin/users/{user_id}/role",
        status="success" if success else "failed",
        processing_time=duration
    )
    
    if success:
        return {"success": True, "message": f"User role updated to {new_role} successfully."}
    raise HTTPException(status_code=400, detail="Failed to update user role.")

@app.post("/api/admin/users/{user_id}/delete", response_model=dict)
async def admin_delete_user(request: Request, user_id: int, current_user: dict = Depends(require_admin)):
    """
    Delete a user. Admin role required.
    """
    start_time = time.time()
    ip = request.client.host if request.client else "unknown"
    
    success = DBManager.delete_user(user_id)
    duration = time.time() - start_time
    
    DBManager.log_audit_event(
        username=current_user["username"],
        role=current_user["role"],
        ip_address=ip,
        action=f"Admin Delete User {user_id}",
        endpoint=f"/api/admin/users/{user_id}/delete",
        status="success" if success else "failed",
        processing_time=duration
    )
    
    if success:
        return {"success": True, "message": f"User deleted successfully."}
    raise HTTPException(status_code=400, detail="Failed to delete user.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
