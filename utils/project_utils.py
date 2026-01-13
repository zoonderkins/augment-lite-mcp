#!/usr/bin/env python3
"""
Project utility functions for auto-initialization and management.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Optional, List, Tuple
import datetime
import hashlib

BASE = Path(__file__).resolve().parents[1]
PROJECTS_CONFIG = BASE / "data" / "projects.json"
DATA_DIR = BASE / "data"


def load_projects() -> Dict[str, dict]:
    """Load projects configuration."""
    if not PROJECTS_CONFIG.exists():
        return {}
    try:
        with open(PROJECTS_CONFIG, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_projects(projects: Dict[str, dict]):
    """Save projects configuration."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROJECTS_CONFIG, "w", encoding="utf-8") as f:
        json.dump(projects, indent=2, ensure_ascii=False, fp=f)


def get_active_project() -> Optional[str]:
    """Get the active project name."""
    projects = load_projects()
    for name, config in projects.items():
        if config.get("active", False):
            return name
    return None


def resolve_auto_project() -> Optional[str]:
    """
    Resolve 'auto' project mode intelligently.

    Priority:
    1. Check if current directory name matches a registered project
    2. Check if current directory path matches any registered project's root
    3. Fall back to active project
    4. Return None if nothing found
    """
    cwd = Path(os.getcwd()).resolve()
    cwd_name = cwd.name
    projects = load_projects()

    # Priority 1: Check if current directory name matches a registered project
    if cwd_name in projects:
        return cwd_name

    # Priority 2: Check if current directory path matches any registered project's root
    for proj_name, proj_config in projects.items():
        proj_root = Path(proj_config.get("root", "")).resolve()
        if proj_root == cwd:
            return proj_name

    # Priority 3: Fall back to active project
    active = get_active_project()
    if active:
        return active

    # Priority 4: Return None
    return None


def find_project_by_id_or_name(identifier: str) -> Optional[Tuple[str, dict]]:
    """Find project by ID or name. Returns (name, config) or None."""
    projects = load_projects()

    # Try exact name match first
    if identifier in projects:
        return (identifier, projects[identifier])

    # Try ID match
    for name, config in projects.items():
        if config.get("id") == identifier:
            return (name, config)

    return None


def is_project_registered(project_name_or_id: str) -> bool:
    """Check if a project is registered by name or ID."""
    return find_project_by_id_or_name(project_name_or_id) is not None


def resolve_project_name(name_or_id_or_auto: str) -> Optional[str]:
    """Resolve project name from name, ID, or 'auto' (current directory)."""
    if name_or_id_or_auto == "auto":
        # Detect from current working directory
        cwd = Path(os.getcwd()).resolve()
        detected_name = cwd.name

        # Check if this project is registered
        result = find_project_by_id_or_name(detected_name)
        if result:
            return result[0]

        # Not registered, return detected name for potential registration
        return detected_name

    # Try to find by ID or name
    result = find_project_by_id_or_name(name_or_id_or_auto)
    if result:
        return result[0]

    # If not found, return as-is (might be a new project name)
    return name_or_id_or_auto


def has_bm25_index(project: str = "auto") -> bool:
    """Check if BM25 index exists for a project."""
    if project == "auto":
        project = get_active_project()

    if not project:
        return False

    projects = load_projects()
    if project not in projects:
        return False

    config = projects[project]
    db_path = BASE / config.get("db", f"data/corpus_{project}.duckdb")
    chunks_path = BASE / config.get("chunks", f"data/chunks_{project}.jsonl")

    return db_path.exists() and chunks_path.exists()


def has_vector_index(project: str = "auto") -> bool:
    """Check if vector index exists for a project."""
    if project == "auto":
        project = get_active_project()

    if not project:
        return False

    vector_index = DATA_DIR / f"vector_index_{project}.faiss"
    vector_metadata = DATA_DIR / f"vector_metadata_{project}.json"

    return vector_index.exists() and vector_metadata.exists()


def get_chunks_count(project: str = "auto") -> int:
    """Get the number of chunks in a project's index."""
    if project == "auto":
        project = get_active_project()

    if not project or not has_bm25_index(project):
        return 0

    projects = load_projects()
    config = projects[project]
    chunks_path = BASE / config.get("chunks", f"data/chunks_{project}.jsonl")

    try:
        count = 0
        with open(chunks_path, "r", encoding="utf-8") as f:
            for _ in f:
                count += 1
        return count
    except Exception:
        return 0


def get_index_mtime(project: str = "auto") -> Optional[str]:
    """Get the last modified time of a project's index."""
    if project == "auto":
        project = resolve_auto_project()

    if not project or not has_bm25_index(project):
        return None

    projects = load_projects()
    config = projects[project]
    db_path = BASE / config.get("db", f"data/corpus_{project}.duckdb")

    if db_path.exists():
        mtime = db_path.stat().st_mtime
        return datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")

    return None


def get_cache_size(project: str = "auto") -> str:
    """Get the cache size for a project."""
    cache_db = DATA_DIR / "response_cache.sqlite"

    if not cache_db.exists():
        return "0 KB"

    size_bytes = cache_db.stat().st_size

    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def get_memory_keys_count(project: str = "auto") -> int:
    """Get the number of memory keys for a project."""
    memory_db = DATA_DIR / "longterm.sqlite"

    if not memory_db.exists():
        return 0

    try:
        import sqlite3

        if project == "auto":
            project = resolve_auto_project()

        if not project:
            project = ""  # Global memory

        conn = sqlite3.connect(memory_db)
        cursor = conn.execute(
            "SELECT COUNT(*) FROM longterm WHERE project = ?",
            (project,)
        )
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0


