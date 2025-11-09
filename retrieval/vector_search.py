"""
Vector search using FAISS and sentence-transformers.

Features:
- Dense vector embeddings using sentence-transformers
- FAISS index for efficient similarity search
- Multi-project support
- Automatic index building and caching
"""

import os
import json
import pickle
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Lazy imports to avoid startup overhead
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
            logger.error("faiss-cpu not installed. Run: pip install faiss-cpu")
            raise
    
    if _SentenceTransformer is None:
        try:
            from sentence_transformers import SentenceTransformer
            _SentenceTransformer = SentenceTransformer
        except ImportError:
            logger.error("sentence-transformers not installed. Run: pip install sentence-transformers")
            raise
    
    return _faiss, _SentenceTransformer

BASE = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("AUGMENT_DB_DIR", BASE / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Default embedding model
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # 384 dimensions, fast

class VectorSearchEngine:
    """
    Vector search engine using FAISS.
    
    Features:
    - Automatic embedding generation
    - FAISS index for fast similarity search
    - Multi-project support
    - Index caching
    """
    
    def __init__(
        self,
        project: str = None,
        model_name: str = DEFAULT_MODEL,
        dimension: int = 384
    ):
        """
        Initialize vector search engine.
        
        Args:
            project: Project name (None for global)
            model_name: Sentence-transformers model name
            dimension: Embedding dimension
        """
        self.project = project or ""
        self.model_name = model_name
        self.dimension = dimension
        
        # Lazy load dependencies
        faiss, SentenceTransformer = _lazy_imports()
        
        # Load embedding model
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        
        # Initialize FAISS index
        self.index = None
        self.chunks = []  # Store chunk metadata
        
        # Load existing index if available
        self._load_index()
    
    def _get_index_path(self) -> Path:
        """Get path to FAISS index file."""
        if self.project:
            return DATA_DIR / f"vector_index_{self.project}.faiss"
        return DATA_DIR / "vector_index.faiss"
    
    def _get_chunks_path(self) -> Path:
        """Get path to chunks metadata file."""
        if self.project:
            return DATA_DIR / f"vector_chunks_{self.project}.pkl"
        return DATA_DIR / "vector_chunks.pkl"
    
    def _load_index(self):
        """Load existing FAISS index and chunks."""
        index_path = self._get_index_path()
        chunks_path = self._get_chunks_path()
        
        if index_path.exists() and chunks_path.exists():
            try:
                faiss, _ = _lazy_imports()
                self.index = faiss.read_index(str(index_path))
                with open(chunks_path, "rb") as f:
                    self.chunks = pickle.load(f)
                logger.info(
                    f"Loaded vector index: {len(self.chunks)} chunks "
                    f"(project: {self.project or 'global'})"
                )
            except Exception as e:
                logger.warning(f"Failed to load vector index: {e}")
                self.index = None
                self.chunks = []
    
    def _save_index(self):
        """Save FAISS index and chunks."""
        if self.index is None:
            return
        
        index_path = self._get_index_path()
        chunks_path = self._get_chunks_path()
        
        try:
            faiss, _ = _lazy_imports()
            faiss.write_index(self.index, str(index_path))
            with open(chunks_path, "wb") as f:
                pickle.dump(self.chunks, f)
            logger.info(
                f"Saved vector index: {len(self.chunks)} chunks "
                f"(project: {self.project or 'global'})"
            )
        except Exception as e:
            logger.error(f"Failed to save vector index: {e}")
    
    def build_index(self, chunks: List[Dict[str, Any]]):
        """
        Build FAISS index from chunks.
        
        Args:
            chunks: List of chunk dicts with 'text' and 'source' fields
        """
        if not chunks:
            logger.warning("No chunks to index")
            return
        
        logger.info(f"Building vector index for {len(chunks)} chunks...")
        
        # Extract texts
        texts = [chunk["text"] for chunk in chunks]
        
        # Generate embeddings
        logger.info("Generating embeddings...")
        embeddings = self.model.encode(
            texts,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True  # L2 normalization for cosine similarity
        )
        
        # Create FAISS index
        faiss, _ = _lazy_imports()
        
        # Use IndexFlatIP for cosine similarity (with normalized vectors)
        self.index = faiss.IndexFlatIP(self.dimension)
        self.index.add(embeddings.astype(np.float32))
        
        # Store chunks
        self.chunks = chunks
        
        # Save index
        self._save_index()
        
        logger.info(f"Vector index built: {len(chunks)} chunks")
    
    def search(
        self,
        query: str,
        k: int = 10,
        score_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks using vector similarity.
        
        Args:
            query: Query text
            k: Number of results to return
            score_threshold: Minimum similarity score (0-1)
        
        Returns:
            List of dicts with 'text', 'source', and 'score' fields
        """
        if self.index is None or len(self.chunks) == 0:
            logger.warning("Vector index not built. Call build_index() first.")
            return []
        
        # Generate query embedding
        query_embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        
        # Search FAISS index
        k = min(k, len(self.chunks))
        scores, indices = self.index.search(query_embedding.astype(np.float32), k)
        
        # Format results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if score >= score_threshold:
                chunk = self.chunks[idx]
                # Ensure consistent field names with BM25 search
                result = {
                    "text": chunk.get("text", ""),
                    "source": chunk.get("path", chunk.get("source", "")),  # Support both 'path' and 'source'
                    "score": float(score)
                }
                results.append(result)

        return results
    
    def add_chunks(self, new_chunks: List[Dict[str, Any]]):
        """
        Add new chunks to existing index.
        
        Args:
            new_chunks: List of chunk dicts with 'text' and 'source' fields
        """
        if not new_chunks:
            return
        
        # Extract texts
        texts = [chunk["text"] for chunk in new_chunks]
        
        # Generate embeddings
        embeddings = self.model.encode(
            texts,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        
        # Add to index
        if self.index is None:
            faiss, _ = _lazy_imports()
            self.index = faiss.IndexFlatIP(self.dimension)
        
        self.index.add(embeddings.astype(np.float32))
        self.chunks.extend(new_chunks)
        
        # Save index
        self._save_index()
        
        logger.info(f"Added {len(new_chunks)} chunks to vector index")

def get_vector_search_engine(project: str = "auto") -> VectorSearchEngine:
    """
    Get vector search engine for a project.
    
    Args:
        project: Project name ("auto" for active project, None for global)
    
    Returns:
        VectorSearchEngine instance
    """
    if project == "auto":
        project = _get_active_project()
    
    return VectorSearchEngine(project=project)

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

