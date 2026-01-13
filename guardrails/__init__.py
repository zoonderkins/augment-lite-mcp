# guardrails/__init__.py - Guardrails Module
"""
Modern guardrails for LLM applications (2026).

Modules:
- abstain: Result quality checking
- prompt_injection: Detect prompt injection attacks
- pii_detection: PII and API key detection
- code_security: Code vulnerability scanning
- hallucination: Hallucination detection
- context_grounding: Response grounding validation
- schema_validation: Output schema validation
"""

from .abstain import should_abstain, get_abstain_reason, suggest_query_improvements
from .prompt_injection import detect_prompt_injection, sanitize_input, get_injection_report
from .pii_detection import detect_pii, mask_pii, should_block_pii, get_pii_report
from .code_security import scan_code, should_block_code, get_security_report
from .hallucination import detect_hallucinations, should_flag_response, get_hallucination_report
from .context_grounding import validate_grounding, enforce_grounding, calculate_grounding_score
from .schema_validation import validate_output, validate_json_output, validate_mcp_output

__all__ = [
    # Abstain
    "should_abstain",
    "get_abstain_reason",
    "suggest_query_improvements",
    # Prompt Injection
    "detect_prompt_injection",
    "sanitize_input",
    "get_injection_report",
    # PII Detection
    "detect_pii",
    "mask_pii",
    "should_block_pii",
    "get_pii_report",
    # Code Security
    "scan_code",
    "should_block_code",
    "get_security_report",
    # Hallucination
    "detect_hallucinations",
    "should_flag_response",
    "get_hallucination_report",
    # Context Grounding
    "validate_grounding",
    "enforce_grounding",
    "calculate_grounding_score",
    # Schema Validation
    "validate_output",
    "validate_json_output",
    "validate_mcp_output",
]
