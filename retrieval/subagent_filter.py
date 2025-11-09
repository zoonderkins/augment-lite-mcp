"""
Subagent filtering layer for improving retrieval relevance.

This module implements ACE-like two-stage retrieval:
1. Initial search returns candidates (k*3)
2. Fast LLM re-ranks candidates based on query relevance
"""

from pathlib import Path
import json
import logging
from typing import List, Dict, Optional

BASE = Path(__file__).resolve().parents[1]

logger = logging.getLogger(__name__)


def subagent_filter(
    query: str,
    candidates: List[Dict],
    max_results: int = 8,
    model: str = "gemini-local",  # Uses local Port 8084 Gemini proxy (OpenAI compatible)
    use_llm: bool = True
) -> List[Dict]:
    """
    Use a fast LLM to filter and re-rank search candidates.

    This implements the core ACE optimization: instead of returning
    raw search results, we use a cheap/fast model to evaluate
    which candidates are truly relevant to the user query.

    Args:
        query: User's original query
        candidates: Search results from hybrid_search
        max_results: Number of results to return
        model: Model provider name (default: "requesty-gemini" -> google/gemini-2.5-flash)
        use_llm: If False, skip LLM filtering (for testing)

    Returns:
        Filtered and re-ranked list of results
    """
    if not candidates:
        return []

    # If disabled or candidates <= max_results, return as-is
    if not use_llm or len(candidates) <= max_results:
        return candidates[:max_results]

    try:
        # Lazy import to avoid circular dependencies
        import sys
        sys.path.insert(0, str(BASE))
        from providers.registry import get_provider, openai_chat
        from providers.system_prompts import get_subagent_filter_messages

        # Get provider
        provider = get_provider(model)
        model_id = provider.get("model_id", "")

        # Build messages using system prompts config
        messages = get_subagent_filter_messages(
            model_id=model_id,
            query=query,
            candidates=candidates,
            max_results=max_results
        )

        response = openai_chat(
            provider,
            messages,
            temperature=0.1,  # Low temperature for consistency
            max_output_tokens=500
        )

        # Parse response to get selected indices
        selected_indices = _parse_selection_response(response, len(candidates))

        if not selected_indices:
            logger.warning("Subagent filter returned no results, falling back to original ranking")
            return candidates[:max_results]

        # Return selected candidates
        return [candidates[i] for i in selected_indices if i < len(candidates)][:max_results]

    except Exception as e:
        logger.error(f"Subagent filtering failed: {e}, falling back to original ranking")
        return candidates[:max_results]


# _build_filtering_prompt removed - now using system_prompts.get_subagent_filter_messages()


def _parse_selection_response(response: str, max_index: int) -> List[int]:
    """
    Parse the LLM response to extract selected indices.

    Args:
        response: LLM response text
        max_index: Maximum valid index

    Returns:
        List of selected indices
    """
    # Try to extract numbers from response
    import re

    # Clean response
    response = response.strip()

    # Try to find comma-separated numbers
    numbers = re.findall(r'\d+', response)

    if not numbers:
        logger.warning(f"Could not parse selection response: {response}")
        return []

    # Convert to integers and filter valid indices
    indices = []
    for num_str in numbers:
        try:
            idx = int(num_str)
            if 0 <= idx < max_index:
                if idx not in indices:  # Avoid duplicates
                    indices.append(idx)
        except ValueError:
            continue

    return indices


def hybrid_search_with_subagent(
    query: str,
    k: int = 8,
    bm25_weight: float = 0.5,
    vector_weight: float = 0.5,
    use_vector: bool = True,
    use_subagent: bool = True,
    subagent_model: str = "gemini-local",  # Uses local Port 8084 Gemini proxy (OpenAI compatible)
    project: str = "auto"
) -> List[Dict]:
    """
    Enhanced hybrid search with subagent filtering.

    This is the main entry point that combines:
    1. Hybrid retrieval (BM25 + vector)
    2. Subagent filtering (LLM re-ranking)

    Args:
        query: Query text
        k: Number of final results
        bm25_weight: BM25 score weight
        vector_weight: Vector score weight
        use_vector: Enable vector search
        use_subagent: Enable subagent filtering
        subagent_model: Model for subagent filtering
        project: Project name

    Returns:
        Filtered and ranked results
    """
    # Import hybrid_search
    from retrieval.search import hybrid_search

    # Step 1: Get more candidates than needed
    candidate_multiplier = 3 if use_subagent else 1
    candidates = hybrid_search(
        query,
        k=k * candidate_multiplier,
        bm25_weight=bm25_weight,
        vector_weight=vector_weight,
        use_vector=use_vector,
        project=project
    )

    if not use_subagent:
        return candidates[:k]

    # Step 2: Apply subagent filtering
    filtered = subagent_filter(
        query=query,
        candidates=candidates,
        max_results=k,
        model=subagent_model,
        use_llm=True
    )

    return filtered
