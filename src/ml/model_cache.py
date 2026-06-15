"""
Global Model Cache - Singleton Pattern for Performance Optimization
Ensures models are loaded ONCE and reused for all requests.

This is critical for:
1. InLegalBERT model (768-dim embeddings)
2. Tokenizers
3. FAISS index

Avoids redundant model loading which was a major bottleneck.
"""

import torch
import time
from transformers import AutoTokenizer, AutoModel
from src.config import DEVICE, MODEL_NAME

print(f"[MODEL_CACHE] Initializing global model cache on {DEVICE}")

# ============================================================================
# GLOBAL CACHE - These are loaded ONCE on app startup
# ============================================================================

_inlegalbert_model = None
_inlegalbert_tokenizer = None
_cache_lock = None
_load_times = {}

def load_inlegalbert_model():
    """
    Load InLegalBERT model globally (singleton).
    Called ONCE when routes.py is loaded.
    Reused for all subsequent requests.
    """
    global _inlegalbert_model, _inlegalbert_tokenizer, _load_times
    
    if _inlegalbert_model is not None:
        print("[MODEL_CACHE] ✓ InLegalBERT already cached - returning cached model")
        return _inlegalbert_model, _inlegalbert_tokenizer
    
    start = time.time()
    print(f"[MODEL_CACHE] Loading InLegalBERT model ({MODEL_NAME})...")
    
    try:
        _inlegalbert_tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        print(f"[MODEL_CACHE]   [OK] Tokenizer loaded ({time.time() - start:.1f}s)")
        
        model_start = time.time()
        _inlegalbert_model = AutoModel.from_pretrained(MODEL_NAME)
        _inlegalbert_model.to(DEVICE)
        
        # Enable eval mode + disable gradients for faster inference
        _inlegalbert_model.eval()
        
        model_load_time = time.time() - model_start
        total_time = time.time() - start
        
        print(f"[MODEL_CACHE]   [OK] Model loaded and moved to {DEVICE} ({model_load_time:.1f}s)")
        print(f"[MODEL_CACHE] [OK] InLegalBERT ready ({total_time:.1f}s total)")
        
        _load_times['inlegalbert'] = total_time
        
        return _inlegalbert_model, _inlegalbert_tokenizer
        
    except Exception as e:
        print(f"[MODEL_CACHE] [ERROR] Failed to load InLegalBERT: {e}")
        raise

def get_inlegalbert_model():
    """Get cached InLegalBERT model (or load if not cached)."""
    global _inlegalbert_model, _inlegalbert_tokenizer
    
    if _inlegalbert_model is None:
        _inlegalbert_model, _inlegalbert_tokenizer = load_inlegalbert_model()
    
    return _inlegalbert_model, _inlegalbert_tokenizer

def get_model_stats():
    """Return model loading statistics."""
    return {
        "model_loaded": _inlegalbert_model is not None,
        "device": DEVICE,
        "load_times_ms": {k: round(v * 1000, 2) for k, v in _load_times.items()}
    }

print("[MODEL_CACHE] [OK] Model cache system initialized")
