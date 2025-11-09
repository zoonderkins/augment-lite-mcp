def should_abstain(
    hits,
    min_hits: int = 1,
    min_score: float = 0.1,
    min_diversity: int = 1,
    min_avg_score: float = 0.05
):
    """
    Enhanced guardrails to determine if we should abstain from answering.

    Args:
        hits: Search results
        min_hits: Minimum number of results required
        min_score: Minimum score for best result
        min_diversity: Minimum number of unique source files
        min_avg_score: Minimum average score across all results

    Returns:
        True if we should abstain (results insufficient)
    """
    # Check 1: Basic result count
    if not hits or len(hits) < min_hits:
        return True

    # Check 2: Best result quality
    if max(h.get("score", 0.0) for h in hits) < min_score:
        return True

    # Check 3: Result diversity (avoid all results from same file)
    unique_sources = set(h.get("source", "") for h in hits)
    if len(unique_sources) < min_diversity:
        return True

    # Check 4: Average quality (avoid low-quality bulk results)
    avg_score = sum(h.get("score", 0.0) for h in hits) / len(hits)
    if avg_score < min_avg_score:
        return True

    return False


def get_abstain_reason(
    hits,
    min_hits: int = 1,
    min_score: float = 0.1,
    min_diversity: int = 1,
    min_avg_score: float = 0.05
) -> str:
    """
    Get concise abstain reason code.

    Returns short error code for LLM consumption.
    Detailed diagnostics are logged to stderr separately.
    """
    import sys

    # Detailed diagnostics go to stderr (for developers/logs)
    def _log_detail(msg: str):
        print(f"[ABSTAIN] {msg}", file=sys.stderr)

    if not hits:
        _log_detail("No relevant code found. Try different keywords or provide more context.")
        return "NO_RESULTS"

    if len(hits) < min_hits:
        _log_detail(f"Insufficient results: {len(hits)} found, {min_hits} required. Try broader search terms.")
        return "INSUFFICIENT_RESULTS"

    max_score = max(h.get("score", 0.0) for h in hits)
    if max_score < min_score:
        _log_detail(f"Low relevance: max score {max_score:.2f} < threshold {min_score:.2f}. Refine query.")
        return "LOW_RELEVANCE"

    unique_sources = set(h.get("source", "") for h in hits)
    if len(unique_sources) < min_diversity:
        _log_detail(f"Low diversity: {len(unique_sources)} unique files. Try more specific query.")
        return "LOW_DIVERSITY"

    avg_score = sum(h.get("score", 0.0) for h in hits) / len(hits)
    if avg_score < min_avg_score:
        _log_detail(f"Low average quality: {avg_score:.2f} < threshold {min_avg_score:.2f}.")
        return "LOW_QUALITY"

    _log_detail("Results insufficient for high-quality answer.")
    return "INSUFFICIENT_QUALITY"


def suggest_query_improvements(query: str, hits):
    """
    Log query improvement suggestions to stderr.

    Args:
        query: Original query
        hits: Search results (possibly insufficient)

    Returns:
        None - suggestions are logged, not returned (to save tokens)
    """
    import sys

    suggestions = []

    # Analyze query
    query_len = len(query)
    query_words = query.split()

    if query_len < 10:
        suggestions.append("• Query too short - provide more context or specific requirements")

    if len(query_words) == 1:
        suggestions.append("• Use multiple keywords to improve search accuracy")

    # Analyze results
    if hits:
        # Check if results are low quality
        avg_score = sum(h.get("score", 0.0) for h in hits) / len(hits)
        if avg_score < 0.2:
            suggestions.append("• Low keyword match - try synonyms or related terms")

        # Check diversity
        unique_sources = set(h.get("source", "") for h in hits)
        if len(unique_sources) < 2 and len(hits) > 2:
            suggestions.append("• Results concentrated in few files - need more specific function/module names")

    if not suggestions:
        suggestions.append("• Try using actual file names, function names, or class names from codebase")
        suggestions.append("• Describe specific functionality rather than abstract concepts")

    # Log to stderr only
    if suggestions:
        print("[SUGGESTIONS]", file=sys.stderr)
        for s in suggestions:
            print(f"  {s}", file=sys.stderr)