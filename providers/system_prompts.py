"""
System prompts management for different model providers.

This module loads and manages system instructions from config/system_prompts.yaml,
providing model-specific and use-case-specific prompt templates.
"""

from pathlib import Path
import yaml
import logging
from typing import Dict, Optional, Any

BASE = Path(__file__).resolve().parents[1]
logger = logging.getLogger(__name__)

# Load system prompts configuration
_prompts_config: Optional[Dict] = None

def load_prompts_config() -> Dict:
    """Load system prompts configuration from YAML."""
    global _prompts_config

    if _prompts_config is not None:
        return _prompts_config

    config_path = BASE / "config" / "system_prompts.yaml"

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            _prompts_config = yaml.safe_load(f)
        logger.info(f"Loaded system prompts config from {config_path}")
        return _prompts_config
    except FileNotFoundError:
        logger.warning(f"System prompts config not found at {config_path}, using defaults")
        _prompts_config = {
            "defaults": {},
            "model_specific": {},
            "use_case_templates": {},
            "model_compatibility": {}
        }
        return _prompts_config
    except Exception as e:
        logger.error(f"Failed to load system prompts config: {e}")
        _prompts_config = {
            "defaults": {},
            "model_specific": {},
            "use_case_templates": {},
            "model_compatibility": {}
        }
        return _prompts_config


def get_system_prompt(
    use_case: str,
    model_id: str,
    fallback_to_default: bool = True
) -> Optional[str]:
    """
    Get system prompt for a specific use case and model.

    Args:
        use_case: Use case name (e.g., "subagent_filter", "query_expansion")
        model_id: Model ID (e.g., "google/gemini-2.5-flash")
        fallback_to_default: If True, fall back to default prompt if model-specific not found

    Returns:
        System prompt string, or None if not found
    """
    config = load_prompts_config()

    # Try model-specific prompt first
    model_prompts = config.get("model_specific", {}).get(model_id, {})
    if use_case in model_prompts:
        logger.debug(f"Using model-specific prompt for {model_id} / {use_case}")
        return model_prompts[use_case]

    # Fall back to default
    if fallback_to_default:
        default_prompts = config.get("defaults", {})
        if use_case in default_prompts:
            logger.debug(f"Using default prompt for {use_case}")
            return default_prompts[use_case]

    logger.warning(f"No system prompt found for {use_case} / {model_id}")
    return None


def get_model_compatibility(model_id: str) -> Dict[str, Any]:
    """
    Get compatibility configuration for a model.

    Args:
        model_id: Model ID (e.g., "google/gemini-2.5-flash")

    Returns:
        Dictionary with compatibility settings:
        - supports_system_role: bool
        - system_instruction_format: str ("native" or "system_message")
        - prefer_concise/detailed/balanced: bool
        - max_system_instruction_tokens: int
    """
    config = load_prompts_config()
    compatibility = config.get("model_compatibility", {})

    # Check Google models
    google_models = compatibility.get("google_models", {})
    if isinstance(google_models, dict):
        model_list = google_models.get("models", [])
        if model_id in model_list or model_id.startswith("google/"):
            return {
                "supports_system_role": google_models.get("supports_system_role", False),
                "system_instruction_format": google_models.get("system_instruction_format", "native"),
                "prefer_concise": google_models.get("prefer_concise", True),
                "max_system_instruction_tokens": google_models.get("max_system_instruction_tokens", 1000)
            }
    elif isinstance(google_models, list):
        # Handle old format where it's just a list
        if model_id in google_models or model_id.startswith("google/"):
            return {
                "supports_system_role": False,
                "system_instruction_format": "native",
                "prefer_concise": True,
                "max_system_instruction_tokens": 1000
            }

    # Check Anthropic models
    anthropic_models = compatibility.get("anthropic_models", {})
    if isinstance(anthropic_models, dict):
        model_list = anthropic_models.get("models", [])
        if model_id in model_list or model_id.startswith("anthropic/"):
            return {
                "supports_system_role": anthropic_models.get("supports_system_role", True),
                "system_instruction_format": anthropic_models.get("system_instruction_format", "system_message"),
                "prefer_detailed": anthropic_models.get("prefer_detailed", True),
                "max_system_instruction_tokens": anthropic_models.get("max_system_instruction_tokens", 2000)
            }
    elif isinstance(anthropic_models, list):
        if model_id in anthropic_models or model_id.startswith("anthropic/"):
            return {
                "supports_system_role": True,
                "system_instruction_format": "system_message",
                "prefer_detailed": True,
                "max_system_instruction_tokens": 2000
            }

    # Default: OpenAI-compatible
    openai_compat = compatibility.get("openai_compatible", {})
    return {
        "supports_system_role": openai_compat.get("supports_system_role", True),
        "system_instruction_format": openai_compat.get("system_instruction_format", "system_message"),
        "prefer_balanced": openai_compat.get("prefer_balanced", True),
        "max_system_instruction_tokens": openai_compat.get("max_system_instruction_tokens", 1500)
    }


