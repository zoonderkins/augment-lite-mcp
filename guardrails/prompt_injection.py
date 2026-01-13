# guardrails/prompt_injection.py - Prompt Injection Detection
"""
Detects and blocks prompt injection attacks.
Common patterns: instruction override, role hijacking, delimiter abuse.
"""

import re
from typing import Tuple

# Known injection patterns (regex)
INJECTION_PATTERNS = [
    # Instruction override attempts
    (r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|rules?)", "INSTRUCTION_OVERRIDE"),
    (r"disregard\s+(all\s+)?(previous|above|prior)", "INSTRUCTION_OVERRIDE"),
    (r"forget\s+(everything|all|what)\s+(you|i)\s+(told|said)", "INSTRUCTION_OVERRIDE"),

    # Role hijacking
    (r"you\s+are\s+now\s+(a|an|the)\s+", "ROLE_HIJACK"),
    (r"pretend\s+(to\s+be|you\s+are)\s+", "ROLE_HIJACK"),
    (r"act\s+as\s+(if\s+you\s+are|a|an)\s+", "ROLE_HIJACK"),
    (r"from\s+now\s+on[,\s]+(you|your)\s+", "ROLE_HIJACK"),

    # System prompt extraction
    (r"(show|reveal|display|print|output)\s+(your|the)\s+(system\s+)?(prompt|instructions?)", "PROMPT_LEAK"),
    (r"what\s+(are|is)\s+your\s+(system\s+)?(prompt|instructions?)", "PROMPT_LEAK"),
    (r"repeat\s+(your|the)\s+(initial|system|original)\s+", "PROMPT_LEAK"),

    # Delimiter injection
    (r"```\s*system\s*\n", "DELIMITER_INJECT"),
    (r"\[INST\]|\[/INST\]", "DELIMITER_INJECT"),
    (r"<\|im_start\|>|<\|im_end\|>", "DELIMITER_INJECT"),
    (r"<<SYS>>|<</SYS>>", "DELIMITER_INJECT"),
    (r"Human:|Assistant:|System:", "DELIMITER_INJECT"),

    # Jailbreak attempts
    (r"DAN\s*mode|do\s+anything\s+now", "JAILBREAK"),
    (r"developer\s+mode\s+(enabled|activated|on)", "JAILBREAK"),
    (r"(enable|activate|turn\s+on)\s+(evil|unrestricted|unfiltered)\s+mode", "JAILBREAK"),

    # Code execution attempts
    (r"execute\s+(this|the\s+following)\s+(code|script|command)", "CODE_EXEC"),
    (r"run\s+(this|the)\s+(python|bash|shell|code)", "CODE_EXEC"),
    (r"eval\s*\(|exec\s*\(", "CODE_EXEC"),
]

# Suspicious character sequences
SUSPICIOUS_SEQUENCES = [
    ("\x00", "NULL_BYTE"),
    ("\x1b[", "ANSI_ESCAPE"),
    ("${", "VAR_EXPANSION"),
    ("$(", "CMD_SUBSTITUTION"),
]


def detect_prompt_injection(text: str, strict: bool = False) -> Tuple[bool, str, float]:
    """
    Detect prompt injection attempts in user input.

    Args:
        text: User input text to analyze
        strict: If True, use stricter detection (more false positives)

    Returns:
        Tuple of (is_injection, reason_code, confidence)
        - is_injection: True if injection detected
        - reason_code: Short code describing the attack type
        - confidence: 0.0-1.0 confidence score
    """
    if not text:
        return False, "", 0.0

    text_lower = text.lower()

    # Check suspicious character sequences (high confidence)
    for seq, reason in SUSPICIOUS_SEQUENCES:
        if seq in text:
            return True, reason, 0.95

    # Check regex patterns
    for pattern, reason in INJECTION_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            confidence = 0.85 if strict else 0.75
            return True, reason, confidence

    # Heuristic checks
    scores = []

    # Many special delimiters
    delimiter_count = sum(text.count(d) for d in ['```', '"""', "'''", '###', '---'])
    if delimiter_count > 5:
        scores.append(("EXCESSIVE_DELIMITERS", 0.5 + min(delimiter_count * 0.05, 0.3)))

    # Unusual capitalization patterns (e.g., "IGNORE ALL")
    caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
    if caps_ratio > 0.5 and len(text) > 20:
        scores.append(("CAPS_SHOUTING", 0.4))

    # Very long input (potential payload)
    if len(text) > 10000:
        scores.append(("EXCESSIVE_LENGTH", 0.3))

    # Return highest confidence detection
    if scores:
        scores.sort(key=lambda x: x[1], reverse=True)
        reason, confidence = scores[0]
        if confidence >= (0.6 if strict else 0.7):
            return True, reason, confidence

    return False, "", 0.0


def sanitize_input(text: str) -> str:
    """
    Sanitize user input by removing/escaping dangerous patterns.
    Use this as a fallback when blocking is too aggressive.

    Args:
        text: User input to sanitize

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Remove null bytes and control characters
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    # Escape common delimiters that could be used for injection
    replacements = [
        ('```system', '` ` `system'),
        ('[INST]', '[_INST_]'),
        ('[/INST]', '[/_INST_]'),
        ('<|im_start|>', '<_im_start_>'),
        ('<|im_end|>', '<_im_end_>'),
    ]

    for old, new in replacements:
        text = text.replace(old, new)

    return text


def get_injection_report(text: str) -> dict:
    """
    Generate detailed injection analysis report.

    Args:
        text: Text to analyze

    Returns:
        Dict with analysis results
    """
    is_injection, reason, confidence = detect_prompt_injection(text, strict=True)

    report = {
        "is_injection": is_injection,
        "reason": reason,
        "confidence": confidence,
        "text_length": len(text),
        "patterns_matched": [],
    }

    # Find all matching patterns for detailed report
    if text:
        text_lower = text.lower()
        for pattern, reason_code in INJECTION_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                report["patterns_matched"].append(reason_code)

    return report
