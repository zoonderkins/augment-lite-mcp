"""Regex pattern search (complements semantic search)."""
import re
import fnmatch
from pathlib import Path
from typing import Optional


def search_pattern(
    pattern: str,
    project_root: str,
    file_glob: str = "**/*",
    context_lines: int = 2,
    max_results: int = 50,
    case_sensitive: bool = True
) -> list[dict]:
    """Search files using regex pattern.

    Args:
        pattern: Regex pattern to search
        project_root: Root directory
        file_glob: Glob pattern for files (e.g., '**/*.py', 'src/**/*.ts')
        context_lines: Lines of context around matches
        max_results: Maximum results
        case_sensitive: Case-sensitive search

    Returns:
        List of matches with file, line, context
    """
    results = []
    root = Path(project_root)

    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        regex = re.compile(pattern, flags)
    except re.error as e:
        return [{"error": f"Invalid regex: {e}"}]

    # Determine file extensions to search (text files only)
    text_extensions = {
        '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.go', '.rs', '.c', '.cpp', '.h',
        '.rb', '.php', '.swift', '.kt', '.scala', '.sh', '.bash', '.zsh',
        '.json', '.yaml', '.yml', '.toml', '.xml', '.html', '.css', '.scss',
        '.md', '.txt', '.rst', '.sql', '.graphql', '.proto'
    }

    for fp in root.glob(file_glob):
        if not fp.is_file():
            continue
        # Skip binary and system directories
        if any(part.startswith('.') or part in ('__pycache__', 'node_modules', 'venv', '.venv', 'dist', 'build')
               for part in fp.parts):
            continue
        # Skip non-text files unless glob is specific
        if '.' in file_glob:
            pass  # User specified extension
        elif fp.suffix.lower() not in text_extensions:
            continue

        try:
            content = fp.read_text(encoding="utf-8")
            lines = content.splitlines()
        except (UnicodeDecodeError, PermissionError):
            continue

        for i, line in enumerate(lines, start=1):
            match = regex.search(line)
            if match:
                start = max(0, i - 1 - context_lines)
                end = min(len(lines), i + context_lines)
                context = lines[start:end]

                results.append({
                    "file": str(fp.relative_to(root)),
                    "line": i,
                    "column": match.start() + 1,
                    "match": match.group(),
                    "text": line.strip(),
                    "context": "\n".join(context),
                })

                if len(results) >= max_results:
                    return results

    return results


def search_and_replace_preview(
    pattern: str,
    replacement: str,
    project_root: str,
    file_glob: str = "**/*",
    max_results: int = 50
) -> list[dict]:
    """Preview regex replacements (dry-run, no file changes).

    Args:
        pattern: Regex pattern to find
        replacement: Replacement string (supports \\1, \\2 groups)
        project_root: Root directory
        file_glob: File filter
        max_results: Max results

    Returns:
        List of potential changes with before/after preview
    """
    results = []
    root = Path(project_root)

    try:
        regex = re.compile(pattern)
    except re.error as e:
        return [{"error": f"Invalid regex: {e}"}]

    for fp in root.glob(file_glob):
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
            if regex.search(line):
                new_line = regex.sub(replacement, line)
                if new_line != line:
                    results.append({
                        "file": str(fp.relative_to(root)),
                        "line": i,
                        "before": line,
                        "after": new_line,
                    })
                    if len(results) >= max_results:
                        return results

    return results
