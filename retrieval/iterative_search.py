"""
Iterative search with automatic query expansion.

This implements ACE-like multi-round retrieval:
- LLM can call search multiple times
- Automatically expands queries if results are insufficient
- Combines results from multiple iterations
"""

from pathlib import Path
import logging
from typing import List, Dict, Set, Optional

BASE = Path(__file__).resolve().parents[1]

logger = logging.getLogger(__name__)


def iterative_search(
    query: str,
    max_iterations: int = 3,
    min_quality_score: float = 0.7,
    min_results: int = 5,
    k_per_iteration: int = 8,
    use_subagent: bool = True,
    project: str = "auto"
) -> List[Dict]:
    """
    Multi-round retrieval with automatic query expansion.

    Mimics ACE behavior where the LLM can call codebase-retrieval
    multiple times with different search terms.

    Args:
        query: Initial user query
        max_iterations: Maximum number of search iterations
        min_quality_score: Minimum score threshold for results
        min_results: Minimum number of quality results needed
        k_per_iteration: Results per iteration
        use_subagent: Use subagent filtering
        project: Project name

    Returns:
        Combined and deduplicated results
    """
    from retrieval.subagent_filter import hybrid_search_with_subagent

    all_hits = []
    seen_sources: Set[str] = set()
    current_query = query

    for iteration in range(max_iterations):
        logger.info(f"Iteration {iteration + 1}/{max_iterations}: query='{current_query}'")

        # Execute search
        hits = hybrid_search_with_subagent(
            query=current_query,
            k=k_per_iteration,
            use_subagent=use_subagent,
            project=project
        )

        # Add new hits (deduplicate by source)
        new_hits_count = 0
        for hit in hits:
            source = hit.get("source", "")
            if source not in seen_sources:
                all_hits.append(hit)
                seen_sources.add(source)
                new_hits_count += 1

        logger.info(f"  Found {len(hits)} results, {new_hits_count} new")

        # Check stopping criteria
        quality_hits = [h for h in all_hits if h.get("score", 0) >= min_quality_score]

        if len(quality_hits) >= min_results:
            logger.info(f"  Stopping: found {len(quality_hits)} quality results")
            break

        if iteration < max_iterations - 1:
            # Expand query for next iteration
            current_query = expand_query(
                original_query=query,
                current_results=hits,
                iteration=iteration + 1
            )

            if not current_query or current_query == query:
                logger.info("  Stopping: no new query expansion")
                break

    # Sort by score and return
    all_hits.sort(key=lambda x: x.get("score", 0), reverse=True)

    logger.info(f"Iterative search completed: {len(all_hits)} total results from {iteration + 1} iterations")

    return all_hits[:k_per_iteration * 2]  # Return up to 2x the per-iteration k


def expand_query(
    original_query: str,
    current_results: List[Dict],
    iteration: int,
    model: str = "gemini-local"  # Uses local Port 8084 Gemini proxy (OpenAI compatible)
) -> str:
    """
    Use LLM to expand the query based on current results.

    This simulates ACE's behavior where it searches for related terms
    like "fetch" → "Axios" → "api config".

    Args:
        original_query: User's original query
        current_results: Results from current iteration
        iteration: Current iteration number
        model: Model provider name (default: "requesty-gemini" -> google/gemini-2.5-flash)

    Returns:
        Expanded query string
    """
    try:
        import sys
        sys.path.insert(0, str(BASE))
        from providers.registry import get_provider, openai_chat
        from providers.system_prompts import get_query_expansion_messages

        # Get provider
        provider = get_provider(model)
        model_id = provider.get("model_id", "")

        # Build messages using system prompts config
        messages = get_query_expansion_messages(
            model_id=model_id,
            original_query=original_query,
            current_results=current_results,
            iteration=iteration
        )

        response = openai_chat(
            provider,
            messages,
            temperature=0.3,
            max_output_tokens=100
        )

        # Extract expanded query
        expanded = response.strip()

        # Validate expansion
        if not expanded or len(expanded) > 200:
            logger.warning(f"Invalid expansion: {expanded}")
            return original_query

        logger.info(f"Query expanded: '{original_query}' → '{expanded}'")
        return expanded

    except Exception as e:
        logger.error(f"Query expansion failed: {e}")
        return original_query


# _build_expansion_prompt removed - now using system_prompts.get_query_expansion_messages()


def should_use_iterative_search(query: str, task_type: str = "lookup") -> bool:
    """
    Determine if iterative search should be used.

    Args:
        query: User query
        task_type: Type of task (lookup, refactor, etc.)

    Returns:
        True if iterative search is recommended
    """
    # Use iterative search for:
    # - Complex queries (longer than 50 chars)
    # - Refactoring tasks
    # - When query mentions multiple concepts

    if task_type in ("refactor", "reason", "implement"):
        return True

    if len(query) > 50:
        return True

    # Check for multiple concepts (contains "and", "or", multiple nouns)
    import re
    connectors = len(re.findall(r'\b(and|or|以及|和|或)\b', query.lower()))
    if connectors >= 2:
        return True

    return False
