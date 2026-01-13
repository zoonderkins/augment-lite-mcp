# guardrails/context_grounding.py - Context Grounding Validation
"""
Ensures LLM responses are grounded in provided context.
Validates that answers don't go beyond the evidence.
"""

import re
from typing import List, Dict, Tuple, Optional
from difflib import SequenceMatcher


def extract_key_terms(text: str) -> set:
    """Extract significant terms from text."""
    if not text:
        return set()

    # Extract words 4+ chars, exclude common stopwords
    words = set(re.findall(r'\b[a-zA-Z]{4,}\b', text.lower()))

    stopwords = {
        'this', 'that', 'these', 'those', 'have', 'been', 'were', 'will',
        'would', 'could', 'should', 'about', 'with', 'from', 'into', 'through',
        'during', 'before', 'after', 'above', 'below', 'between', 'under',
        'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where',
        'which', 'while', 'other', 'some', 'such', 'only', 'same', 'than',
        'very', 'just', 'also', 'more', 'most', 'being', 'having', 'doing',
    }

    return words - stopwords


def calculate_grounding_score(response: str, context: str) -> float:
    """
    Calculate how well response is grounded in context.

    Args:
        response: LLM response text
        context: Provided context/evidence

    Returns:
        Grounding score 0.0-1.0
    """
    if not response or not context:
        return 0.0

    response_terms = extract_key_terms(response)
    context_terms = extract_key_terms(context)

    if not response_terms:
        return 1.0  # No specific terms = vacuously grounded

    # Calculate term overlap
    overlap = response_terms & context_terms
    coverage = len(overlap) / len(response_terms)

    # Sequence similarity for phrases
    seq_score = SequenceMatcher(None, response.lower(), context.lower()).ratio()

    # Combined score (weighted)
    score = coverage * 0.7 + seq_score * 0.3

    return round(min(score, 1.0), 2)


def find_ungrounded_segments(response: str, context: str, window_size: int = 50) -> List[Dict]:
    """
    Find segments of response not grounded in context.

    Args:
        response: LLM response
        context: Provided context
        window_size: Size of text windows to check

    Returns:
        List of ungrounded segments
    """
    if not response or not context:
        return []

    ungrounded = []
    context_lower = context.lower()

    # Split response into sentences
    sentences = re.split(r'[.!?]\s+', response)

    for i, sentence in enumerate(sentences):
        if len(sentence) < 15:
            continue

        sentence_lower = sentence.lower()

        # Check if sentence content appears in context
        terms = extract_key_terms(sentence)

        if not terms:
            continue

        context_terms = extract_key_terms(context)
        overlap = terms & context_terms
        coverage = len(overlap) / len(terms) if terms else 0

        # Check sequence similarity
        best_sim = 0.0
        for j in range(0, len(context) - window_size, window_size // 2):
            window = context_lower[j:j + window_size]
            sim = SequenceMatcher(None, sentence_lower[:window_size], window).ratio()
            best_sim = max(best_sim, sim)

        # Ungrounded if low coverage AND low similarity
        if coverage < 0.3 and best_sim < 0.3:
            ungrounded.append({
                "sentence": sentence[:200],
                "position": i,
                "term_coverage": round(coverage, 2),
                "best_similarity": round(best_sim, 2),
            })

    return ungrounded


def validate_grounding(
    response: str,
    context: str,
    min_score: float = 0.4
) -> Tuple[bool, str, float]:
    """
    Validate that response is adequately grounded.

    Args:
        response: LLM response
        context: Provided context
        min_score: Minimum grounding score required

    Returns:
        Tuple of (is_valid, reason, score)
    """
    if not response:
        return True, "", 1.0

    if not context:
        return False, "NO_CONTEXT_PROVIDED", 0.0

    score = calculate_grounding_score(response, context)

    if score < min_score:
        return False, "LOW_GROUNDING_SCORE", score

    # Check for ungrounded segments
    ungrounded = find_ungrounded_segments(response, context)

    if len(ungrounded) > 3:
        return False, "MULTIPLE_UNGROUNDED_SEGMENTS", score

    return True, "", score


def enforce_grounding(
    response: str,
    context: str,
    citations: Optional[List[str]] = None
) -> Dict:
    """
    Enforce grounding requirements and generate report.

    Args:
        response: LLM response
        context: Provided context
        citations: Optional list of citations in response

    Returns:
        Grounding enforcement report
    """
    score = calculate_grounding_score(response, context)
    ungrounded = find_ungrounded_segments(response, context)
    is_valid, reason, _ = validate_grounding(response, context)

    # Check citation coverage if provided
    citation_score = 0.0
    if citations:
        cited_terms = set()
        for cite in citations:
            cited_terms.update(extract_key_terms(cite))

        response_terms = extract_key_terms(response)
        if response_terms:
            citation_score = len(cited_terms & response_terms) / len(response_terms)

    return {
        "grounding_score": score,
        "is_valid": is_valid,
        "validation_reason": reason,
        "ungrounded_segments": len(ungrounded),
        "segments": ungrounded[:5],
        "citation_coverage": round(citation_score, 2) if citations else None,
        "recommendation": _get_recommendation(score, len(ungrounded), is_valid),
    }


def _get_recommendation(score: float, ungrounded_count: int, is_valid: bool) -> str:
    """Generate recommendation based on grounding analysis."""
    if is_valid and score >= 0.7:
        return "ACCEPT"

    if not is_valid:
        if ungrounded_count > 5:
            return "REJECT_UNGROUNDED"
        return "REVIEW_REQUIRED"

    if score < 0.3:
        return "REJECT_LOW_GROUNDING"

    return "REVIEW_REQUIRED"
