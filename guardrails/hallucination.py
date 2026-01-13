# guardrails/hallucination.py - Hallucination Detection
"""
Detects potential hallucinations in LLM responses.
Verifies claims are grounded in provided evidence.
"""

import re
from typing import List, Dict, Tuple, Set
from difflib import SequenceMatcher


def extract_claims(response: str) -> List[str]:
    """
    Extract factual claims from LLM response.

    Args:
        response: LLM response text

    Returns:
        List of extracted claims
    """
    if not response:
        return []

    claims = []

    # Split into sentences
    sentences = re.split(r'[.!?]\s+', response)

    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 10:
            continue

        # Skip meta-statements
        skip_patterns = [
            r"^(I |Based on|According to|The evidence|As shown)",
            r"^(Let me|I'll |I can|I don't|I cannot)",
            r"^(Here|This|That|These|Those)\s+(is|are|shows?)",
        ]

        if any(re.match(p, sentence, re.IGNORECASE) for p in skip_patterns):
            continue

        # Detect factual claims (contains specific details)
        factual_indicators = [
            r"\d+",  # Numbers
            r"(is|are|was|were|has|have|does|do)\s+\w+",  # Assertions
            r"(will|can|must|should)\s+\w+",  # Predictions
            r"\"[^\"]+\"",  # Quoted content
            r"\b(always|never|all|none|every)\b",  # Absolute statements
        ]

        if any(re.search(p, sentence) for p in factual_indicators):
            claims.append(sentence)

    return claims


def check_grounding(claim: str, evidence: List[str], threshold: float = 0.4) -> Tuple[bool, float, str]:
    """
    Check if a claim is grounded in evidence.

    Args:
        claim: The claim to verify
        evidence: List of evidence texts
        threshold: Minimum similarity for grounding

    Returns:
        Tuple of (is_grounded, best_score, best_match)
    """
    if not claim or not evidence:
        return False, 0.0, ""

    claim_lower = claim.lower()
    best_score = 0.0
    best_match = ""

    for ev in evidence:
        if not ev:
            continue

        ev_lower = ev.lower()

        # Method 1: Sequence matching
        seq_score = SequenceMatcher(None, claim_lower, ev_lower).ratio()

        # Method 2: Key term overlap
        claim_words = set(re.findall(r'\b\w{4,}\b', claim_lower))
        ev_words = set(re.findall(r'\b\w{4,}\b', ev_lower))

        if claim_words:
            overlap = len(claim_words & ev_words) / len(claim_words)
        else:
            overlap = 0.0

        # Combined score
        score = max(seq_score, overlap * 0.8)

        if score > best_score:
            best_score = score
            best_match = ev[:200]

    return best_score >= threshold, best_score, best_match


def detect_hallucinations(
    response: str,
    evidence: List[str],
    strict: bool = False
) -> List[Dict]:
    """
    Detect potential hallucinations in response.

    Args:
        response: LLM response to check
        evidence: List of evidence/context provided
        strict: If True, use stricter grounding threshold

    Returns:
        List of potential hallucinations
    """
    if not response:
        return []

    claims = extract_claims(response)
    threshold = 0.5 if strict else 0.35

    hallucinations = []

    for claim in claims:
        is_grounded, score, match = check_grounding(claim, evidence, threshold)

        if not is_grounded:
            hallucinations.append({
                "claim": claim[:200],
                "grounding_score": round(score, 2),
                "closest_evidence": match[:100] if match else "",
                "confidence": round(1.0 - score, 2),
            })

    # Sort by confidence (most likely hallucinations first)
    hallucinations.sort(key=lambda x: x["confidence"], reverse=True)

    return hallucinations


def should_flag_response(
    response: str,
    evidence: List[str],
    max_hallucinations: int = 2,
    min_confidence: float = 0.7
) -> Tuple[bool, str, List[Dict]]:
    """
    Determine if response should be flagged for hallucinations.

    Args:
        response: LLM response
        evidence: Evidence provided
        max_hallucinations: Max allowed ungrounded claims
        min_confidence: Min confidence to count as hallucination

    Returns:
        Tuple of (should_flag, reason, hallucinations)
    """
    hallucinations = detect_hallucinations(response, evidence)

    # Filter by confidence
    high_confidence = [h for h in hallucinations if h["confidence"] >= min_confidence]

    if len(high_confidence) > max_hallucinations:
        return True, f"UNGROUNDED_CLAIMS: {len(high_confidence)} detected", hallucinations

    # Check for absolute statements without evidence
    absolute_patterns = [
        r"\b(always|never|all|none|every|impossible|certain)\b",
    ]

    for pattern in absolute_patterns:
        if re.search(pattern, response, re.IGNORECASE):
            # Check if any absolute claim is ungrounded
            for h in hallucinations:
                if re.search(pattern, h["claim"], re.IGNORECASE):
                    return True, "UNGROUNDED_ABSOLUTE_CLAIM", hallucinations

    return False, "", hallucinations


def get_hallucination_report(response: str, evidence: List[str]) -> Dict:
    """
    Generate hallucination detection report.

    Args:
        response: LLM response
        evidence: Evidence provided

    Returns:
        Detailed hallucination report
    """
    claims = extract_claims(response)
    hallucinations = detect_hallucinations(response, evidence)
    should_flag, reason, _ = should_flag_response(response, evidence)

    grounded_count = len(claims) - len(hallucinations)

    return {
        "total_claims": len(claims),
        "grounded_claims": grounded_count,
        "potential_hallucinations": len(hallucinations),
        "grounding_rate": round(grounded_count / max(len(claims), 1), 2),
        "should_flag": should_flag,
        "flag_reason": reason,
        "hallucinations": hallucinations[:10],
    }
