"""Find symbol references across codebase."""
import re
from pathlib import Path
from typing import Optional


def find_references(
    symbol: str,
    project_root: str,
    file_glob: str = "**/*.py",
    context_lines: int = 2,
    max_results: int = 50
) -> list[dict]:
    """Find all references to a symbol in the codebase.

    Args:
        symbol: Symbol name to search for
        project_root: Root directory to search
        file_glob: Glob pattern for files to search
        context_lines: Lines of context around each match
        max_results: Maximum results to return

    Returns:
        List of reference locations with context
    """
    results = []
    root = Path(project_root)

    # Build regex pattern for word boundary match
    pattern = re.compile(rf'\b{re.escape(symbol)}\b')

    for fp in root.glob(file_glob):
        if not fp.is_file():
            continue
        # Skip common non-code directories
        if any(part.startswith('.') or part in ('__pycache__', 'node_modules', 'venv', '.venv')
               for part in fp.parts):
            continue

        try:
            lines = fp.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, PermissionError):
            continue

        for i, line in enumerate(lines, start=1):
            if pattern.search(line):
                # Get context
                start = max(0, i - 1 - context_lines)
                end = min(len(lines), i + context_lines)
                context = lines[start:end]

                results.append({
                    "file": str(fp.relative_to(root)),
                    "line": i,
                    "column": line.find(symbol) + 1,
                    "text": line.strip(),
                    "context": "\n".join(context),
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

    # Patterns for import statements
    patterns = [
        re.compile(rf'^import\s+.*\b{re.escape(symbol)}\b'),
        re.compile(rf'^from\s+.*\bimport\s+.*\b{re.escape(symbol)}\b'),
    ]

    for fp in root.rglob("*.py"):
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
                        "type": "import"
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

    return result
