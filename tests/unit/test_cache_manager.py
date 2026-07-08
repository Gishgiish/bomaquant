# tests/unit/test_cache_manager.py
import time

import pytest

from src.data_fetchers.cache_manager import CacheManager


@pytest.fixture
def cache(tmp_path):
    """Fixture: fresh cache in temp directory for each test"""
    return CacheManager(cache_dir=str(tmp_path), ttl_seconds=2)  # 2 sec TTL for fast tests

def test_cache_set_and_get(cache):
    """Test basic set/get functionality"""
    endpoint = "/prices"
    params = {"symbol": "SCOM"}
    data = {"price": 28.50, "volume": 1000000}
    
    cache.set(endpoint, params, data)
    result = cache.get(endpoint, params)
    
    assert result == data

def test_cache_expires(cache):
    """Test that cached data expires after TTL"""
    endpoint = "/prices"
    params = {"symbol": "EQTY"}
    data = {"price": 45.00}
    
    cache.set(endpoint, params, data)
    assert cache.get(endpoint, params) == data  # Should hit
    
    time.sleep(3)  # Wait for 2-second TTL to expire
    
    assert cache.get(endpoint, params) is None  # Should miss

def test_cache_key_uniqueness(cache):
    """Test that different params create different cache keys"""
    data1 = {"price": 10.0}
    data2 = {"price": 20.0}
    
    cache.set("/prices", {"symbol": "SCOM"}, data1)
    cache.set("/prices", {"symbol": "EQTY"}, data2)
    
    assert cache.get("/prices", {"symbol": "SCOM"}) == data1
    assert cache.get("/prices", {"symbol": "EQTY"}) == data2

def test_cache_clear(cache):
    """Test clearing all cache"""
    cache.set("/test", {"a": 1}, {"value": 100})
    cache.clear()
    
    # Cache dir should be empty
    assert len(list(cache.cache_dir.glob("*.json"))) == 0