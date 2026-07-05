import os
import json
import hashlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class LegalAdvisorCache:
    _cache_dir = os.path.join(os.getcwd(), '.cache')
    _in_memory_cache = {}

    @classmethod
    def initialize(cls):
        os.makedirs(cls._cache_dir, exist_ok=True)

    @classmethod
    def _get_key(cls, data_str: str) -> str:
        return hashlib.sha256(data_str.strip().encode('utf-8')).hexdigest()

    @classmethod
    def get(cls, category: str, query: str) -> Optional[dict]:
        try:
            cls.initialize()
            key = cls._get_key(f'{category}:{query}')
            if key in cls._in_memory_cache:
                logger.info(f'[CACHE] In-memory hit for category={category}')
                return cls._in_memory_cache[key]
            cache_file = os.path.join(cls._cache_dir, f'{key}.json')
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    encrypted_data = f.read()
                
                # Decrypt the cache file
                from src.utils.crypto_helper import decrypt_string
                try:
                    decrypted_str = decrypt_string(encrypted_data)
                    data = json.loads(decrypted_str)
                except Exception as dec_err:
                    # Fallback for plain json if we changed keys or during transition
                    logger.warning(f'[CACHE] Decryption failed, trying raw read: {dec_err}')
                    data = json.loads(encrypted_data)
                
                cls._in_memory_cache[key] = data
                logger.info(f'[CACHE] Disk hit for category={category}')
                return data
        except Exception as e:
            logger.warning(f'[CACHE] Error reading cache for category {category}: {e}')
        return None

    @classmethod
    def set(cls, category: str, query: str, response: dict):
        try:
            cls.initialize()
            key = cls._get_key(f'{category}:{query}')
            cls._in_memory_cache[key] = response
            cache_file = os.path.join(cls._cache_dir, f'{key}.json')
            
            # Encrypt the cache file
            from src.utils.crypto_helper import encrypt_string
            serialized = json.dumps(response, ensure_ascii=False, indent=2)
            encrypted_data = encrypt_string(serialized)
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(encrypted_data)
            logger.info(f'[CACHE] Saved to cache for category={category}')
        except Exception as e:
            logger.warning(f'[CACHE] Error writing cache for category {category}: {e}')