def is_valid_project(path: str) -> bool:
    """Check if a path contains a valid code project."""
    path = Path(path)

    if not path.exists() or not path.is_dir():
        return False

    # Check for code files
    code_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs', '.cpp', '.c', '.rb', '.php', '.swift', '.kt'}

    for ext in code_extensions:
        if list(path.rglob(f'*{ext}')):
            return True

    return False


def generate_project_id(name: str, root: str) -> str:
    """Generate a unique project ID based on name and root path."""
    # Use first 8 characters of hash for short ID
    content = f"{name}:{root}"
    return hashlib.sha256(content.encode()).hexdigest()[:8]


def auto_register_project(name: str, path: str) -> bool:
    """Automatically register a project."""
    if not is_valid_project(path):
        return False

    root = Path(path).resolve()
    projects = load_projects()

    # Don't overwrite existing projects
    if name in projects:
        return True

    # Generate project ID
    project_id = generate_project_id(name, str(root))

    projects[name] = {
        "id": project_id,
        "root": str(root),
        "db": f"data/corpus_{name}.duckdb",
        "chunks": f"data/chunks_{name}.jsonl",
        "active": len(projects) == 0,  # First project is active by default
    }

    save_projects(projects)
    return True


def set_active_project(name: str) -> bool:
    """Set a project as active."""
    projects = load_projects()

    if name not in projects:
        return False

    # Deactivate all projects
    for proj_name in projects:
        projects[proj_name]["active"] = False

    # Activate the specified project
    projects[name]["active"] = True

    save_projects(projects)

    # Create symlinks for backward compatibility
    _create_symlinks(name, projects[name])

    return True


def _create_symlinks(name: str, config: dict):
    """Create symlinks to active project's files."""
    db_link = DATA_DIR / "corpus.duckdb"
    chunks_link = DATA_DIR / "chunks.jsonl"

    db_target = BASE / config['db']
    chunks_target = BASE / config['chunks']

    # Remove old symlinks if they exist
    if db_link.exists() or db_link.is_symlink():
        db_link.unlink()
    if chunks_link.exists() or chunks_link.is_symlink():
        chunks_link.unlink()

    # Create new symlinks
    if db_target.exists():
        db_link.symlink_to(db_target.name)

    if chunks_target.exists():
        chunks_link.symlink_to(chunks_target.name)


def get_project_status(project: str = "auto") -> dict:
    """Get comprehensive status of a project."""
    if project == "auto":
        project = resolve_auto_project()

    if not project:
        return {
            "error": "No active project",
            "suggestion": "Register a project first"
        }

    projects = load_projects()

    if project not in projects:
        return {
            "error": f"Project '{project}' not registered",
            "suggestion": "Use project.init to register and initialize"
        }

    config = projects[project]

    status = {
        "project_name": project,
        "registered": True,
        "root": config.get("root"),
        "active": config.get("active", False),
        "bm25_index": {
            "exists": has_bm25_index(project),
            "chunks_count": get_chunks_count(project),
            "last_updated": get_index_mtime(project)
        },
        "vector_index": {
            "exists": has_vector_index(project),
        },
        "cache": {
            "size": get_cache_size(project)
        },
        "memory": {
            "keys_count": get_memory_keys_count(project)
        }
    }

    # Add vector index details if exists
    if has_vector_index(project):
        try:
            vector_metadata_path = DATA_DIR / f"vector_metadata_{project}.json"
            with open(vector_metadata_path, "r") as f:
                metadata = json.load(f)
                status["vector_index"]["vectors_count"] = metadata.get("count", 0)
                status["vector_index"]["model"] = metadata.get("model", "unknown")
                status["vector_index"]["dimension"] = metadata.get("dimension", 0)
        except Exception:
            pass

    return status


def clear_cache(project: str = "auto"):
    """Clear cache for a project."""
    import sqlite3

    cache_db = DATA_DIR / "response_cache.sqlite"

    if not cache_db.exists():
        return {"ok": True, "message": "No cache to clear"}

    if project == "auto":
        project = get_active_project()

    if not project:
        project = ""  # Global cache

    conn = sqlite3.connect(cache_db)

    # Clear exact cache
    conn.execute("DELETE FROM cache WHERE project = ?", (project,))

    conn.commit()
    conn.close()

    # Clear semantic cache if available
    try:
        from semantic_cache import clear_cache as clear_semantic
        clear_semantic(project=project)
    except Exception:
        pass

    return {"ok": True, "message": f"Cache cleared for project: {project or 'global'}"}


def clear_memory(project: str = "auto"):
    """Clear memory for a project."""
    import sqlite3

    memory_db = DATA_DIR / "longterm.sqlite"

    if not memory_db.exists():
        return {"ok": True, "message": "No memory to clear"}

    if project == "auto":
        project = resolve_auto_project()

    if not project:
        project = ""  # Global memory

    conn = sqlite3.connect(memory_db)
    conn.execute("DELETE FROM mem WHERE project = ?", (project,))
    conn.commit()
    conn.close()

    return {"ok": True, "message": f"Memory cleared for project: {project or 'global'}"}


def get_all_projects() -> List[str]:
    """Get list of all project names."""
    projects = load_projects()
    return list(projects.keys())
