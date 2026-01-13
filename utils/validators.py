# utils/validators.py - Input validation for security
"""
Security validators for user input sanitization.
Prevents command injection and path traversal attacks.
"""

import re
from pathlib import Path
from typing import Optional


# Dangerous shell metacharacters
SHELL_METACHARACTERS = frozenset([';', '&', '|', '$', '`', '(', ')', '{', '}', '<', '>', '\n', '\r', '\x00'])


def validate_project_path(path: str) -> Path:
    """
    Validate and sanitize project path.

    Args:
        path: User-provided path string

    Returns:
        Resolved Path object

    Raises:
        ValueError: If path is invalid or contains dangerous characters
    """
    if not path:
        raise ValueError("Path cannot be empty")

    # Resolve to absolute path
    try:
        p = Path(path).resolve()
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Invalid path format: {e}")

    # Security checks
    if not p.exists():
        raise ValueError(f"Path does not exist: {path}")

    if not p.is_dir():
        raise ValueError(f"Not a directory: {path}")

    # Prevent path traversal
    if ".." in p.parts:
        raise ValueError("Path traversal (..) not allowed")

    # Check for shell metacharacters
    path_str = str(p)
    dangerous_found = [c for c in SHELL_METACHARACTERS if c in path_str]
    if dangerous_found:
        raise ValueError(f"Invalid characters in path: {dangerous_found}")

    return p


def validate_project_name(name: str, allow_auto: bool = True) -> str:
    """
    Validate project name.

    Args:
        name: Project name to validate
        allow_auto: If True, "auto" is a valid value

    Returns:
        Validated project name

    Raises:
        ValueError: If name is invalid
    """
    if not name:
        raise ValueError("Project name cannot be empty")

    # Allow "auto" as special value
    if allow_auto and name == "auto":
        return name

    # Length check
    if len(name) > 64:
        raise ValueError("Project name must be at most 64 characters")

    # Only alphanumeric, underscore, hyphen
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        raise ValueError(f"Invalid project name: {name}. Use only alphanumeric, underscore, hyphen.")

    return name


def validate_query(query: str, max_length: int = 10000) -> str:
    """
    Validate search query.

    Args:
        query: Search query string
        max_length: Maximum allowed length

    Returns:
        Validated query

    Raises:
        ValueError: If query is invalid
    """
    if not query:
        raise ValueError("Query cannot be empty")

    if len(query) > max_length:
        raise ValueError(f"Query too long: {len(query)} > {max_length}")

    # Remove null bytes
    query = query.replace('\x00', '')

    return query


def validate_memory_key(key: str) -> str:
    """
    Validate memory key.

    Args:
        key: Memory key to validate

    Returns:
        Validated key

    Raises:
        ValueError: If key is invalid
    """
    if not key:
        raise ValueError("Memory key cannot be empty")

    if len(key) > 256:
        raise ValueError("Memory key must be at most 256 characters")

    # Only allow safe characters
    if not re.match(r'^[a-zA-Z0-9_.-]+$', key):
        raise ValueError(f"Invalid memory key: {key}. Use only alphanumeric, underscore, dot, hyphen.")

    return key


def sanitize_for_display(text: str, max_length: int = 1000) -> str:
    """
    Sanitize text for safe display in logs/responses.

    Args:
        text: Text to sanitize
        max_length: Maximum length to return

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Remove control characters except newline/tab
    sanitized = ''.join(c if c.isprintable() or c in '\n\t' else '?' for c in text)

    # Truncate if needed
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "... (truncated)"

    return sanitized
