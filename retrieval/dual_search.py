"""
Dual Search Engine - Combines augment-lite + auggie-mcp

Automatically orchestrates:
1. augment-lite: Local hybrid BM25 + vector search
2. auggie-mcp: External semantic search (if configured)

This implements the CLAUDE.md Phase 1 workflow:
- Parallel retrieval from multiple sources
- Result deduplication and ranking
- Fallback hints for manual orchestration
"""

import logging
from typing import List, Dict
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

logger = logging.getLogger(__name__)


def _detect_stale_index(al_hits: List[Dict], auggie_hits: List[Dict]) -> bool:
    """
    Detect if augment-lite index is stale compared to auggie results.

    Heuristics:
    1. auggie has results but augment-lite has none/few
    2. auggie sources don't appear in augment-lite results
    """
    if not auggie_hits:
        return False

    if len(al_hits) < 2 and len(auggie_hits) >= 3:
        return True

    # Check if auggie found files that augment-lite missed
    auggie_sources = set()
    for hit in auggie_hits:
        src = hit.get("source", "")
        if src and src != "unknown":
            auggie_sources.add(Path(src).name)

    al_sources = set()
    for hit in al_hits:
        src = hit.get("source", "")
        if src and src != "unknown":
            al_sources.add(Path(src).name)

    # If auggie found >50% files that augment-lite missed, index is stale
    if auggie_sources:
        missing = auggie_sources - al_sources
        if len(missing) / len(auggie_sources) > 0.5:
            return True

    return False


def dual_search(
    query: str,
    k: int = 8,
    use_subagent: bool = True,
    use_iterative: bool = False,
    include_auggie: bool = True,
    auto_rebuild: bool = True,
    project: str = "auto"
) -> Dict:
    """
    Execute search across both augment-lite and auggie-mcp engines.

    Args:
        query: Natural language search query
        k: Number of results per engine
        use_subagent: Enable LLM re-ranking for augment-lite
        use_iterative: Enable multi-round query expansion
        include_auggie: Try to include auggie results (if configured)
        auto_rebuild: Auto-trigger index_rebuild if stale index detected
        project: Project name for augment-lite search

    Returns:
        Dict with:
        - ok: bool
        - hits: List[Dict] - merged results
        - sources: Dict - breakdown by source engine
        - auggie_available: bool
        - auggie_hint: str (if auggie not available)
        - index_rebuilt: bool (if auto_rebuild triggered)
    """
    from retrieval.subagent_filter import hybrid_search_with_subagent
    from retrieval.iterative_search import iterative_search, should_use_iterative_search
    from retrieval.auggie_client import auggie_search, is_auggie_available, merge_results

    results = {
        "ok": True,
        "hits": [],
        "sources": {
            "augment_lite": {"count": 0, "results": []},
            "auggie": {"count": 0, "results": [], "available": False}
        },
        "auggie_available": is_auggie_available(),
        "auggie_hint": None
    }

    # 1. Execute augment-lite search
    try:
        # Auto-enable iterative for complex queries
        if not use_iterative and should_use_iterative_search(query, task_type="lookup"):
            use_iterative = True
            logger.info(f"Auto-enabled iterative search for complex query")

        if use_iterative:
            al_hits = iterative_search(
                query,
                k_per_iteration=k,
                use_subagent=use_subagent,
                project=project
            )
        else:
            al_hits = hybrid_search_with_subagent(
                query,
                k=k,
                use_subagent=use_subagent,
                project=project
            )

        results["sources"]["augment_lite"]["results"] = al_hits
        results["sources"]["augment_lite"]["count"] = len(al_hits)

    except Exception as e:
        logger.error(f"augment-lite search failed: {e}")
        al_hits = []
        results["sources"]["augment_lite"]["error"] = str(e)

    # 2. Execute auggie search (if enabled and configured)
    auggie_hits = []
    if include_auggie:
        auggie_response = auggie_search(query)

        if auggie_response.get("available"):
            auggie_hits = auggie_response.get("results", [])
            results["sources"]["auggie"]["results"] = auggie_hits
            results["sources"]["auggie"]["count"] = len(auggie_hits)
            results["sources"]["auggie"]["available"] = True
        else:
            results["auggie_hint"] = auggie_response.get("hint", "")
            if auggie_response.get("error"):
                results["sources"]["auggie"]["error"] = auggie_response["error"]

    # 3. Merge results
    merged = merge_results(al_hits, auggie_hits, max_total=k * 2)
    results["hits"] = merged
    results["index_rebuilt"] = False

    # 4. Auto-rebuild stale index if detected
    if auto_rebuild and auggie_hits and _detect_stale_index(al_hits, auggie_hits):
        logger.info("Stale index detected, triggering auto-rebuild...")
        try:
            from retrieval.incremental_indexer import incremental_index
            rebuild_result = incremental_index(project=project)
            if rebuild_result.get("ok"):
                results["index_rebuilt"] = True
                results["rebuild_info"] = {
                    "files_updated": rebuild_result.get("files_updated", 0),
                    "reason": "auggie found files missing from augment-lite index"
                }
                logger.info(f"Index rebuilt: {rebuild_result.get('files_updated', 0)} files updated")

                # Re-search with fresh index
                if use_iterative:
                    fresh_hits = iterative_search(query, k_per_iteration=k, use_subagent=use_subagent, project=project)
                else:
                    fresh_hits = hybrid_search_with_subagent(query, k=k, use_subagent=use_subagent, project=project)

                results["sources"]["augment_lite"]["results"] = fresh_hits
                results["sources"]["augment_lite"]["count"] = len(fresh_hits)
                merged = merge_results(fresh_hits, auggie_hits, max_total=k * 2)
                results["hits"] = merged

        except Exception as e:
            logger.warning(f"Auto-rebuild failed: {e}")
            results["rebuild_error"] = str(e)

    # 5. Add orchestration hints if auggie not available
    if not results["auggie_available"] and include_auggie:
        results["auggie_hint"] = (
            "For comprehensive results, also call: "
            "mcp__auggie-mcp__codebase-retrieval(information_request=\"{}\")".format(query)
        )

    return results


def dual_search_simple(
    query: str,
    k: int = 8,
    project: str = "auto"
) -> List[Dict]:
    """
    Simplified dual search that returns just the hit list.

    For direct drop-in replacement of rag_search.
    """
    result = dual_search(query, k=k, project=project)
    return result.get("hits", [])
