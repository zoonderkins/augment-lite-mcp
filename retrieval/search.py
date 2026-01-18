# --- add at top ---
import os
from pathlib import Path
BASE = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("AUGMENT_DB_DIR", BASE / "data"))
# -------------------
import json, hashlib, re, sys, logging
from pathlib import Path
from typing import List, Dict, Optional

sys.path.insert(0, str(BASE))

from utils.project_utils import resolve_auto_project

try:
    from rank_bm25 import BM25Okapi
except Exception:
    BM25Okapi = None

# Lazy import vector search
_VectorSearchEngine = None

def _lazy_vector_search():
    """Lazy import vector search to avoid startup overhead."""
    global _VectorSearchEngine
    if _VectorSearchEngine is None:
        try:
            from retrieval.vector_search import VectorSearchEngine
            _VectorSearchEngine = VectorSearchEngine
        except ImportError:
            logging.warning("Vector search not available. Install: uv pip install faiss-cpu sentence-transformers")
            _VectorSearchEngine = False
    return _VectorSearchEngine if _VectorSearchEngine is not False else None

logger = logging.getLogger(__name__)

def _get_active_chunks_path():
    """Get the active project's chunks path, or fallback to default."""
    projects_config = DATA_DIR / "projects.json"

    # Try to load active project
    if projects_config.exists():
        try:
            with open(projects_config, "r", encoding="utf-8") as f:
                projects = json.load(f)
                for name, config in projects.items():
                    if config.get("active", False):
                        chunks_path = DATA_DIR / f"chunks_{name}.jsonl"
                        if chunks_path.exists():
                            return chunks_path
        except Exception:
            pass

    # Fallback to default path
    return DATA_DIR / "chunks.jsonl"


def _load_chunks(path=None):
    if path is None:
        path = _get_active_chunks_path()
    chunks = []
    p = Path(path)
    if not p.exists():
        return chunks
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                chunks.append(json.loads(line))
            except Exception:
                continue
    return chunks

def _tokenize(s: str):
    return re.findall(r"[\w#@/\.\-]+", s.lower())


def bm25_search(query: str, k: int = 8) -> List[Dict]:
    """
    BM25-based keyword search.

    Args:
        query: Query text
        k: Number of results to return

    Returns:
        List of dicts with 'text', 'source', and 'score' fields
    """
    chunks = _load_chunks()
    if not chunks:
        return []

    docs = [_tokenize(c["text"]) for c in chunks]
    query_toks = _tokenize(query)

    if BM25Okapi is None:
        scores = [sum(1 for t in query_toks if t in d) for d in docs]
    else:
        bm25 = BM25Okapi(docs)
        scores = bm25.get_scores(query_toks).tolist()

    pairs = list(zip(range(len(chunks)), scores))
    pairs.sort(key=lambda x: x[1], reverse=True)

    out = []
    for idx, sc in pairs[:max(1, k * 3)]:
        rec = chunks[idx]
        out.append({
            "text": rec.get("text", ""),
            "source": rec.get("path", "unknown"),
            "score": float(sc)
        })

    # Deduplicate by path
    by_path = {}
    for h in out:
        key = h["source"]
        if key not in by_path or h["score"] > by_path[key]["score"]:
            by_path[key] = h

    return sorted(by_path.values(), key=lambda x: x["score"], reverse=True)[:k]

def vector_search(query: str, k: int = 8, project: str = "auto") -> List[Dict]:
    """
    Vector-based semantic search.

    Args:
        query: Query text
        k: Number of results to return
        project: Project name ("auto" for active project, None for global)

    Returns:
        List of dicts with 'text', 'source', and 'score' fields
    """
    VectorSearchEngine = _lazy_vector_search()
    if VectorSearchEngine is None:
        logger.warning("Vector search not available. Falling back to BM25.")
        return []

    if project == "auto":
        project = resolve_auto_project()

    try:
        engine = VectorSearchEngine(project=project)
        results = engine.search(query, k=k)
        return results
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        return []

def hybrid_search(
    query: str,
    k: int = 8,
    bm25_weight: float = 0.5,
    vector_weight: float = 0.5,
    use_vector: bool = True,
    project: str = "auto"
) -> List[Dict]:
    """
    Hybrid search combining BM25 and vector search.

    Args:
        query: Query text
        k: Number of results to return
        bm25_weight: Weight for BM25 scores (0-1)
        vector_weight: Weight for vector scores (0-1)
        use_vector: Whether to use vector search (fallback to BM25 only if False)
        project: Project name ("auto" for active project, None for global)

    Returns:
        List of dicts with 'text', 'source', and 'score' fields
    """
    # Get BM25 results (k×3 for larger candidate pool before rerank)
    bm25_results = bm25_search(query, k=k * 3)

    # Get vector results if available (k×3 for larger candidate pool)
    vector_results = []
    if use_vector:
        VectorSearchEngine = _lazy_vector_search()
        if VectorSearchEngine is not None:
            vector_results = vector_search(query, k=k * 3, project=project)

    # If no vector results, return BM25 only
    if not vector_results:
        return bm25_results[:k]

    # Normalize scores to 0-1 range
    def normalize_scores(results: List[Dict]) -> List[Dict]:
        if not results:
            return []
        max_score = max(r["score"] for r in results)
        if max_score == 0:
            return results
        return [
            {**r, "score": r["score"] / max_score}
            for r in results
        ]

    bm25_results = normalize_scores(bm25_results)
    vector_results = normalize_scores(vector_results)

    # Combine results
    combined = {}

    # Add BM25 results
    for r in bm25_results:
        key = r["source"]
        combined[key] = {
            "text": r["text"],
            "source": r["source"],
            "bm25_score": r["score"] * bm25_weight,
            "vector_score": 0.0
        }

    # Add vector results
    for r in vector_results:
        key = r["source"]
        if key in combined:
            combined[key]["vector_score"] = r["score"] * vector_weight
        else:
            combined[key] = {
                "text": r["text"],
                "source": r["source"],
                "bm25_score": 0.0,
                "vector_score": r["score"] * vector_weight
            }

    # Calculate final scores
    results = []
    for key, data in combined.items():
        final_score = data["bm25_score"] + data["vector_score"]
        results.append({
            "text": data["text"],
            "source": data["source"],
            "score": final_score
        })

    # Sort by final score
    results.sort(key=lambda x: x["score"], reverse=True)

    # Same-file deduplication: keep top N chunks per file (avoid all results from one file)
    # Source format: "path/to/file.py:123" or "path/to/file.md:chunk5"
    per_file_limit = 2  # Keep up to 2 chunks per file for better recall
    file_counts = {}
    deduped_results = []

    for r in results:
        source = r["source"]
        # Safe extraction: match ":line_number" or ":chunkN" at end
        # Handles Windows paths (C:\...), URLs, repo:branch formats safely
        if re.search(r":(?:chunk)?\d+$", source):
            file_key = source.rsplit(":", 1)[0]
        else:
            file_key = source

        file_counts[file_key] = file_counts.get(file_key, 0) + 1
        if file_counts[file_key] <= per_file_limit:
            deduped_results.append(r)

    return deduped_results[:k]

def evidence_fingerprints_for_hits(hits: List[Dict]):
    fps = []
    for h in hits:
        s = (h.get("source","") + "|" + h.get("text","")).encode("utf-8")
        fps.append(hashlib.sha1(s).hexdigest())
    return fps