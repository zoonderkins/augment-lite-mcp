"""Multi-language symbol extraction using Tree-sitter (with Python AST fallback)."""
import ast
from pathlib import Path
from typing import Optional

# Try to import tree-sitter parser
try:
    from .tree_sitter_parser import (
        parse_file, detect_language, extract_symbols_from_tree,
        supported_extensions, EXT_TO_LANG
    )
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    EXT_TO_LANG = {".py": "python"}

    def supported_extensions():
        return [".py"]


def extract_symbols(
    file_path: str,
    depth: int = 2,
    include_body: bool = False
) -> list[dict]:
    """Extract symbols from a source file.

    Uses Tree-sitter for multi-language support, falls back to Python AST.

    Args:
        file_path: Path to source file
        depth: 1=top-level only, 2=include nested (class methods, etc.)
        include_body: Include source code body

    Returns:
        List of symbol dicts with name, kind, lineno, language, etc.
    """
    path = Path(file_path)
    if not path.exists():
        return []

    ext = path.suffix.lower()

    # Try Tree-sitter first (multi-language)
    if TREE_SITTER_AVAILABLE and ext in EXT_TO_LANG:
        try:
            source = path.read_bytes()
            tree = parse_file(file_path)
            if tree:
                lang = detect_language(file_path)
                return extract_symbols_from_tree(tree, source, lang, depth, include_body)
        except Exception:
            pass  # Fall through to Python AST

    # Fallback: Python AST for .py files
    if ext == ".py":
        return _extract_python_ast(file_path, depth, include_body)

    return []


def _extract_python_ast(file_path: str, depth: int, include_body: bool) -> list[dict]:
    """Extract symbols from Python file using built-in AST (fallback)."""
    path = Path(file_path)
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return []

    source_lines = source.splitlines() if include_body else []
    symbols = []

    def get_body(start: int, end: int) -> str:
        if not include_body or not source_lines:
            return ""
        return "\n".join(source_lines[start - 1:end])

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            end_line = node.end_lineno or node.lineno
            sym = {
                "name": node.name,
                "kind": "class",
                "lineno": node.lineno,
                "end_lineno": end_line,
                "name_path": node.name,
                "language": "python",
            }
            if include_body:
                sym["body"] = get_body(node.lineno, end_line)

            if depth >= 2:
                children = []
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        child_end = child.end_lineno or child.lineno
                        child_sym = {
                            "name": child.name,
                            "kind": "method",
                            "lineno": child.lineno,
                            "end_lineno": child_end,
                            "name_path": f"{node.name}/{child.name}",
                            "language": "python",
                        }
                        if include_body:
                            child_sym["body"] = get_body(child.lineno, child_end)
                        children.append(child_sym)
                if children:
                    sym["children"] = children

            symbols.append(sym)

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end_line = node.end_lineno or node.lineno
            sym = {
                "name": node.name,
                "kind": "function",
                "lineno": node.lineno,
                "end_lineno": end_line,
                "name_path": node.name,
                "language": "python",
            }
            if include_body:
                sym["body"] = get_body(node.lineno, end_line)
            symbols.append(sym)

        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    symbols.append({
                        "name": target.id,
                        "kind": "variable",
                        "lineno": node.lineno,
                        "end_lineno": node.end_lineno or node.lineno,
                        "name_path": target.id,
                        "language": "python",
                    })

    return symbols


def find_symbol(
    pattern: str,
    file_path: Optional[str] = None,
    project_root: Optional[str] = None,
    include_body: bool = True,
    max_results: int = 10
) -> list[dict]:
    """Find symbol definitions by name pattern (multi-language).

    Args:
        pattern: Symbol name or prefix (e.g., 'MyClass', 'handle_')
        file_path: Optional specific file to search
        project_root: Project root directory
        include_body: Include source code
        max_results: Maximum results to return

    Returns:
        List of matching symbols with file path
    """
    results = []
    pattern_lower = pattern.lower()

    # Determine which extensions to search
    extensions = supported_extensions() if TREE_SITTER_AVAILABLE else [".py"]

    if file_path:
        files = [Path(file_path)]
    elif project_root:
        files = []
        root = Path(project_root)
        for ext in extensions:
            files.extend(root.rglob(f"*{ext}"))
    else:
        return []

    for fp in files:
        if not fp.exists() or fp.is_dir():
            continue
        # Skip common non-code directories
        if any(part.startswith('.') or part in ('__pycache__', 'node_modules', 'venv', '.venv', 'dist', 'build')
               for part in fp.parts):
            continue

        symbols = extract_symbols(str(fp), depth=2, include_body=include_body)

        for sym in symbols:
            name_lower = sym["name"].lower()
            if pattern_lower in name_lower or name_lower.startswith(pattern_lower):
                sym["file"] = str(fp)
                results.append(sym)
                if len(results) >= max_results:
                    return results

            # Also check children (methods)
            for child in sym.get("children", []):
                child_name_lower = child["name"].lower()
                if pattern_lower in child_name_lower or child_name_lower.startswith(pattern_lower):
                    child["file"] = str(fp)
                    child["parent"] = sym["name"]
                    results.append(child)
                    if len(results) >= max_results:
                        return results

    return results


def get_symbol_at_line(file_path: str, line: int) -> Optional[dict]:
    """Get symbol definition containing a specific line."""
    symbols = extract_symbols(file_path, depth=2, include_body=False)

    def find_in_symbols(syms: list[dict]) -> Optional[dict]:
        for sym in syms:
            if sym["lineno"] <= line <= sym["end_lineno"]:
                # Check children first (more specific)
                for child in sym.get("children", []):
                    if child["lineno"] <= line <= child["end_lineno"]:
                        return child
                return sym
        return None

    return find_in_symbols(symbols)


def get_supported_languages() -> list[str]:
    """Return list of supported languages."""
    if TREE_SITTER_AVAILABLE:
        from .tree_sitter_parser import supported_languages
        return supported_languages()
    return ["python"]
