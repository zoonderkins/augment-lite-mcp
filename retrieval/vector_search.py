"""
Vector search using FAISS and OpenRouter API / sentence-transformers.

Features:
- API embeddings via OpenRouter (Qwen3-Embedding-4B) - recommended
- Fallback to local sentence-transformers
- FAISS index for efficient similarity search
- Multi-project support
- Automatic index building and caching
"""

import os
import sys
import json
import pickle
import logging
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np

logger = logging.getLogger(__name__)

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
DATA_DIR = Path(os.getenv("AUGMENT_DB_DIR", BASE / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

from utils.project_utils import resolve_auto_project

# Lazy imports to avoid startup overhead
_faiss = None
_SentenceTransformer = None
_openai_client = None
_embedding_config = None

def _load_embedding_config() -> Dict:
    """Load embedding configuration from models.yaml."""
    global _embedding_config
    if _embedding_config is not None:
        return _embedding_config

    config_path = BASE / "config" / "models.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            _embedding_config = config.get("embedding", {})
    else:
        _embedding_config = {}

    return _embedding_config

def _get_openai_client():
    """Get OpenAI client for API embeddings."""
    global _openai_client
    if _openai_client is not None:
        return _openai_client

    try:
        from openai import OpenAI
        config = _load_embedding_config()
        api_key_env = config.get("api_key_env", "OPENROUTER_API_KEY")
        api_key = os.getenv(api_key_env)

        if not api_key:
            logger.warning(f"API key not found: {api_key_env}. Falling back to local model.")
            return None

        base_url = config.get("base_url", "https://openrouter.ai/api/v1")
        _openai_client = OpenAI(api_key=api_key, base_url=base_url)
        return _openai_client
    except ImportError:
        logger.warning("openai package not installed. Run: uv pip install openai")
        return None

def _lazy_faiss():
    """Lazy import FAISS."""
    global _faiss
    if _faiss is None:
        try:
            import faiss
            _faiss = faiss
        except ImportError:
            logger.error("faiss-cpu not installed. Run: uv pip install faiss-cpu")
            raise
    return _faiss

def _lazy_sentence_transformer():
    """Lazy import sentence-transformers."""
    global _SentenceTransformer
    if _SentenceTransformer is None:
        try:
            from sentence_transformers import SentenceTransformer
            _SentenceTransformer = SentenceTransformer
        except ImportError:
            logger.error("sentence-transformers not installed. Run: uv pip install sentence-transformers")
            raise
    return _SentenceTransformer

# Default embedding model (fallback)
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # 384 dimensions, fast


class EmbeddingProvider:
    """Unified embedding provider supporting API and local models."""

    def __init__(self, use_api: bool = True):
        """
        Initialize embedding provider.

        Args:
            use_api: Whether to use API (True) or local model (False)
        """
        self.config = _load_embedding_config()
        self.use_api = use_api and bool(self.config.get("provider"))
        self._local_model = None

        if self.use_api:
            self.client = _get_openai_client()
            if self.client is None:
                logger.info("API client unavailable, falling back to local model")
                self.use_api = False

        if not self.use_api:
            self._init_local_model()

    def _init_local_model(self):
        """Initialize local sentence-transformer model."""
        SentenceTransformer = _lazy_sentence_transformer()
        fallback_model = self.config.get("fallback_local", DEFAULT_MODEL)
        logger.info(f"Loading local embedding model: {fallback_model}")
        self._local_model = SentenceTransformer(fallback_model)

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        if self.use_api:
            return self.config.get("dimension", 1024)
        return self.config.get("fallback_dimension", 384)

    def encode(
        self,
        texts: List[str],
        show_progress_bar: bool = False,
        normalize: bool = True
    ) -> np.ndarray:
        """
        Generate embeddings for texts.

        Args:
            texts: List of texts to embed
            show_progress_bar: Show progress (only for local model)
            normalize: L2 normalize embeddings

        Returns:
            numpy array of embeddings (N x dimension)
        """
        if not texts:
            return np.array([])

        if self.use_api:
            return self._encode_api(texts, normalize)
        else:
            return self._encode_local(texts, show_progress_bar, normalize)

    def _encode_api(self, texts: List[str], normalize: bool = True) -> np.ndarray:
        """Encode using OpenRouter API."""
        config = self.config
        model_id = config.get("model_id", "qwen/qwen3-embedding-4b")
        batch_size = config.get("batch_size", 10)

        all_embeddings = []

        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                response = self.client.embeddings.create(
                    model=model_id,
                    input=batch
                )
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)

                if len(texts) > batch_size:
                    logger.info(f"Embedded {min(i + batch_size, len(texts))}/{len(texts)} texts")

            except Exception as e:
                logger.error(f"API embedding failed: {e}")
                # Fallback to local for this batch
                if self._local_model is None:
                    self._init_local_model()
                local_emb = self._local_model.encode(
                    batch,
                    convert_to_numpy=True,
                    normalize_embeddings=normalize
                )
                all_embeddings.extend(local_emb.tolist())

        embeddings = np.array(all_embeddings, dtype=np.float32)

        # Ensure 2D shape: (N, D) - handle single vector (D,) case
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)
        elif embeddings.ndim != 2:
            raise ValueError(f"Unexpected embedding shape: {embeddings.shape}. Expected 1D or 2D array.")

        # Dimension assertion - guard against API returning unexpected dims
        expected_dim = self.config.get("dimension", 2560)
        actual_dim = embeddings.shape[1] if embeddings.size > 0 else 0
        if actual_dim > 0 and actual_dim != expected_dim:
            provider = self.config.get("provider", "unknown")
            model_id = self.config.get("model_id", "unknown")
            logger.warning(
                f"⚠️ Dimension mismatch! provider={provider} model={model_id} "
                f"expected={expected_dim} got={actual_dim}. "
                f"Update config/models.yaml embedding.dimension to {actual_dim}"
            )
        elif actual_dim > 0:
            logger.debug(f"Embedding dimension verified: {actual_dim}")

        if normalize:
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            norms[norms == 0] = 1
            embeddings = embeddings / norms

        return embeddings

    def _encode_local(
        self,
        texts: List[str],
        show_progress_bar: bool = False,
        normalize: bool = True
    ) -> np.ndarray:
        """Encode using local sentence-transformers."""
        return self._local_model.encode(
            texts,
            show_progress_bar=show_progress_bar,
            convert_to_numpy=True,
            normalize_embeddings=normalize
        )


