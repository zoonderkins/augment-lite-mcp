# --- add at top ---
from pathlib import Path
BASE = Path(__file__).resolve().parents[1]
# -------------------

import os, requests, json, yaml, sys
sys.path.insert(0, str(BASE))
from retry import retry_with_backoff

with open(BASE / "config" / "models.yaml", "r", encoding="utf-8") as f:
    CFG = yaml.safe_load(f)

def get_provider(model_alias: str):
    p = CFG["providers"][model_alias]

    # Get base_url: direct value or from env
    if "base_url_env" in p:
        base = os.getenv(p["base_url_env"], p.get("base_url", ""))
    else:
        base = p.get("base_url", "")
    base = base.rstrip("/")

    # Get API key from env
    key_env = p.get("api_key_env")
    api_key = os.getenv(key_env) if key_env else None

    # Get model_id: direct value or from env
    if "model_id_env" in p:
        model_id = os.getenv(p["model_id_env"], p.get("model_id", ""))
    else:
        model_id = p.get("model_id", "")

    # Get API type
    api_type = p.get("type", "openai-compatible")

    return {
        "base": base,
        "api_key": api_key,
        "type": api_type,
        "model_id": model_id
    }


class ProviderError(Exception):
    pass


@retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=60.0)
def _openai_chat_request(url: str, headers: dict, body: dict, timeout: int):
    """Internal function to make OpenAI-compatible HTTP request."""
    r = requests.post(url, headers=headers, data=json.dumps(body), timeout=timeout)
    r.raise_for_status()
    return r.json()


@retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=60.0)
def _anthropic_chat_request(url: str, headers: dict, body: dict, timeout: int):
    """Internal function to make Anthropic-compatible HTTP request."""
    r = requests.post(url, headers=headers, data=json.dumps(body), timeout=timeout)
    r.raise_for_status()
    return r.json()


def chat(provider, messages, **kw):
    """
    Unified chat API - auto-selects OpenAI or Anthropic format based on provider type.

    Args:
        provider: Provider config from get_provider()
        messages: List of message dicts
        **kw: Additional parameters

    Returns:
        str: Generated text
    """
    api_type = provider.get("type", "openai-compatible")

    if api_type == "anthropic":
        return anthropic_chat(provider, messages, **kw)
    else:
        return openai_chat(provider, messages, **kw)


def anthropic_chat(provider, messages, **kw):
    """
    Call Anthropic-compatible chat API (GLM/MiniMax 原厂 Anthropic 格式).

    Args:
        provider: Provider config from get_provider()
        messages: List of message dicts
        **kw: Additional parameters

    Returns:
        str: Generated text
    """
    url = f"{provider['base']}/messages"
    headers = {
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }
    if provider["api_key"]:
        headers["x-api-key"] = provider["api_key"]

    model_id = provider.get("model_id", "")

    # Get max_output_tokens
    max_tokens = kw.get("max_output_tokens")
    if max_tokens is None:
        max_tokens = CFG.get("defaults", {}).get("max_output_tokens", 4096)

    # Extract system message
    system_content = None
    user_messages = []
    for msg in messages:
        if msg.get("role") == "system":
            system_content = msg.get("content", "")
        else:
            user_messages.append(msg)

    body = {
        "model": model_id,
        "messages": user_messages,
        "max_tokens": max_tokens,
        "temperature": kw.get("temperature", 0.2),
    }

    if system_content:
        body["system"] = system_content

    # Make request
    j = _anthropic_chat_request(url, headers, body, kw.get("timeout", 90))

    # Extract content from Anthropic response format
    content_blocks = j.get("content", [])
    if content_blocks:
        # Concatenate all text blocks
        return "".join(
            block.get("text", "")
            for block in content_blocks
            if block.get("type") == "text"
        )

    return ""


def openai_chat(provider, messages, **kw):
    """
    Call OpenAI-compatible chat API with automatic retry and model-specific handling.

    Args:
        provider: Provider config from get_provider()
        messages: List of message dicts
        **kw: Additional parameters:
            - temperature: float (default: 0.2)
            - top_p: float (default: 1.0)
            - max_output_tokens: int (default: from config or 4096)
            - seed: int (default: 7)
            - timeout: int (default: 90)
            - max_retries: int (default: 3)
            - system_instruction: dict (optional, for Gemini native format)
            - use_case: str (optional, auto-load system prompt from config)

    Returns:
        str: Generated text
    """
    url = f"{provider['base']}/chat/completions"
    headers = {"Content-Type": "application/json"}
    if provider["api_key"]:
        headers["Authorization"] = f"Bearer {provider['api_key']}"

    model_id = provider.get("model_id", "")

    # Get max_output_tokens from kwargs or use default from config
    max_tokens = kw.get("max_output_tokens")
    if max_tokens is None:
        max_tokens = CFG.get("defaults", {}).get("max_output_tokens", 4096)

    # 通用保護: 確保 max_tokens 不會太小 (避免 finish_reason=length 返回空響應)
    # 根據模型特性設置最小 token 數
    model_lower = model_id.lower()
    if "glm" in model_lower:
        min_tokens = 10000
    elif "minimax" in model_lower:
        min_tokens = 500
    elif "gemini" in model_lower:
        min_tokens = 100
    else:
        min_tokens = 100

    if max_tokens < min_tokens:
        max_tokens = min_tokens

    # Handle system instructions based on model type
    processed_messages = _process_messages_for_model(messages, model_id, kw)

    body = {
        "model": model_id or "gpt-4o-mini",
        "messages": processed_messages,
        "temperature": kw.get("temperature", 0.2),
        "top_p": kw.get("top_p", 1.0),
        "max_tokens": max_tokens,
    }

    # Add Gemini native system_instruction if provided and model supports it
    if "gemini" in model_id.lower() and kw.get("system_instruction"):
        body["system_instruction"] = kw["system_instruction"]

    # Only add seed for models that support it (not Gemini)
    if "gemini" not in model_id.lower():
        body["seed"] = kw.get("seed", 7)

    # Make request with retry logic
    j = _openai_chat_request(url, headers, body, kw.get("timeout", 90))

    # Extract content from response
    message = j["choices"][0]["message"]
    content = message.get("content", "")

    # Handle empty content (some models may return empty for various reasons)
    if not content:
        if "text" in message:
            content = message["text"]
        elif "reasoning_content" in message and message.get("reasoning_content"):
            content = message["reasoning_content"]

    return content


def _process_messages_for_model(messages: list, model_id: str, kwargs: dict) -> list:
    """
    Process messages based on model compatibility.

    For Gemini:
    - Remove system role messages (not supported)
    - Merge system content into first user message
    - Or use native system_instruction parameter
    """
    model_lower = model_id.lower()

    # For Gemini, handle system messages specially
    if "gemini" in model_lower:
        processed = []
        system_content = None

        for msg in messages:
            if msg.get("role") == "system":
                system_content = msg.get("content", "")
            else:
                processed.append(msg)

        if system_content and not kwargs.get("system_instruction"):
            for i, msg in enumerate(processed):
                if msg.get("role") == "user":
                    processed[i] = {
                        "role": "user",
                        "content": f"{system_content}\n\n{msg['content']}"
                    }
                    break

        return processed

    return messages
