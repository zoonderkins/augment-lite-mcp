"""File reading with line ranges (Serena-like)."""
from pathlib import Path
from typing import Optional


def read_file(
    path: str,
    project_root: Optional[str] = None,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
    max_lines: int = 500
) -> dict:
    """Read file content with optional line range.

    Args:
        path: File path (relative to project_root or absolute)
        project_root: Project root for relative paths
        start_line: Start line (1-indexed, inclusive)
        end_line: End line (1-indexed, inclusive)
        max_lines: Maximum lines to return

    Returns:
        Dict with content, line info, and metadata
    """
    # Resolve path
    if project_root and not Path(path).is_absolute():
        full_path = Path(project_root) / path
    else:
        full_path = Path(path)

    if not full_path.exists():
        return {"ok": False, "error": f"File not found: {path}"}

    if not full_path.is_file():
        return {"ok": False, "error": f"Not a file: {path}"}

    try:
        content = full_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        total_lines = len(lines)

        # Apply line range
        if start_line is not None:
            start_idx = max(0, start_line - 1)
        else:
            start_idx = 0

        if end_line is not None:
            end_idx = min(total_lines, end_line)
        else:
            end_idx = min(total_lines, start_idx + max_lines)

        selected = lines[start_idx:end_idx]

        # Add line numbers
        numbered = [f"{i:4d}| {line}" for i, line in enumerate(selected, start=start_idx + 1)]

        return {
            "ok": True,
            "path": str(full_path),
            "content": "\n".join(numbered),
            "raw_content": "\n".join(selected),
            "start_line": start_idx + 1,
            "end_line": end_idx,
            "total_lines": total_lines,
            "truncated": (end_idx - start_idx) < (total_lines - start_idx)
        }

    except UnicodeDecodeError:
        return {"ok": False, "error": f"Cannot read binary file: {path}"}
    except PermissionError:
        return {"ok": False, "error": f"Permission denied: {path}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def read_symbol_body(
    path: str,
    symbol_name: str,
    project_root: Optional[str] = None
) -> dict:
    """Read specific symbol body from file.

    Args:
        path: File path
        symbol_name: Symbol name or name_path (e.g., 'MyClass/method')
        project_root: Project root

    Returns:
        Dict with symbol body content
    """
    from code.symbols import extract_symbols

    # Resolve path
    if project_root and not Path(path).is_absolute():
        full_path = Path(project_root) / path
    else:
        full_path = Path(path)

    if not full_path.exists():
        return {"ok": False, "error": f"File not found: {path}"}

    symbols = extract_symbols(str(full_path), depth=2, include_body=True)

    # Search for symbol
    for sym in symbols:
        if sym["name"] == symbol_name or sym.get("name_path") == symbol_name:
            return {
                "ok": True,
                "symbol": sym,
                "body": sym.get("body", ""),
                "path": str(full_path)
            }
        # Check children
        for child in sym.get("children", []):
            if child["name"] == symbol_name or child.get("name_path") == symbol_name:
                return {
                    "ok": True,
                    "symbol": child,
                    "body": child.get("body", ""),
                    "path": str(full_path)
                }

    return {"ok": False, "error": f"Symbol not found: {symbol_name}"}
