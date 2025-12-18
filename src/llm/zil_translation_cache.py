"""Cache for ZIL code to natural language translations.

This cache stores translations of ZIL code snippets to avoid redundant LLM calls.
Translations are keyed by content hash and persisted to disk.
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from threading import Lock

logger = logging.getLogger(__name__)


class ZILTranslationCache:
    """Manages cached translations of ZIL code to natural language."""

    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize ZIL translation cache.

        Args:
            cache_dir: Directory to store cache files (default: .cache/zil_translations/)
        """
        if cache_dir is None:
            cache_dir = Path.cwd() / ".cache" / "zil_translations"

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.cache_file = self.cache_dir / "translations.json"
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()

        # Load existing cache
        self._load_cache()

    def _compute_hash(self, zil_code: str) -> str:
        """Compute hash of ZIL code for cache key.

        Args:
            zil_code: ZIL code string

        Returns:
            SHA256 hash of the code
        """
        return hashlib.sha256(zil_code.encode('utf-8')).hexdigest()

    def _load_cache(self):
        """Load cache from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    self._cache = json.load(f)
                logger.info(f"Loaded {len(self._cache)} ZIL translations from cache")
            except Exception as e:
                logger.warning(f"Failed to load ZIL translation cache: {e}")
                self._cache = {}
        else:
            self._cache = {}

    def _save_cache(self):
        """Save cache to disk."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self._cache, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save ZIL translation cache: {e}")

    def get(self, zil_code: str) -> Optional[str]:
        """Get cached translation for ZIL code.

        Args:
            zil_code: ZIL code to look up

        Returns:
            Natural language translation, or None if not cached
        """
        code_hash = self._compute_hash(zil_code)

        with self._lock:
            if code_hash in self._cache:
                entry = self._cache[code_hash]
                logger.debug(f"Cache HIT for ZIL routine: {entry.get('routine_name', 'unknown')}")
                return entry.get('translation')

        return None

    def put(
        self,
        zil_code: str,
        translation: str,
        routine_name: Optional[str] = None,
        context: Optional[str] = None
    ):
        """Store translation in cache.

        Args:
            zil_code: Original ZIL code
            translation: Natural language translation
            routine_name: Optional routine name for metadata
            context: Optional context description
        """
        code_hash = self._compute_hash(zil_code)

        entry = {
            'translation': translation,
            'routine_name': routine_name,
            'context': context,
            'cached_at': datetime.now().isoformat(),
            'zil_length': len(zil_code)
        }

        with self._lock:
            self._cache[code_hash] = entry
            self._save_cache()

        logger.info(f"Cached translation for: {routine_name or 'unknown routine'}")

    def has(self, zil_code: str) -> bool:
        """Check if translation exists in cache.

        Args:
            zil_code: ZIL code to check

        Returns:
            True if translation is cached
        """
        code_hash = self._compute_hash(zil_code)
        with self._lock:
            return code_hash in self._cache

    def clear(self):
        """Clear all cached translations."""
        with self._lock:
            self._cache = {}
            self._save_cache()
        logger.info("Cleared ZIL translation cache")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with cache size, file size, etc.
        """
        with self._lock:
            cache_size = len(self._cache)

        file_size = 0
        if self.cache_file.exists():
            file_size = self.cache_file.stat().st_size

        return {
            'entries': cache_size,
            'cache_file': str(self.cache_file),
            'file_size_bytes': file_size,
            'file_size_mb': round(file_size / (1024 * 1024), 2)
        }


# Global cache instance (lazy-initialized)
_global_cache: Optional[ZILTranslationCache] = None


def get_cache() -> ZILTranslationCache:
    """Get or create global ZIL translation cache instance.

    Returns:
        Global ZILTranslationCache instance
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = ZILTranslationCache()
    return _global_cache
