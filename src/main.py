#!/usr/bin/env python
"""
Indian Legal Advisor - Main Entry Point
Runs FastAPI backend for legal analysis
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

if __name__ == "__main__":
    import uvicorn
    from src.api.routes import app
    
    print("\n" + "="*80)
    print("INDIAN LEGAL ADVISOR - FastAPI Backend")
    print("="*80)
    print("\nStarting server...")
    print("API Documentation: http://localhost:8000/docs")
    print("Health Check: http://localhost:8000/health")
    print("="*80 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)