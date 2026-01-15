"""
Accumulated Answer Generation

Implements multi-aspect retrieval with evidence accumulation:
1. Decompose complex query into sub-queries
2. Execute multiple targeted searches
3. Accumulate evidence from all searches
4. Generate comprehensive answer with all evidence

This solves the "不知道" problem by ensuring coverage across
different aspects of a complex question.
"""

import logging
from typing import List, Dict, Optional
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

logger = logging.getLogger(__name__)


def decompose_query(
    query: str,
    model: str = "minimax-m2.1"
) -> List[str]:
    """
    Use LLM to decompose a complex query into sub-queries.

    Args:
        query: Original complex query
        model: Model for decomposition

    Returns:
        List of sub-queries covering different aspects
    """
    try:
        import sys
        sys.path.insert(0, str(BASE))
        from providers.registry import get_provider, chat

        provider = get_provider(model)

        messages = [
            {
                "role": "system",
                "content": (
                    "You decompose complex code analysis queries into specific sub-queries. "
                    "Each sub-query should target one specific aspect. "
                    "Return 3-5 sub-queries, one per line. No numbering or bullets."
                )
            },
            {
                "role": "user",
                "content": f"Decompose this query into specific search terms:\n\n{query}"
            }
        ]

        response = chat(provider, messages, temperature=0.3, max_output_tokens=300)

        # Parse response into list
        sub_queries = []
        for line in response.strip().split("\n"):
            line = line.strip()
            # Remove numbering like "1.", "1)", "-", "*"
            if line and len(line) > 5:
                cleaned = line.lstrip("0123456789.)-* ")
                if cleaned:
                    sub_queries.append(cleaned)

        # Ensure at least original query is included
        if not sub_queries:
            sub_queries = [query]

        logger.info(f"Decomposed query into {len(sub_queries)} sub-queries")
        return sub_queries[:5]  # Max 5 sub-queries

    except Exception as e:
        logger.error(f"Query decomposition failed: {e}")
        return [query]  # Fallback to original query


def accumulated_search(
    query: str,
    sub_queries: Optional[List[str]] = None,
    k_per_query: int = 5,
    use_subagent: bool = True,
    project: str = "auto"
) -> Dict:
    """
    Execute multiple searches and accumulate results.

    Args:
        query: Original query (for context)
        sub_queries: List of sub-queries (auto-generated if None)
        k_per_query: Results per sub-query
        use_subagent: Enable LLM re-ranking
        project: Project name

    Returns:
        Dict with accumulated hits and metadata
    """
    from retrieval.subagent_filter import hybrid_search_with_subagent

    # Auto-decompose if no sub-queries provided
    if not sub_queries:
        sub_queries = decompose_query(query)

    all_hits = []
    seen_sources = set()
    search_metadata = []

    for i, sub_q in enumerate(sub_queries):
        logger.info(f"Accumulated search {i+1}/{len(sub_queries)}: {sub_q[:50]}...")

        try:
            hits = hybrid_search_with_subagent(
                sub_q,
                k=k_per_query,
                use_subagent=use_subagent,
                project=project
            )

            new_count = 0
            for hit in hits:
                source = hit.get("source", "")
                if source not in seen_sources:
                    hit["_sub_query"] = sub_q
                    hit["_search_round"] = i + 1
                    all_hits.append(hit)
                    seen_sources.add(source)
                    new_count += 1

            search_metadata.append({
                "query": sub_q,
                "found": len(hits),
                "new": new_count
            })

        except Exception as e:
            logger.error(f"Sub-query search failed: {e}")
            search_metadata.append({
                "query": sub_q,
                "error": str(e)
            })

    # Sort by score
    all_hits.sort(key=lambda x: x.get("score", 0), reverse=True)

    return {
        "hits": all_hits,
        "total_unique": len(all_hits),
        "sub_queries": sub_queries,
        "search_metadata": search_metadata
    }


def generate_accumulated_answer(
    query: str,
    sub_queries: Optional[List[str]] = None,
    k_per_query: int = 5,
    route: str = "auto",
    temperature: float = 0.2,
    project: str = "auto"
) -> Dict:
    """
    Generate answer with accumulated evidence from multiple searches.

    This is the main entry point for accumulated answer generation.

    Args:
        query: User's complex question
        sub_queries: Optional pre-defined sub-queries
        k_per_query: Results per sub-query
        route: Model route (auto/small-fast/reason-large/etc)
        temperature: Generation temperature
        project: Project name

    Returns:
        Dict with answer, citations, and metadata
    """
    import sys
    sys.path.insert(0, str(BASE))
    from providers.registry import get_provider, chat
    from router import get_route_config
    from tokenizer import estimate_tokens_from_messages
    from cache import make_key, cache_get, cache_set
    from guardrails.abstain import should_abstain, get_abstain_reason

    # 1. Accumulated search
    search_result = accumulated_search(
        query=query,
        sub_queries=sub_queries,
        k_per_query=k_per_query,
        project=project
    )

    hits = search_result["hits"]

    # 2. Abstain check
    if should_abstain(hits, min_diversity=2):
        error_code = get_abstain_reason(hits, min_diversity=2)
        return {
            "ok": True,
            "answer": f"Search failed: {error_code}",
            "citations": [],
            "abstained": True,
            "search_metadata": search_result["search_metadata"]
        }

    # 3. Build evidence from accumulated hits
    # Take more hits since we have accumulated from multiple searches
    top_hits = hits[:12]  # More evidence for comprehensive answer

    system_prompt = (
        "You answer based ONLY on the provided Evidence. "
        "After each key conclusion, cite the source as [source:<file:line>]. "
        "If evidence is insufficient for any aspect, clearly state what is missing. "
        "Structure your answer with clear sections matching the query aspects."
    )

    evidence = "\n\n".join([
        f"[{h['source']}] (round {h.get('_search_round', '?')})\n{h['text']}"
        for h in top_hits
    ])

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"# Query\n{query}\n\n# Evidence\n{evidence}"},
    ]

    # 4. Route selection
    total_tokens = estimate_tokens_from_messages(messages)
    route_config = get_route_config("reason", total_tokens, route_override=route)
    model_alias = route_config["model"]
    max_output_tokens = route_config["max_output_tokens"]

    # 5. Cache check
    key = make_key(
        model=model_alias,
        messages=messages,
        extra={"temperature": temperature, "accumulated": True},
        project=project
    )
    cached = cache_get(key)
    if cached:
        return {"ok": True, **cached, "cached": True, "search_metadata": search_result["search_metadata"]}

    # 6. Generate answer
    provider = get_provider(model_alias)
    answer = chat(
        provider,
        messages,
        temperature=temperature,
        max_output_tokens=max_output_tokens
    )

    # 7. Build response
    payload = {
        "answer": answer,
        "citations": [h["source"] for h in top_hits]
    }
    cache_set(key, payload, ttl_sec=7200)

    return {
        "ok": True,
        **payload,
        "cached": False,
        "sub_queries": search_result["sub_queries"],
        "search_metadata": search_result["search_metadata"],
        "evidence_count": len(top_hits)
    }
