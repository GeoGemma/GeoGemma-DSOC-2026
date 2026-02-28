"""
Cache module for the GIS AI Agent.

This module provides caching functionality to improve performance by storing
and retrieving frequently used data.
"""

import os
import json
import time
import logging
import hashlib
import threading
from typing import Dict, Any, Optional, Callable, Tuple
from pathlib import Path
import functools

# Configure logging
logger = logging.getLogger(__name__)

class Cache:
    """A thread-safe cache implementation with TTL support."""

    def __init__(self, cache_dir: Optional[str] = None, default_ttl: int = 3600):
        """
        Initialize the cache.

        Args:
            cache_dir: Directory to store cache files. If not provided,
                      a default directory will be used.
            default_ttl: Default time-to-live for cache entries in seconds (1 hour default).
        """
        if cache_dir is None:
            # Use the default cache directory in the project
            self.cache_dir = Path(__file__).parent.parent.parent / "data" / "cache"
        else:
            self.cache_dir = Path(cache_dir)
        
        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache for faster access
        self.memory_cache: Dict[str, Tuple[Any, float]] = {}
        
        # Default time-to-live for cache entries (seconds)
        self.default_ttl = default_ttl
        
        # Lock for thread safety
        self.lock = threading.RLock()
        
        logger.info(f"Cache initialized with directory: {self.cache_dir}")

    def _generate_key(self, key_parts: Any) -> str:
        """
        Generate a cache key from the given parts.

        Args:
            key_parts: Parts to include in the key generation.

        Returns:
            A string key.
        """
        # Convert key_parts to a JSON string
        try:
            key_str = json.dumps(key_parts, sort_keys=True)
        except (TypeError, ValueError):
            # If key_parts cannot be JSON serialized, use str representation
            key_str = str(key_parts)
        
        # Generate hash from the key string
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, key_parts: Any) -> Optional[Any]:
        """
        Get a value from the cache.

        Args:
            key_parts: Parts to include in the key generation.

        Returns:
            The cached value, or None if not found or expired.
        """
        key = self._generate_key(key_parts)
        
        with self.lock:
            # Try memory cache first
            if key in self.memory_cache:
                value, expiry = self.memory_cache[key]
                if expiry > time.time():
                    return value
                else:
                    # Remove expired entry
                    del self.memory_cache[key]
            
            # Check file cache
            cache_file = self.cache_dir / f"{key}.json"
            if cache_file.exists():
                try:
                    with open(cache_file, "r") as f:
                        cache_data = json.load(f)
                    
                    # Check if the entry has expired
                    if cache_data.get("expiry", 0) > time.time():
                        # Update memory cache
                        self.memory_cache[key] = (cache_data["value"], cache_data["expiry"])
                        return cache_data["value"]
                    else:
                        # Remove expired cache file
                        try:
                            os.remove(cache_file)
                        except OSError as e:
                            logger.warning(f"Failed to remove expired cache file {cache_file}: {e}")
                except (json.JSONDecodeError, KeyError, OSError) as e:
                    logger.warning(f"Failed to read cache file {cache_file}: {e}")
        
        # Not found or expired
        return None

    def set(self, key_parts: Any, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a value in the cache.

        Args:
            key_parts: Parts to include in the key generation.
            value: Value to cache.
            ttl: Time-to-live in seconds. If None, the default TTL is used.

        Returns:
            True if the value was successfully cached, False otherwise.
        """
        try:
            key = self._generate_key(key_parts)
            ttl = ttl if ttl is not None else self.default_ttl
            expiry = time.time() + ttl
            
            with self.lock:
                # Update memory cache
                self.memory_cache[key] = (value, expiry)
                
                # Prepare data for file cache
                cache_data = {
                    "value": value,
                    "expiry": expiry,
                    "created_at": time.time()
                }
                
                # Save to file
                cache_file = self.cache_dir / f"{key}.json"
                with open(cache_file, "w") as f:
                    json.dump(cache_data, f)
            
            return True
        except Exception as e:
            logger.error(f"Failed to set cache value: {e}")
            return False

    def delete(self, key_parts: Any) -> bool:
        """
        Delete a value from the cache.

        Args:
            key_parts: Parts to include in the key generation.

        Returns:
            True if the value was successfully deleted, False otherwise.
        """
        try:
            key = self._generate_key(key_parts)
            
            with self.lock:
                # Remove from memory cache
                if key in self.memory_cache:
                    del self.memory_cache[key]
                
                # Remove from file cache
                cache_file = self.cache_dir / f"{key}.json"
                if cache_file.exists():
                    os.remove(cache_file)
            
            return True
        except Exception as e:
            logger.error(f"Failed to delete cache value: {e}")
            return False

    def clear(self) -> bool:
        """
        Clear all cache entries.

        Returns:
            True if the cache was successfully cleared, False otherwise.
        """
        try:
            with self.lock:
                # Clear memory cache
                self.memory_cache.clear()
                
                # Clear file cache
                for cache_file in self.cache_dir.glob("*.json"):
                    try:
                        os.remove(cache_file)
                    except OSError as e:
                        logger.warning(f"Failed to remove cache file {cache_file}: {e}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False

    def clean_expired(self) -> int:
        """
        Remove all expired entries from the cache.

        Returns:
            Number of entries removed.
        """
        removed_count = 0
        current_time = time.time()
        
        try:
            with self.lock:
                # Clean memory cache
                keys_to_remove = [key for key, (_, expiry) in self.memory_cache.items() 
                                if expiry <= current_time]
                for key in keys_to_remove:
                    del self.memory_cache[key]
                removed_count += len(keys_to_remove)
                
                # Clean file cache
                for cache_file in self.cache_dir.glob("*.json"):
                    try:
                        with open(cache_file, "r") as f:
                            cache_data = json.load(f)
                        
                        if cache_data.get("expiry", 0) <= current_time:
                            os.remove(cache_file)
                            removed_count += 1
                    except (json.JSONDecodeError, KeyError, OSError) as e:
                        logger.warning(f"Failed to check/remove cache file {cache_file}: {e}")
                        try:
                            # Remove invalid cache file
                            os.remove(cache_file)
                            removed_count += 1
                        except OSError:
                            pass
        except Exception as e:
            logger.error(f"Error cleaning expired cache entries: {e}")
        
        return removed_count

    def cached(self, ttl: Optional[int] = None):
        """
        Decorator to cache function results.

        Args:
            ttl: Time-to-live in seconds. If None, the default TTL is used.

        Returns:
            Decorated function.
        """
        def decorator(func: Callable):
            def wrapper(*args, **kwargs):
                # Generate cache key from function name, args, and kwargs
                key_parts = {
                    "func": func.__name__,
                    "args": args,
                    "kwargs": kwargs
                }
                
                # Try to get from cache
                cached_result = self.get(key_parts)
                if cached_result is not None:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return cached_result
                
                # Execute function and cache result
                logger.debug(f"Cache miss for {func.__name__}")
                result = func(*args, **kwargs)
                self.set(key_parts, result, ttl)
                
                return result
            return wrapper
        return decorator


# Singleton instance
_cache = None

def get_cache(cache_dir: Optional[str] = None, default_ttl: int = 3600) -> Cache:
    """
    Get the cache instance.

    Args:
        cache_dir: Directory to store cache files. If not provided,
                 a default directory will be used.
        default_ttl: Default time-to-live for cache entries in seconds.

    Returns:
        The Cache instance.
    """
    global _cache
    
    if _cache is None:
        _cache = Cache(cache_dir, default_ttl)
    
    return _cache


def get_tool_result_cache(cache_dir: Optional[str] = None, default_ttl: int = 3600) -> Cache:
    """
    Get the cache instance specifically for tool results.
    This is a convenience alias for get_cache.

    Args:
        cache_dir: Directory to store cache files. If not provided,
                 a default directory will be used.
        default_ttl: Default time-to-live for cache entries in seconds.

    Returns:
        The Cache instance.
    """
    return get_cache(cache_dir, default_ttl)


def async_cached(ttl: Optional[int] = None):
    """
    Decorator for caching results of async functions.

    Args:
        ttl: Time-to-live in seconds. If None, the default TTL is used.

    Returns:
        Decorated async function.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_cache()
            
            # Generate cache key
            key_parts = {
                "func": func.__name__,
                "args": args,
                "kwargs": kwargs
            }
            
            # Try to get from cache
            cached_result = cache.get(key_parts)
            if cached_result is not None:
                logger.debug(f"Async cache hit for {func.__name__}")
                return cached_result
            
            # Execute function and cache result
            logger.debug(f"Async cache miss for {func.__name__}")
            result = await func(*args, **kwargs)
            cache.set(key_parts, result, ttl)
            
            return result
        return wrapper
    return decorator


def schedule_cache_maintenance(interval: int = 3600) -> None:
    """
    Schedule periodic cache maintenance to clean expired entries.

    Args:
        interval: Interval in seconds between maintenance runs (default: 1 hour).
    """
    def maintenance_task():
        try:
            cache = get_cache()
            removed = cache.clean_expired()
            logger.info(f"Cache maintenance completed: {removed} expired entries removed")
            
            # Schedule next run
            threading.Timer(interval, maintenance_task).start()
        except Exception as e:
            logger.error(f"Error in cache maintenance task: {e}")
            # Even if there's an error, try to schedule the next run
            threading.Timer(interval, maintenance_task).start()
    
    # Start the first run
    threading.Timer(interval, maintenance_task).start()
    logger.info(f"Cache maintenance scheduled with interval: {interval} seconds") 