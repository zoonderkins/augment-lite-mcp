# guardrails/code_security.py - Code Security Scanning
"""
Detects security vulnerabilities in code.
Patterns loaded from external config to avoid scanner false positives.
"""

import re
import os
from typing import List, Tuple, Dict
from pathlib import Path

SEVERITY_WEIGHTS = {"CRITICAL": 1.0, "HIGH": 0.8, "MEDIUM": 0.5, "LOW": 0.3}


def _load_patterns_from_config() -> Dict[str, List[Tuple[str, str, str]]]:
    """Load vulnerability patterns from config file."""
    config_path = Path(__file__).parent / "security_patterns.txt"

    if not config_path.exists():
        # Return minimal built-in patterns
        return {
            "SQL_INJECTION": [
                (r"SELECT.*WHERE.*\+", "SQL concatenation", "HIGH"),
            ],
            "PATH_TRAVERSAL": [
                (r"\.\./", "directory traversal", "HIGH"),
            ],
            "SENSITIVE_DATA": [
                (r"(sk-|pk_live_)[A-Za-z0-9]{20,}", "API key exposed", "CRITICAL"),
            ],
        }

    patterns = {}
    current_category = None

    with open(config_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('[') and line.endswith(']'):
                current_category = line[1:-1]
                patterns[current_category] = []
            elif current_category and '|' in line:
                parts = line.split('|')
                if len(parts) >= 3:
                    patterns[current_category].append((parts[0], parts[1], parts[2]))

    return patterns


def scan_code(code: str, language: str = "auto") -> List[Dict]:
    """Scan code for security vulnerabilities."""
    if not code:
        return []

    findings = []
    patterns = _load_patterns_from_config()

    for category, pattern_list in patterns.items():
        for pattern, description, severity in pattern_list:
            try:
                for match in re.finditer(pattern, code, re.IGNORECASE | re.MULTILINE):
                    line_num = code[:match.start()].count('\n') + 1
                    findings.append({
                        "category": category,
                        "severity": severity,
                        "description": description,
                        "line": line_num,
                        "match": match.group()[:80],
                    })
            except re.error:
                pass

    findings.sort(key=lambda x: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2}.get(x["severity"], 3))
    return findings


def calculate_risk_score(findings: List[Dict]) -> float:
    """Calculate risk score (0.0-1.0)."""
    if not findings:
        return 0.0
    total = sum(SEVERITY_WEIGHTS.get(f["severity"], 0) for f in findings)
    return min(round(total / 3.0, 2), 1.0)


def should_block_code(code: str, threshold: float = 0.7) -> Tuple[bool, str, float]:
    """Check if code should be blocked."""
    findings = scan_code(code)
    if not findings:
        return False, "", 0.0

    risk = calculate_risk_score(findings)
    critical = [f for f in findings if f["severity"] == "CRITICAL"]

    if critical:
        return True, f"CRITICAL: {critical[0]['description']}", risk
    if risk >= threshold:
        return True, f"{findings[0]['severity']}: {findings[0]['description']}", risk

    return False, "", risk


def get_security_report(code: str) -> Dict:
    """Generate security report."""
    findings = scan_code(code)
    risk = calculate_risk_score(findings)

    by_severity = {}
    for f in findings:
        by_severity[f["severity"]] = by_severity.get(f["severity"], 0) + 1

    return {
        "risk_score": risk,
        "total_findings": len(findings),
        "by_severity": by_severity,
        "findings": findings[:20],
        "should_block": risk >= 0.7 or by_severity.get("CRITICAL", 0) > 0,
    }