def build_use_case_messages(
    use_case: str,
    model_id: str,
    variables: Dict[str, Any]
) -> list:
    """
    Build message list for a specific use case.

    Args:
        use_case: Use case template name (e.g., "rag_retrieval", "iterative_search")
        model_id: Model ID for selecting appropriate system prompt
        variables: Variables to fill in the template

    Returns:
        List of message dictionaries ready for API call
    """
    config = load_prompts_config()
    templates = config.get("use_case_templates", {})

    if use_case not in templates:
        logger.warning(f"Use case template '{use_case}' not found")
        return []

    template = templates[use_case]
    compatibility = get_model_compatibility(model_id)

    # Get system instruction
    system_key = template.get("system_instruction", "").strip("{}")
    system_prompt = get_system_prompt(system_key, model_id)

    # Build user message
    user_prefix = template.get("user_prefix", "").format(**variables)
    user_suffix = template.get("user_suffix", "").format(**variables)
    user_content = user_prefix + user_suffix

    messages = []

    # Add system instruction based on model compatibility
    if system_prompt:
        if compatibility.get("supports_system_role", True):
            # Standard OpenAI format
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        else:
            # Gemini format: merge into user message
            user_content = f"{system_prompt}\n\n{user_content}"

    # Add user message
    messages.append({
        "role": "user",
        "content": user_content
    })

    return messages


def supports_native_system_instruction(model_id: str) -> bool:
    """
    Check if a model supports native system_instruction parameter.

    Args:
        model_id: Model ID

    Returns:
        True if model supports native system_instruction (like Gemini)
    """
    compatibility = get_model_compatibility(model_id)
    return compatibility.get("system_instruction_format") == "native"


def get_system_instruction_for_gemini(
    use_case: str,
    model_id: str
) -> Optional[Dict]:
    """
    Get system instruction in Gemini's native format.

    Args:
        use_case: Use case name
        model_id: Model ID

    Returns:
        Dictionary in Gemini format: {"parts": [{"text": "..."}]}
        or None if not applicable
    """
    if not supports_native_system_instruction(model_id):
        return None

    system_prompt = get_system_prompt(use_case, model_id)
    if not system_prompt:
        return None

    return {
        "parts": [
            {"text": system_prompt}
        ]
    }


# Convenience functions for common use cases

def get_subagent_filter_messages(model_id: str, query: str, candidates: list, max_results: int) -> list:
    """Build messages for subagent filtering."""

    # Format candidates
    candidates_text = []
    for i, cand in enumerate(candidates):
        source = cand.get("source", "unknown")
        text_preview = cand.get("text", "")[:200]
        score = cand.get("score", 0.0)

        candidates_text.append(
            f"[{i}] 文件: {source}\n"
            f"    分數: {score:.3f}\n"
            f"    內容: {text_preview}...\n"
        )

    candidates_str = "\n".join(candidates_text)

    return build_use_case_messages(
        "rag_retrieval",
        model_id,
        {
            "query": query,
            "count": len(candidates),
            "candidates": candidates_str,
            "max_results": max_results
        }
    )


def get_query_expansion_messages(
    model_id: str,
    original_query: str,
    current_results: list,
    iteration: int
) -> list:
    """Build messages for query expansion."""

    # Summarize results
    if not current_results:
        results_summary = "（沒有找到結果）"
    else:
        top_sources = [r.get("source", "unknown") for r in current_results[:3]]
        results_summary = "\n".join(f"- {src}" for src in top_sources)

    return build_use_case_messages(
        "iterative_search",
        model_id,
        {
            "original_query": original_query,
            "iteration": iteration + 1,
            "results_summary": results_summary
        }
    )
