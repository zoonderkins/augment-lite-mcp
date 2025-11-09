import sqlite3, time, hashlib, json, os, sys, logging
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

DB_PATH = Path(os.getenv("AUGMENT_DB_DIR", "./data")) / "response_cache.sqlite"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)

# Lazy import semantic cache
_SemanticCache = None

def _lazy_semantic_cache():
    """Lazy import semantic cache to avoid startup overhead."""
    global _SemanticCache
    if _SemanticCache is None:
        try:
            from semantic_cache import SemanticCache
            _SemanticCache = SemanticCache
        except ImportError:
            logger.warning("Semantic cache not available. Install: pip install faiss-cpu sentence-transformers")
            _SemanticCache = False
    return _SemanticCache if _SemanticCache is not False else None

def _get_active_project():
    """Get the active project name from projects.json"""
    projects_config = BASE / "data" / "projects.json"

    if projects_config.exists():
        try:
            with open(projects_config, "r", encoding="utf-8") as f:
                projects = json.load(f)
                for name, config in projects.items():
                    if config.get("active", False):
                        return name
        except Exception:
            pass

    return None  # No active project (global cache)

def _db():
    conn = sqlite3.connect(DB_PATH)
    # Updated schema: add project column
    conn.execute("""CREATE TABLE IF NOT EXISTS cache (
        project TEXT NOT NULL,
        k TEXT NOT NULL,
        v TEXT NOT NULL,
        expire_at INTEGER NOT NULL,
        PRIMARY KEY (project, k)
    )""")
    return conn

def make_key(model: str, messages: list, extra: dict, evidence_fingerprints: list, project: str = None):
    """
    Generate cache key.

    Args:
        model: Model name
        messages: Messages list
        extra: Extra parameters
        evidence_fingerprints: Evidence fingerprints
        project: Project name (None for global, "auto" for active project)

    Returns:
        Tuple of (project, key_hash)
    """
    if project == "auto":
        project = _get_active_project()

    # Use empty string for global cache
    project = project or ""

    payload = {
        "model": model,
        "messages": messages,
        "extra": extra,
        "evidence": evidence_fingerprints,
    }
    s = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    key_hash = hashlib.sha256(s.encode("utf-8")).hexdigest()

    return (project, key_hash)

def get(k: str | tuple, project: str = None):
    """
    Get cached value.

    Args:
        k: Cache key (str for backward compatibility, or tuple of (project, key))
        project: Project name (None for global, "auto" for active project)

    Returns:
        Cached value or None
    """
    # Handle backward compatibility
    if isinstance(k, tuple):
        project, key_hash = k
    else:
        # Old API: k is just the hash
        if project == "auto":
            project = _get_active_project()
        project = project or ""
        key_hash = k

    now = int(time.time())
    with _db() as conn:
        cur = conn.execute("SELECT v, expire_at FROM cache WHERE project=? AND k=?", (project, key_hash))
        row = cur.fetchone()
        if not row:
            return None
        v, expire_at = row
        if expire_at < now:
            conn.execute("DELETE FROM cache WHERE project=? AND k=?", (project, key_hash))
            return None
        return json.loads(v)

def set(k: str | tuple, v, ttl_sec: int = 3600, project: str = None):
    """
    Set cached value.

    Args:
        k: Cache key (str for backward compatibility, or tuple of (project, key))
        v: Value to cache
        ttl_sec: Time to live in seconds
        project: Project name (None for global, "auto" for active project)
    """
    # Handle backward compatibility
    if isinstance(k, tuple):
        project, key_hash = k
    else:
        # Old API: k is just the hash
        if project == "auto":
            project = _get_active_project()
        project = project or ""
        key_hash = k

    expire_at = int(time.time()) + ttl_sec
    with _db() as conn:
        conn.execute(
            "REPLACE INTO cache (project, k, v, expire_at) VALUES (?, ?, ?, ?)",
            (project, key_hash, json.dumps(v, ensure_ascii=False), expire_at)
        )

def clear(project: str = None):
    """
    Clear cache for a project.

    Args:
        project: Project name (None for global, "auto" for active project, "all" for all projects)
    """
    if project == "auto":
        project = _get_active_project()

    with _db() as conn:
        if project == "all":
            conn.execute("DELETE FROM cache")
            print("✅ Cleared all cache")
        else:
            project = project or ""
            conn.execute("DELETE FROM cache WHERE project=?", (project,))
            print(f"✅ Cleared cache for project: {project or 'global'}")

    # Also clear semantic cache
    SemanticCache = _lazy_semantic_cache()
    if SemanticCache is not None:
        try:
            if project == "all":
                # Clear all semantic caches (would need to iterate projects)
                cache = SemanticCache(project=None)
                cache.clear()
            else:
                cache = SemanticCache(project=project)
                cache.clear()
        except Exception as e:
            logger.warning(f"Failed to clear semantic cache: {e}")

def semantic_get(query: str, project: str = "auto", similarity_threshold: float = 0.95):
    """
    Get cached value using semantic similarity.

    Args:
        query: Query text
        project: Project name (None for global, "auto" for active project)
        similarity_threshold: Minimum similarity score (0-1)

    Returns:
        Cached value or None
    """
    SemanticCache = _lazy_semantic_cache()
    if SemanticCache is None:
        return None

    if project == "auto":
        project = _get_active_project()

    try:
        cache = SemanticCache(project=project, similarity_threshold=similarity_threshold)
        return cache.get(query)
    except Exception as e:
        logger.error(f"Semantic cache get failed: {e}")
        return None

def semantic_set(query: str, value, ttl_sec: int = 3600, project: str = "auto"):
    """
    Cache a value using semantic similarity.

    Args:
        query: Query text
        value: Value to cache
        ttl_sec: Time to live in seconds
        project: Project name (None for global, "auto" for active project)
    """
    SemanticCache = _lazy_semantic_cache()
    if SemanticCache is None:
        return

    if project == "auto":
        project = _get_active_project()

    try:
        cache = SemanticCache(project=project)
        cache.set(query, value, ttl_sec=ttl_sec)
    except Exception as e:
        logger.error(f"Semantic cache set failed: {e}")