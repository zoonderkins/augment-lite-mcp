"""
Semantic cache using vector similarity.

Features:
- Cache similar queries instead of exact matches
- Uses sentence-transformers for query embeddings
- FAISS for fast similarity search
- Configurable similarity threshold
- Multi-project support
"""

import os
import json
import time
import pickle
import logging
from pathlib import Path
from typing import Any, Optional, Dict, List

import numpy as np

logger = logging.getLogger(__name__)

# Lazy imports
_faiss = None
_SentenceTransformer = None

def _lazy_imports():
    """Lazy import heavy dependencies."""
    global _faiss, _SentenceTransformer
    
    if _faiss is None:
        try:
            import faiss
            _faiss = faiss
        except ImportError:
            logger.warning("faiss-cpu not installed. Semantic cache disabled.")
            return None, None
    
    if _SentenceTransformer is None:
        try:
            from sentence_transformers import SentenceTransformer
            _SentenceTransformer = SentenceTransformer
        except ImportError:
            logger.warning("sentence-transformers not installed. Semantic cache disabled.")
            return None, None
    
    return _faiss, _SentenceTransformer

BASE = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("AUGMENT_DB_DIR", BASE / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Default embedding model (same as vector search)
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # 384 dimensions

class SemanticCache:
    """
    Semantic cache using vector similarity.
    
    Features:
    - Cache similar queries (not just exact matches)
    - Configurable similarity threshold
    - Automatic expiration
    - Multi-project support
    """
    
    def __init__(
        self,
        project: str = None,
        model_name: str = DEFAULT_MODEL,
        dimension: int = 384,
        similarity_threshold: float = 0.95
    ):
        """
        Initialize semantic cache.
        
        Args:
            project: Project name (None for global)
            model_name: Sentence-transformers model name
            dimension: Embedding dimension
            similarity_threshold: Minimum similarity score (0-1) to consider a cache hit
        """
        self.project = project or ""
        self.model_name = model_name
        self.dimension = dimension
        self.similarity_threshold = similarity_threshold
        
        # Lazy load dependencies
        faiss, SentenceTransformer = _lazy_imports()
        if faiss is None or SentenceTransformer is None:
            self.enabled = False
            logger.warning("Semantic cache disabled (missing dependencies)")
            return
        
        self.enabled = True
        
        # Load embedding model
        logger.info(f"Loading semantic cache model: {model_name}")
        self.model = SentenceTransformer(model_name)
        
        # Initialize FAISS index
        self.index = None
        self.cache_entries = []  # List of (query, value, expire_at)
        
        # Load existing cache
        self._load_cache()
    
    def _get_cache_path(self) -> Path:
        """Get path to cache index file."""
        if self.project:
            return DATA_DIR / f"semantic_cache_{self.project}.faiss"
        return DATA_DIR / "semantic_cache.faiss"
    
    def _get_entries_path(self) -> Path:
        """Get path to cache entries file."""
        if self.project:
            return DATA_DIR / f"semantic_cache_entries_{self.project}.pkl"
        return DATA_DIR / "semantic_cache_entries.pkl"
    
    def _load_cache(self):
        """Load existing cache."""
        if not self.enabled:
            return
        
        cache_path = self._get_cache_path()
        entries_path = self._get_entries_path()
        
        if cache_path.exists() and entries_path.exists():
            try:
                faiss, _ = _lazy_imports()
                self.index = faiss.read_index(str(cache_path))
                with open(entries_path, "rb") as f:
                    self.cache_entries = pickle.load(f)
                
                # Remove expired entries
                self._cleanup_expired()
                
                logger.info(
                    f"Loaded semantic cache: {len(self.cache_entries)} entries "
                    f"(project: {self.project or 'global'})"
                )
            except Exception as e:
                logger.warning(f"Failed to load semantic cache: {e}")
                self.index = None
                self.cache_entries = []
    
    def _save_cache(self):
        """Save cache to disk."""
        if not self.enabled or self.index is None:
            return
        
        cache_path = self._get_cache_path()
        entries_path = self._get_entries_path()
        
        try:
            faiss, _ = _lazy_imports()
            faiss.write_index(self.index, str(cache_path))
            with open(entries_path, "wb") as f:
                pickle.dump(self.cache_entries, f)
            logger.debug(
                f"Saved semantic cache: {len(self.cache_entries)} entries "
                f"(project: {self.project or 'global'})"
            )
        except Exception as e:
            logger.error(f"Failed to save semantic cache: {e}")
    
    def _cleanup_expired(self):
        """Remove expired cache entries."""
        if not self.enabled:
            return
        
        now = int(time.time())
        valid_indices = []
        valid_entries = []
        
        for i, (query, value, expire_at) in enumerate(self.cache_entries):
            if expire_at >= now:
                valid_indices.append(i)
                valid_entries.append((query, value, expire_at))
        
        if len(valid_entries) < len(self.cache_entries):
            # Rebuild index with valid entries only
            if valid_entries:
                queries = [entry[0] for entry in valid_entries]
                embeddings = self.model.encode(
                    queries,
                    convert_to_numpy=True,
                    normalize_embeddings=True
                )
                
                faiss, _ = _lazy_imports()
                self.index = faiss.IndexFlatIP(self.dimension)
                self.index.add(embeddings.astype(np.float32))
            else:
                self.index = None
            
            self.cache_entries = valid_entries
            self._save_cache()
            
            logger.info(
                f"Cleaned up semantic cache: {len(self.cache_entries)} valid entries "
                f"(removed {len(self.cache_entries) - len(valid_entries)} expired)"
            )
    
    def get(self, query: str) -> Optional[Any]:
        """
        Get cached value for a similar query.
        
        Args:
            query: Query text
        
        Returns:
            Cached value if found, None otherwise
        """
        if not self.enabled or self.index is None or len(self.cache_entries) == 0:
            return None
        
        # Generate query embedding
        query_embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        
        # Search for similar queries
        scores, indices = self.index.search(query_embedding.astype(np.float32), 1)
        
        if len(scores[0]) == 0:
            return None
        
        score = scores[0][0]
        idx = indices[0][0]
        
        # Check similarity threshold
        if score < self.similarity_threshold:
            logger.debug(
                f"Semantic cache miss: similarity {score:.3f} < threshold {self.similarity_threshold}"
            )
            return None
        
        # Check expiration
        cached_query, value, expire_at = self.cache_entries[idx]
        now = int(time.time())
        
        if expire_at < now:
            logger.debug("Semantic cache hit but expired")
            return None
        
        logger.info(
            f"Semantic cache hit: similarity {score:.3f} "
            f"(query: '{query[:50]}...' → cached: '{cached_query[:50]}...')"
        )
        
        return value
    
    def set(self, query: str, value: Any, ttl_sec: int = 3600):
        """
        Cache a value for a query.
        
        Args:
            query: Query text
            value: Value to cache
            ttl_sec: Time to live in seconds
        """
        if not self.enabled:
            return
        
        expire_at = int(time.time()) + ttl_sec
        
        # Generate query embedding
        query_embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        
        # Add to index
        faiss, _ = _lazy_imports()
        if self.index is None:
            self.index = faiss.IndexFlatIP(self.dimension)
        
        self.index.add(query_embedding.astype(np.float32))
        self.cache_entries.append((query, value, expire_at))
        
        # Save cache
        self._save_cache()
        
        logger.debug(f"Semantic cache set: '{query[:50]}...' (ttl: {ttl_sec}s)")
    
    def clear(self):
        """Clear all cache entries."""
        if not self.enabled:
            return
        
        self.index = None
        self.cache_entries = []
        
        # Delete cache files
        cache_path = self._get_cache_path()
        entries_path = self._get_entries_path()
        
        if cache_path.exists():
            cache_path.unlink()
        if entries_path.exists():
            entries_path.unlink()
        
        logger.info("Semantic cache cleared")

def get_semantic_cache(project: str = "auto", **kwargs) -> SemanticCache:
    """
    Get semantic cache for a project.
    
    Args:
        project: Project name ("auto" for active project, None for global)
        **kwargs: Additional arguments for SemanticCache
    
    Returns:
        SemanticCache instance
    """
    if project == "auto":
        project = _get_active_project()
    
    return SemanticCache(project=project, **kwargs)

def _get_active_project() -> Optional[str]:
    """Get the active project name from projects.json"""
    projects_config = DATA_DIR / "projects.json"
    
    if projects_config.exists():
        try:
            with open(projects_config, "r", encoding="utf-8") as f:
                projects = json.load(f)
                for name, config in projects.items():
                    if config.get("active", False):
                        return name
        except Exception:
            pass
    
    return None

