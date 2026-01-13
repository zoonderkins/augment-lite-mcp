# guardrails/schema_validation.py - Output Schema Validation
"""
Validates LLM outputs against expected schemas.
Ensures structured responses meet format requirements.
"""

import re
import json
from typing import Any, Dict, List, Optional, Tuple, Union


def validate_json_output(output: str) -> Tuple[bool, str, Optional[Dict]]:
    """
    Validate that output is valid JSON.

    Args:
        output: String that should be JSON

    Returns:
        Tuple of (is_valid, error_message, parsed_json)
    """
    if not output:
        return False, "EMPTY_OUTPUT", None

    # Try to extract JSON from markdown code blocks
    json_match = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', output)
    if json_match:
        output = json_match.group(1)

    # Clean common issues
    output = output.strip()

    try:
        parsed = json.loads(output)
        return True, "", parsed
    except json.JSONDecodeError as e:
        return False, f"INVALID_JSON: {str(e)[:100]}", None


def validate_schema(data: Any, schema: Dict) -> Tuple[bool, List[str]]:
    """
    Validate data against a simple schema.

    Schema format:
    {
        "type": "object",
        "required": ["field1", "field2"],
        "properties": {
            "field1": {"type": "string"},
            "field2": {"type": "number"},
            "field3": {"type": "array", "items": {"type": "string"}}
        }
    }

    Args:
        data: Data to validate
        schema: Schema definition

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    expected_type = schema.get("type")

    # Type checking
    type_map = {
        "string": str,
        "number": (int, float),
        "integer": int,
        "boolean": bool,
        "array": list,
        "object": dict,
        "null": type(None),
    }

    if expected_type:
        expected_python_type = type_map.get(expected_type)
        if expected_python_type and not isinstance(data, expected_python_type):
            errors.append(f"TYPE_MISMATCH: expected {expected_type}, got {type(data).__name__}")
            return False, errors

    # Object validation
    if expected_type == "object" and isinstance(data, dict):
        # Required fields
        required = schema.get("required", [])
        for field in required:
            if field not in data:
                errors.append(f"MISSING_REQUIRED: {field}")

        # Property validation
        properties = schema.get("properties", {})
        for prop_name, prop_schema in properties.items():
            if prop_name in data:
                is_valid, prop_errors = validate_schema(data[prop_name], prop_schema)
                if not is_valid:
                    errors.extend([f"{prop_name}.{e}" for e in prop_errors])

    # Array validation
    if expected_type == "array" and isinstance(data, list):
        items_schema = schema.get("items")
        if items_schema:
            for i, item in enumerate(data):
                is_valid, item_errors = validate_schema(item, items_schema)
                if not is_valid:
                    errors.extend([f"[{i}].{e}" for e in item_errors])

        # Min/max items
        min_items = schema.get("minItems", 0)
        max_items = schema.get("maxItems", float('inf'))

        if len(data) < min_items:
            errors.append(f"ARRAY_TOO_SHORT: min {min_items}, got {len(data)}")
        if len(data) > max_items:
            errors.append(f"ARRAY_TOO_LONG: max {max_items}, got {len(data)}")

    # String validation
    if expected_type == "string" and isinstance(data, str):
        min_length = schema.get("minLength", 0)
        max_length = schema.get("maxLength", float('inf'))
        pattern = schema.get("pattern")

        if len(data) < min_length:
            errors.append(f"STRING_TOO_SHORT: min {min_length}")
        if len(data) > max_length:
            errors.append(f"STRING_TOO_LONG: max {max_length}")
        if pattern and not re.match(pattern, data):
            errors.append(f"PATTERN_MISMATCH: {pattern}")

    # Number validation
    if expected_type in ("number", "integer") and isinstance(data, (int, float)):
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")

        if minimum is not None and data < minimum:
            errors.append(f"NUMBER_TOO_SMALL: min {minimum}")
        if maximum is not None and data > maximum:
            errors.append(f"NUMBER_TOO_LARGE: max {maximum}")

    # Enum validation
    enum_values = schema.get("enum")
    if enum_values and data not in enum_values:
        errors.append(f"INVALID_ENUM: expected one of {enum_values}")

    return len(errors) == 0, errors


def validate_output(output: str, schema: Dict) -> Tuple[bool, str, List[str]]:
    """
    Validate LLM output against schema.

    Args:
        output: LLM output string
        schema: Expected schema

    Returns:
        Tuple of (is_valid, status, errors)
    """
    # First validate JSON
    is_json_valid, json_error, parsed = validate_json_output(output)

    if not is_json_valid:
        return False, "INVALID_JSON", [json_error]

    # Then validate schema
    is_schema_valid, schema_errors = validate_schema(parsed, schema)

    if not is_schema_valid:
        return False, "SCHEMA_VIOLATION", schema_errors

    return True, "VALID", []


# Common schemas for MCP tools
COMMON_SCHEMAS = {
    "rag_search_result": {
        "type": "object",
        "required": ["ok", "hits"],
        "properties": {
            "ok": {"type": "boolean"},
            "hits": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["text", "source", "score"],
                    "properties": {
                        "text": {"type": "string"},
                        "source": {"type": "string"},
                        "score": {"type": "number", "minimum": 0, "maximum": 1},
                    }
                }
            }
        }
    },
    "answer_generate_result": {
        "type": "object",
        "required": ["ok", "answer"],
        "properties": {
            "ok": {"type": "boolean"},
            "answer": {"type": "string", "minLength": 1},
            "citations": {"type": "array", "items": {"type": "string"}},
            "abstained": {"type": "boolean"},
        }
    },
    "memory_result": {
        "type": "object",
        "required": ["ok"],
        "properties": {
            "ok": {"type": "boolean"},
            "value": {},
            "error": {"type": "string"},
        }
    },
}


def validate_mcp_output(output: str, tool_name: str) -> Tuple[bool, str, List[str]]:
    """
    Validate MCP tool output.

    Args:
        output: Tool output
        tool_name: Name of the MCP tool

    Returns:
        Validation result
    """
    # Map tool to schema
    schema_map = {
        "rag.search": "rag_search_result",
        "answer.generate": "answer_generate_result",
        "memory.get": "memory_result",
        "memory.set": "memory_result",
    }

    schema_name = schema_map.get(tool_name)

    if not schema_name:
        # No schema defined, basic JSON validation only
        is_valid, error, _ = validate_json_output(output)
        return is_valid, "JSON_ONLY" if is_valid else "INVALID", [error] if error else []

    schema = COMMON_SCHEMAS.get(schema_name)
    if not schema:
        return True, "NO_SCHEMA", []

    return validate_output(output, schema)


def get_validation_report(output: str, schema: Optional[Dict] = None) -> Dict:
    """
    Generate validation report.

    Args:
        output: Output to validate
        schema: Optional schema to validate against

    Returns:
        Validation report
    """
    is_json_valid, json_error, parsed = validate_json_output(output)

    report = {
        "is_json_valid": is_json_valid,
        "json_error": json_error,
        "output_length": len(output) if output else 0,
    }

    if is_json_valid and parsed:
        report["parsed_type"] = type(parsed).__name__

        if isinstance(parsed, dict):
            report["keys"] = list(parsed.keys())
        elif isinstance(parsed, list):
            report["array_length"] = len(parsed)

    if schema and is_json_valid:
        is_schema_valid, schema_errors = validate_schema(parsed, schema)
        report["is_schema_valid"] = is_schema_valid
        report["schema_errors"] = schema_errors

    return report
