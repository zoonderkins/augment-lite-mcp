# guardrails/pii_detection.py - PII & Sensitive Data Detection
"""
Detects and masks Personally Identifiable Information (PII) and sensitive data.
Covers: emails, phones, SSN, credit cards, API keys, passwords.
"""

import re
from typing import List, Dict, Tuple

# PII patterns with named groups
PII_PATTERNS = {
    "EMAIL": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "PHONE_US": r"\b(?:\+1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    "PHONE_INTL": r"\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}",
    "SSN": r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b",
    "CREDIT_CARD": r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b",
    "IP_ADDRESS": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    "MAC_ADDRESS": r"\b([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\b",
    "DATE_OF_BIRTH": r"\b(?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b",
    "PASSPORT": r"\b[A-Z]{1,2}[0-9]{6,9}\b",
}

# API Key and Secret patterns
API_KEY_PATTERNS = {
    "OPENAI_KEY": r"sk-[A-Za-z0-9]{20,}",
    "ANTHROPIC_KEY": r"sk-ant-[A-Za-z0-9-]{20,}",
    "AWS_ACCESS_KEY": r"AKIA[0-9A-Z]{16}",
    "AWS_SECRET_KEY": r"[A-Za-z0-9/+=]{40}",
    "GITHUB_TOKEN": r"gh[pousr]_[A-Za-z0-9]{36,}",
    "STRIPE_KEY": r"(sk_live_|pk_live_|sk_test_|pk_test_)[A-Za-z0-9]{24,}",
    "GOOGLE_API_KEY": r"AIza[0-9A-Za-z_-]{35}",
    "SLACK_TOKEN": r"xox[baprs]-[0-9A-Za-z-]{10,}",
    "JWT_TOKEN": r"eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*",
    "GENERIC_API_KEY": r"(?:api[_-]?key|apikey|api_secret|secret_key)\s*[=:]\s*['\"]?([A-Za-z0-9_-]{20,})['\"]?",
    "BEARER_TOKEN": r"Bearer\s+[A-Za-z0-9_-]{20,}",
}

# Sensitivity levels
SENSITIVITY = {
    "EMAIL": "MEDIUM",
    "PHONE_US": "MEDIUM",
    "PHONE_INTL": "MEDIUM",
    "SSN": "CRITICAL",
    "CREDIT_CARD": "CRITICAL",
    "IP_ADDRESS": "LOW",
    "MAC_ADDRESS": "LOW",
    "DATE_OF_BIRTH": "MEDIUM",
    "PASSPORT": "HIGH",
    "OPENAI_KEY": "CRITICAL",
    "ANTHROPIC_KEY": "CRITICAL",
    "AWS_ACCESS_KEY": "CRITICAL",
    "AWS_SECRET_KEY": "CRITICAL",
    "GITHUB_TOKEN": "CRITICAL",
    "STRIPE_KEY": "CRITICAL",
    "GOOGLE_API_KEY": "HIGH",
    "SLACK_TOKEN": "HIGH",
    "JWT_TOKEN": "HIGH",
    "GENERIC_API_KEY": "HIGH",
    "BEARER_TOKEN": "HIGH",
}


def detect_pii(text: str) -> List[Dict]:
    """
    Detect PII in text.

    Args:
        text: Text to scan

    Returns:
        List of PII findings
    """
    if not text:
        return []

    findings = []

    # Check PII patterns
    for pii_type, pattern in PII_PATTERNS.items():
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            findings.append({
                "type": pii_type,
                "category": "PII",
                "sensitivity": SENSITIVITY.get(pii_type, "MEDIUM"),
                "value": _mask_value(match.group(), pii_type),
                "position": match.start(),
            })

    # Check API key patterns
    for key_type, pattern in API_KEY_PATTERNS.items():
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            findings.append({
                "type": key_type,
                "category": "API_KEY",
                "sensitivity": SENSITIVITY.get(key_type, "HIGH"),
                "value": _mask_value(match.group(), key_type),
                "position": match.start(),
            })

    # Sort by position
    findings.sort(key=lambda x: x["position"])
    return findings


def _mask_value(value: str, pii_type: str) -> str:
    """Mask sensitive value for safe display."""
    if len(value) <= 4:
        return "****"

    if pii_type in ["EMAIL"]:
        parts = value.split("@")
        if len(parts) == 2:
            return f"{parts[0][:2]}***@{parts[1]}"

    if pii_type in ["CREDIT_CARD", "SSN"]:
        return f"****{value[-4:]}"

    if pii_type in ["PHONE_US", "PHONE_INTL"]:
        return f"****{value[-4:]}"

    # API keys: show prefix + last 4
    if "KEY" in pii_type or "TOKEN" in pii_type:
        return f"{value[:8]}...{value[-4:]}"

    # Default: show first 2 and last 2
    return f"{value[:2]}***{value[-2:]}"


def mask_pii(text: str, mask_char: str = "*") -> str:
    """
    Mask all PII in text.

    Args:
        text: Text containing PII
        mask_char: Character to use for masking

    Returns:
        Text with PII masked
    """
    if not text:
        return ""

    result = text

    # Mask API keys first (longer patterns)
    for key_type, pattern in API_KEY_PATTERNS.items():
        result = re.sub(pattern, lambda m: mask_char * len(m.group()), result)

    # Mask PII
    for pii_type, pattern in PII_PATTERNS.items():
        result = re.sub(pattern, lambda m: mask_char * len(m.group()), result)

    return result


def should_block_pii(text: str, allow_emails: bool = False) -> Tuple[bool, str, List[Dict]]:
    """
    Determine if content should be blocked due to PII.

    Args:
        text: Text to check
        allow_emails: If True, don't block for email addresses

    Returns:
        Tuple of (should_block, reason, findings)
    """
    findings = detect_pii(text)

    if not findings:
        return False, "", []

    # Filter if emails allowed
    if allow_emails:
        findings = [f for f in findings if f["type"] != "EMAIL"]

    if not findings:
        return False, "", []

    # Check for critical findings
    critical = [f for f in findings if f["sensitivity"] == "CRITICAL"]
    if critical:
        return True, f"CRITICAL_PII: {critical[0]['type']}", findings

    # Check API keys
    api_keys = [f for f in findings if f["category"] == "API_KEY"]
    if api_keys:
        return True, f"API_KEY_EXPOSED: {api_keys[0]['type']}", findings

    # High sensitivity items
    high = [f for f in findings if f["sensitivity"] == "HIGH"]
    if len(high) >= 2:
        return True, "MULTIPLE_HIGH_PII", findings

    return False, "", findings


def get_pii_report(text: str) -> Dict:
    """
    Generate PII detection report.

    Args:
        text: Text to analyze

    Returns:
        Detailed PII report
    """
    findings = detect_pii(text)

    by_type = {}
    by_sensitivity = {}

    for f in findings:
        by_type[f["type"]] = by_type.get(f["type"], 0) + 1
        by_sensitivity[f["sensitivity"]] = by_sensitivity.get(f["sensitivity"], 0) + 1

    should_block, reason, _ = should_block_pii(text)

    return {
        "total_findings": len(findings),
        "by_type": by_type,
        "by_sensitivity": by_sensitivity,
        "should_block": should_block,
        "block_reason": reason,
        "findings": findings,
        "masked_preview": mask_pii(text)[:500] if text else "",
    }
