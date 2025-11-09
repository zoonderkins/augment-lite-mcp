import sqlite3, time, os, json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("AUGMENT_DB_DIR", "./data")) / "longterm.sqlite"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def _resolve_auto_project():
    """Resolve auto project mode intelligently"""
    # Use centralized implementation to avoid code duplication
    from utils.project_utils import resolve_auto_project
    return resolve_auto_project()

def _db():
    conn = sqlite3.connect(DB_PATH)
    # Updated schema: add project column
    conn.execute("""CREATE TABLE IF NOT EXISTS mem (
        project TEXT NOT NULL,
        k TEXT NOT NULL,
        v TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL,
        PRIMARY KEY (project, k)
    )""")
    return conn

def get_mem(key: str, project: str = None):
    """
    Get memory value.

    Args:
        key: Memory key
        project: Project name (None for global, "auto" for active project)
    """
    if project == "auto":
        project = _resolve_auto_project()

    # Use empty string for global memory
    project = project or ""

    with _db() as conn:
        cur = conn.execute("SELECT v FROM mem WHERE project=? AND k=?", (project, key))
        row = cur.fetchone()
        return row[0] if row else None

def set_mem(key: str, value: str, project: str = None):
    """
    Set memory value.

    Args:
        key: Memory key
        value: Memory value
        project: Project name (None for global, "auto" for active project)
    """
    if project == "auto":
        project = _resolve_auto_project()

    # Use empty string for global memory
    project = project or ""

    now = int(time.time())
    with _db() as conn:
        conn.execute(
            "REPLACE INTO mem (project, k, v, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (project, key, value, now, now)
        )

def list_mem(project: str = None):
    """
    List all memory keys for a project.

    Args:
        project: Project name (None for global, "auto" for active project)

    Returns:
        List of (key, value, updated_at) tuples
    """
    if project == "auto":
        project = _resolve_auto_project()

    project = project or ""

    with _db() as conn:
        cur = conn.execute(
            "SELECT k, v, updated_at FROM mem WHERE project=? ORDER BY updated_at DESC",
            (project,)
        )
        return cur.fetchall()

def delete_mem(key: str, project: str = None):
    """
    Delete memory value.

    Args:
        key: Memory key
        project: Project name (None for global, "auto" for active project)
    """
    if project == "auto":
        project = _resolve_auto_project()

    project = project or ""

    with _db() as conn:
        conn.execute("DELETE FROM mem WHERE project=? AND k=?", (project, key))