"""File finding and directory listing (Serena-like)."""
import os
from pathlib import Path
from typing import Optional
import fnmatch


def list_directory(
    path: str = ".",
    project_root: Optional[str] = None,
    recursive: bool = False,
    pattern: Optional[str] = None,
    max_items: int = 200
) -> dict:
    """List directory contents.

    Args:
        path: Directory path (relative or absolute)
        project_root: Project root for relative paths
        recursive: List recursively
        pattern: Glob pattern filter (e.g., '*.py')
        max_items: Maximum items to return

    Returns:
        Dict with files and directories
    """
    # Resolve path
    if project_root and not Path(path).is_absolute():
        full_path = Path(project_root) / path
    else:
        full_path = Path(path)

    if not full_path.exists():
        return {"ok": False, "error": f"Path not found: {path}"}

    if not full_path.is_dir():
        return {"ok": False, "error": f"Not a directory: {path}"}

    files = []
    directories = []
    count = 0

    try:
        if recursive:
            for root, dirs, filenames in os.walk(full_path):
                # Skip hidden and system directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in
                          ('__pycache__', 'node_modules', 'venv', '.venv', 'dist', 'build')]

                rel_root = Path(root).relative_to(full_path)

                for d in dirs:
                    if count >= max_items:
                        break
                    rel_path = rel_root / d if str(rel_root) != '.' else Path(d)
                    directories.append(str(rel_path))
                    count += 1

                for f in filenames:
                    if count >= max_items:
                        break
                    if f.startswith('.'):
                        continue
                    if pattern and not fnmatch.fnmatch(f, pattern):
                        continue
                    rel_path = rel_root / f if str(rel_root) != '.' else Path(f)
                    files.append(str(rel_path))
                    count += 1

                if count >= max_items:
                    break
        else:
            for item in full_path.iterdir():
                if count >= max_items:
                    break
                if item.name.startswith('.'):
                    continue
                if item.is_dir():
                    if item.name not in ('__pycache__', 'node_modules', 'venv', '.venv'):
                        directories.append(item.name)
                        count += 1
                else:
                    if pattern and not fnmatch.fnmatch(item.name, pattern):
                        continue
                    files.append(item.name)
                    count += 1

        return {
            "ok": True,
            "path": str(full_path),
            "files": sorted(files),
            "directories": sorted(directories),
            "count": len(files) + len(directories),
            "truncated": count >= max_items
        }

    except PermissionError:
        return {"ok": False, "error": f"Permission denied: {path}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def find_files(
    pattern: str,
    project_root: str,
    max_results: int = 100
) -> dict:
    """Find files by glob pattern.

    Args:
        pattern: Glob pattern (e.g., '**/*.py', 'src/**/*.ts')
        project_root: Root directory
        max_results: Maximum results

    Returns:
        Dict with matching files
    """
    root = Path(project_root)
    if not root.exists():
        return {"ok": False, "error": f"Root not found: {project_root}"}

    files = []
    count = 0

    try:
        for fp in root.glob(pattern):
            if count >= max_results:
                break
            if not fp.is_file():
                continue
            # Skip hidden and system directories
            if any(part.startswith('.') or part in ('__pycache__', 'node_modules', 'venv', '.venv')
                   for part in fp.parts):
                continue

            files.append({
                "path": str(fp.relative_to(root)),
                "size": fp.stat().st_size,
            })
            count += 1

        return {
            "ok": True,
            "pattern": pattern,
            "files": files,
            "count": len(files),
            "truncated": count >= max_results
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}


def find_file_by_name(
    name: str,
    project_root: str,
    max_results: int = 10
) -> dict:
    """Find files by name (partial match).

    Args:
        name: File name or partial name
        project_root: Root directory
        max_results: Maximum results

    Returns:
        Dict with matching files
    """
    root = Path(project_root)
    if not root.exists():
        return {"ok": False, "error": f"Root not found: {project_root}"}

    files = []
    name_lower = name.lower()

    try:
        for fp in root.rglob("*"):
            if len(files) >= max_results:
                break
            if not fp.is_file():
                continue
            if any(part.startswith('.') or part in ('__pycache__', 'node_modules', 'venv', '.venv')
                   for part in fp.parts):
                continue
            if name_lower in fp.name.lower():
                files.append({
                    "path": str(fp.relative_to(root)),
                    "name": fp.name,
                })

        return {
            "ok": True,
            "query": name,
            "files": files,
            "count": len(files)
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}
