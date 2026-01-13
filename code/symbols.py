"""AST-based Python symbol extraction (Serena-like)."""
import ast
from pathlib import Path
from typing import Optional


class SymbolInfo:
    """Lightweight symbol info container."""
    __slots__ = ('name', 'kind', 'lineno', 'end_lineno', 'name_path', 'children', 'body')

    def __init__(self, name: str, kind: str, lineno: int, end_lineno: int,
                 name_path: str = "", body: str = ""):
        self.name = name
        self.kind = kind  # 'class', 'function', 'method', 'variable'
        self.lineno = lineno
        self.end_lineno = end_lineno
        self.name_path = name_path or name
        self.children: list['SymbolInfo'] = []
        self.body = body

    def to_dict(self, include_body: bool = False) -> dict:
        d = {
            "name": self.name,
            "kind": self.kind,
            "lineno": self.lineno,
            "end_lineno": self.end_lineno,
            "name_path": self.name_path,
        }
        if self.children:
            d["children"] = [c.to_dict(include_body) for c in self.children]
        if include_body and self.body:
            d["body"] = self.body
        return d


def _get_source_segment(source_lines: list[str], start: int, end: int) -> str:
    """Extract source segment by line range."""
    if not source_lines or start < 1:
        return ""
    return "\n".join(source_lines[start - 1:end])


def extract_symbols(
    file_path: str,
    depth: int = 2,
    include_body: bool = False
) -> list[dict]:
    """Extract symbols from a Python file using AST.

    Args:
        file_path: Path to Python file
        depth: 1=top-level only, 2=include class methods
        include_body: Include source code body

    Returns:
        List of symbol dicts with name, kind, lineno, etc.
    """
    path = Path(file_path)
    if not path.exists() or path.suffix != ".py":
        return []

    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return []

    source_lines = source.splitlines() if include_body else []
    symbols: list[SymbolInfo] = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            end_line = node.end_lineno or node.lineno
            body = _get_source_segment(source_lines, node.lineno, end_line) if include_body else ""
            sym = SymbolInfo(node.name, "class", node.lineno, end_line, node.name, body)

            if depth >= 2:
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                        child_end = child.end_lineno or child.lineno
                        child_body = _get_source_segment(source_lines, child.lineno, child_end) if include_body else ""
                        child_sym = SymbolInfo(
                            child.name, "method", child.lineno, child_end,
                            f"{node.name}/{child.name}", child_body
                        )
                        sym.children.append(child_sym)

            symbols.append(sym)

        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            end_line = node.end_lineno or node.lineno
            body = _get_source_segment(source_lines, node.lineno, end_line) if include_body else ""
            sym = SymbolInfo(node.name, "function", node.lineno, end_line, node.name, body)
            symbols.append(sym)

        elif isinstance(node, ast.Assign):
            # Module-level variable assignments
            for target in node.targets:
                if isinstance(target, ast.Name):
                    sym = SymbolInfo(target.id, "variable", node.lineno, node.end_lineno or node.lineno, target.id)
                    symbols.append(sym)

    return [s.to_dict(include_body) for s in symbols]


def find_symbol(
    pattern: str,
    file_path: Optional[str] = None,
    project_root: Optional[str] = None,
    include_body: bool = True,
    max_results: int = 10
) -> list[dict]:
    """Find symbol definitions by name pattern.

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

    if file_path:
        # Search single file
        files = [Path(file_path)]
    elif project_root:
        # Search all Python files in project
        files = list(Path(project_root).rglob("*.py"))
    else:
        return []

    for fp in files:
        if not fp.exists() or fp.is_dir():
            continue
        # Skip common non-code directories
        if any(part.startswith('.') or part in ('__pycache__', 'node_modules', 'venv', '.venv')
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
