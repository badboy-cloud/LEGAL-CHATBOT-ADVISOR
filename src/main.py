#!/usr/bin/env python
"""
Indian Legal Advisor - Main Entry Point
Runs FastAPI backend for legal analysis with HTTPS support.
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    import uvicorn
    from src.api.routes import app
    
    print("\n" + "="*80)
    print("INDIAN LEGAL ADVISOR - FastAPI Backend (Secure Edition)")
    print("="*80)
    print("\nStarting server...")
    
    # Read SSL environment variables
    ssl_enabled = os.getenv("SSL_ENABLED", "False").lower() in ("true", "1", "yes")
    ssl_keyfile = os.getenv("SSL_KEYFILE", "")
    ssl_certfile = os.getenv("SSL_CERTFILE", "")
    
    uvicorn_kwargs = {
        "app": app,
        "host": "0.0.0.0",
        "port": 8000,
        "reload": False
    }
    
    if ssl_enabled and ssl_keyfile and ssl_certfile:
        if os.path.exists(ssl_keyfile) and os.path.exists(ssl_certfile):
            print("[SSL] Configuring HTTPS...")
            print(f"[SSL] Keyfile: {ssl_keyfile}")
            print(f"[SSL] Certfile: {ssl_certfile}")
            uvicorn_kwargs["ssl_keyfile"] = ssl_keyfile
            uvicorn_kwargs["ssl_certfile"] = ssl_certfile
            print("API Documentation: https://localhost:8000/docs")
            print("Health Check: https://localhost:8000/health")
        else:
            print("[SSL_WARNING] SSL keyfile or certfile path not found. Falling back to HTTP...")
            print("API Documentation: http://localhost:8000/docs")
            print("Health Check: http://localhost:8000/health")
    else:
        print("[SSL] SSL disabled or not configured. Running over HTTP.")
        print("API Documentation: http://localhost:8000/docs")
        print("Health Check: http://localhost:8000/health")
        
    print("="*80 + "\n")
    
    uvicorn.run(**uvicorn_kwargs)