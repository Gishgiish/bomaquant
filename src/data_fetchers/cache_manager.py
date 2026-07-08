# src/data_fetchers/cache_manager.py
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)

class CacheManager:
    """Simple file-based cache with TTL (Time-To-Live)"""
    
    def __init__(self, cache_dir: str = ".cache/nse", ttl_seconds: int = 300):
        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = ttl_seconds
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _generate_key(self, endpoint: str, params: Dict) -> str:
        """Generate unique cache key from endpoint + params"""
        key_string = f"{endpoint}:{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get(self, endpoint: str, params: Dict) -> Optional[Any]:
        """Retrieve cached data if not expired"""
        key = self._generate_key(endpoint, params)
        cache_file = self.cache_dir / f"{key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r') as f:
                cached = json.load(f)
            
            # Check TTL
            cached_time = datetime.fromisoformat(cached['timestamp'])
            if datetime.now() - cached_time > timedelta(seconds=self.ttl_seconds):
                cache_file.unlink()  # Delete expired
                return None
            
            logger.debug(f"Cache HIT: {endpoint} | {params}")
            return cached['data']
        
        except (json.JSONDecodeError, KeyError, OSError) as e:
            logger.warning(f"Cache read error: {e}")
            return None
    
    def set(self, endpoint: str, params: Dict, data: Any) -> bool:
        """Store data in cache with timestamp"""
        try:
            key = self._generate_key(endpoint, params)
            cache_file = self.cache_dir / f"{key}.json"
            
            payload = {
                'timestamp': datetime.now().isoformat(),
                'data': data
            }
            
            with open(cache_file, 'w') as f:
                json.dump(payload, f)
            
            logger.debug(f"Cache SET: {endpoint} | {params}")
            return True
        
        except (OSError, TypeError) as e:
            logger.error(f"Cache write error: {e}")
            return False
    
    def clear(self):
        """Clear all cached files (useful for tests)"""
        for file in self.cache_dir.glob("*.json"):
            file.unlink()