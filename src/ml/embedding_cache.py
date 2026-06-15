"""
Embedding Cache - LRU Cache for Query Embeddings
Avoids recalculating embeddings for repeated or similar queries.

Performance benefit: If same query appears twice, saves embedding generation time.
"""

from collections import OrderedDict
import hashlib
import numpy as np
import time

class EmbeddingCache:
    """
    LRU (Least Recently Used) cache for embeddings.
    Stores up to N embeddings, evicting oldest when full.
    """
    
    def __init__(self, max_size=100):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
        self.start_time = time.time()
    
    def _hash_text(self, text: str) -> str:
        """Generate hash key for text."""
        return hashlib.md5(text.strip().lower().encode()).hexdigest()
    
    def get(self, text: str):
        """Get embedding from cache if exists."""
        key = self._hash_text(text)
        
        if key in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            self.hits += 1
            return self.cache[key]
        
        self.misses += 1
        return None
    
    def put(self, text: str, embedding: np.ndarray):
        """Store embedding in cache."""
        key = self._hash_text(text)
        
        # If key exists, move to end
        if key in self.cache:
            self.cache.move_to_end(key)
        else:
            # If cache full, remove oldest (first) item
            if len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)
        
        self.cache[key] = embedding
    
    def clear(self):
        """Clear cache."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
    
    def get_stats(self):
        """Get cache statistics."""
        uptime = time.time() - self.start_time
        hit_rate = self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 2),
            "uptime_seconds": round(uptime, 1)
        }

# Global embedding cache
_embedding_cache = EmbeddingCache(max_size=100)

def get_embedding_cache():
    """Get global embedding cache instance."""
    return _embedding_cache

print("[EMBEDDING_CACHE] ✓ Embedding cache initialized (max 100 entries)")