class VectorSearchEngine:
    """
    Vector search engine using FAISS.

    Features:
    - API embeddings via OpenRouter (default) or local sentence-transformers
    - FAISS index for fast similarity search
    - Multi-project support
    - Index caching
    """

    def __init__(
        self,
        project: str = None,
        use_api: bool = True
    ):
        """
        Initialize vector search engine.

        Args:
            project: Project name (None for global)
            use_api: Use API embeddings (True) or local model (False)
        """
        self.project = project or ""

        # Initialize embedding provider
        self.embedding_provider = EmbeddingProvider(use_api=use_api)
        self.dimension = self.embedding_provider.dimension

        logger.info(f"Vector search initialized: {'API' if self.embedding_provider.use_api else 'local'} mode, dim={self.dimension}")
        
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
                faiss = _lazy_faiss()
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
            faiss = _lazy_faiss()
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

        # Extract texts (filter invalid chunks)
        valid_chunks = [c for c in chunks if c.get("text")]
        if len(valid_chunks) < len(chunks):
            logger.warning(f"Filtered {len(chunks) - len(valid_chunks)} invalid chunks")
        texts = [chunk["text"] for chunk in valid_chunks]
        
        # Generate embeddings
        logger.info("Generating embeddings...")
        embeddings = self.embedding_provider.encode(
            texts,
            show_progress_bar=True,
            normalize=True
        )

        # Fail-fast dimension check before FAISS index creation
        actual_dim = embeddings.shape[1] if len(embeddings.shape) > 1 else 0
        if actual_dim > 0 and actual_dim != self.dimension:
            raise ValueError(
                f"Embedding dimension mismatch: expected {self.dimension}, got {actual_dim}. "
                f"Fix: Update config/models.yaml embedding.dimension to {actual_dim}, "
                f"then run: ./scripts/manage.sh rebuild <project>"
            )

        # Create FAISS index
        faiss = _lazy_faiss()

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
        query_embedding = self.embedding_provider.encode(
            [query],
            normalize=True
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

        # Extract texts (filter invalid chunks)
        valid_chunks = [c for c in new_chunks if c.get("text")]
        if not valid_chunks:
            return
        texts = [chunk["text"] for chunk in valid_chunks]
        
        # Generate embeddings
        embeddings = self.embedding_provider.encode(
            texts,
            show_progress_bar=False,
            normalize=True
        )
        
        # Add to index
        if self.index is None:
            faiss = _lazy_faiss()
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
        project = resolve_auto_project()

    return VectorSearchEngine(project=project)

