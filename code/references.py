"""Find symbol references across codebase using Tree-sitter AST."""
import re
from pathlib import Path
from typing import Optional

# Try to import tree-sitter parser
try:
    from .tree_sitter_parser import (
        parse_file, detect_language, find_references_in_tree,
        supported_extensions, EXT_TO_LANG
    )
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    EXT_TO_LANG = {".py": "python"}

    def supported_extensions():
        return [".py"]


def find_references(
    symbol: str,
    project_root: str,
    file_glob: Optional[str] = None,
    context_lines: int = 2,
    max_results: int = 50
) -> list[dict]:
    """Find all references to a symbol in the codebase.

    Uses Tree-sitter AST for accurate identifier matching when available,
    falls back to regex for unsupported languages.

    Args:
        symbol: Symbol name to search for
        project_root: Root directory to search
        file_glob: Optional glob pattern (e.g., "**/*.py"). Auto-detected if None.
        context_lines: Lines of context around each match
        max_results: Maximum results to return

    Returns:
        List of reference locations with context
    """
    results = []
    root = Path(project_root)

    # Determine files to search
    if file_glob:
        files = list(root.glob(file_glob))
    else:
        # Search all supported extensions
        files = []
        extensions = supported_extensions() if TREE_SITTER_AVAILABLE else [".py"]
        for ext in extensions:
            files.extend(root.rglob(f"*{ext}"))

    for fp in files:
        if not fp.is_file():
            continue
        # Skip common non-code directories
        if any(part.startswith('.') or part in ('__pycache__', 'node_modules', 'venv', '.venv', 'dist', 'build')
               for part in fp.parts):
            continue

        try:
            source = fp.read_bytes()
            source_text = source.decode("utf-8", errors="replace")
            source_lines = source_text.splitlines()
        except (UnicodeDecodeError, PermissionError):
            continue

        # Try Tree-sitter AST-based search first
        if TREE_SITTER_AVAILABLE:
            lang = detect_language(str(fp))
            if lang:
                tree = parse_file(str(fp))
                if tree:
                    refs = find_references_in_tree(tree, source, symbol, lang)
                    for ref in refs:
                        line_idx = ref["line"] - 1
                        start = max(0, line_idx - context_lines)
                        end = min(len(source_lines), line_idx + context_lines + 1)
                        context = source_lines[start:end]

                        results.append({
                            "file": str(fp.relative_to(root)),
                            "line": ref["line"],
                            "column": ref["column"],
                            "text": ref["text"].strip(),
                            "context": "\n".join(context),
                            "node_type": ref.get("node_type", "identifier"),
                            "language": lang,
                            "method": "ast",
                        })

                        if len(results) >= max_results:
                            return results
                    continue  # Move to next file

        # Fallback: regex search
        pattern = re.compile(rf'\b{re.escape(symbol)}\b')
        for i, line in enumerate(source_lines, start=1):
            if pattern.search(line):
                start = max(0, i - 1 - context_lines)
                end = min(len(source_lines), i + context_lines)
                context = source_lines[start:end]

                results.append({
                    "file": str(fp.relative_to(root)),
                    "line": i,
                    "column": line.find(symbol) + 1,
                    "text": line.strip(),
                    "context": "\n".join(context),
                    "language": detect_language(str(fp)) if TREE_SITTER_AVAILABLE else "unknown",
                    "method": "regex",
                })

                if len(results) >= max_results:
                    return results

    return results


def find_imports(
    symbol: str,
    project_root: str,
    max_results: int = 20
) -> list[dict]:
    """Find import statements for a symbol.

    Args:
        symbol: Symbol name (module, class, function)
        project_root: Root directory to search
        max_results: Maximum results

    Returns:
        List of import locations
    """
    results = []
    root = Path(project_root)

    # Import patterns (Python-focused, but works for JS/TS too)
    patterns = [
        re.compile(rf'^import\s+.*\b{re.escape(symbol)}\b'),
        re.compile(rf'^from\s+.*\bimport\s+.*\b{re.escape(symbol)}\b'),
        re.compile(rf'require\s*\(\s*[\'"].*{re.escape(symbol)}.*[\'"]\s*\)'),  # JS require
        re.compile(rf'from\s+[\'"].*{re.escape(symbol)}.*[\'"]\s*import'),  # JS/TS import
    ]

    extensions = supported_extensions() if TREE_SITTER_AVAILABLE else [".py"]

    for ext in extensions:
        for fp in root.rglob(f"*{ext}"):
            if not fp.is_file():
                continue
            if any(part.startswith('.') or part in ('__pycache__', 'node_modules', 'venv', '.venv')
                   for part in fp.parts):
                continue

            try:
                lines = fp.read_text(encoding="utf-8").splitlines()
            except (UnicodeDecodeError, PermissionError):
                continue

            for i, line in enumerate(lines, start=1):
                stripped = line.strip()
                for pattern in patterns:
                    if pattern.match(stripped):
                        results.append({
                            "file": str(fp.relative_to(root)),
                            "line": i,
                            "text": stripped,
                            "type": "import",
                            "language": detect_language(str(fp)) if TREE_SITTER_AVAILABLE else "unknown",
                        })
                        if len(results) >= max_results:
                            return results
                        break

    return results


def find_usages(
    symbol: str,
    project_root: str,
    include_definitions: bool = False,
    max_results: int = 50
) -> dict:
    """Comprehensive usage search: imports, references, and optionally definitions.

    Args:
        symbol: Symbol to search
        project_root: Root directory
        include_definitions: Include definition sites
        max_results: Max results per category

    Returns:
        Dict with 'imports', 'references', and optionally 'definitions'
    """
    result = {
        "symbol": symbol,
        "imports": find_imports(symbol, project_root, max_results=max_results),
        "references": find_references(symbol, project_root, max_results=max_results),
    }

    if include_definitions:
        from .symbols import find_symbol
        result["definitions"] = find_symbol(symbol, project_root=project_root, max_results=max_results)

    # Add summary
    result["summary"] = {
        "total_imports": len(result["imports"]),
        "total_references": len(result["references"]),
        "total_definitions": len(result.get("definitions", [])),
        "method": "tree-sitter" if TREE_SITTER_AVAILABLE else "regex",
    }

    return result
