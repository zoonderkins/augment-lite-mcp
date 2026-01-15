"""
Auggie MCP Integration Helper

Provides integration hints for auggie-mcp (stdio-based MCP server).
Since auggie uses stdio protocol, direct Python calls are not possible.
Instead, this module provides orchestration hints for Claude.

auggie-mcp is added via:
  claude mcp add-json auggie-mcp --scope user
    '{"type":"stdio","command":"auggie","args":["--mcp","--mcp-auto-workspace"]}'

Usage:
    from retrieval.auggie_client import get_auggie_hint, format_auggie_call

    hint = get_auggie_hint("Where is auth handled?")
"""

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def is_auggie_available() -> bool:
    """
    Check if auggie integration is available.

    Since auggie is stdio-based, we cannot call it directly from Python.
    Always returns False to indicate manual orchestration needed.
    """
    return False


def get_auggie_hint(query: str) -> str:
    """
    Generate hint for Claude to call auggie-mcp.

    Args:
        query: The search query

    Returns:
        Formatted MCP tool call suggestion
    """
    safe_query = query.replace('"', "'")
    return f'mcp__auggie-mcp__codebase-retrieval(information_request="{safe_query}")'


def auggie_search(query: str, timeout: int = 30) -> Dict:
    """
    Placeholder for auggie search - returns orchestration hint.

    Since auggie-mcp uses stdio protocol (not HTTP), we cannot call it
    directly from Python. This function returns a hint for Claude to
    make the call.
    """
    return {
        "available": False,
        "results": [],
        "hint": get_auggie_hint(query),
        "note": "auggie-mcp uses stdio protocol. Claude should call it directly."
    }


def merge_results(
    augment_lite_results: List[Dict],
    auggie_results: List[Dict],
    max_total: int = 16
) -> List[Dict]:
    """
    Merge and deduplicate results from both sources.

    Args:
        augment_lite_results: Results from augment-lite rag_search
        auggie_results: Results from auggie-mcp
        max_total: Maximum total results to return

    Returns:
        Merged and deduplicated results list
    """
    seen_sources = set()
    merged = []

    max_per_source = max_total // 2

    # Add augment-lite results first (local, faster)
    for hit in augment_lite_results[:max_per_source]:
        source = hit.get("source", "")
        if source not in seen_sources:
            hit["_source_engine"] = "augment-lite"
            merged.append(hit)
            seen_sources.add(source)

    # Add auggie results
    for hit in auggie_results[:max_per_source]:
        source = hit.get("source", "")
        if source not in seen_sources:
            hit["_source_engine"] = "auggie"
            merged.append(hit)
            seen_sources.add(source)

    # Fill remaining slots
    remaining = max_total - len(merged)
    if remaining > 0:
        for hit in augment_lite_results[max_per_source:]:
            if len(merged) >= max_total:
                break
            source = hit.get("source", "")
            if source not in seen_sources:
                hit["_source_engine"] = "augment-lite"
                merged.append(hit)
                seen_sources.add(source)

    return merged
