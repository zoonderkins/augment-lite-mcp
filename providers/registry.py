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
    base = p["base_url"].rstrip("/")
    key_env = p.get("api_key_env")
    api_key = os.getenv(key_env) if key_env else None
    return {
        "base": base,
        "api_key": api_key,
        "type": p.get("type","openai-compatible"),
        "model_id": p.get("model_id")
    }

class ProviderError(Exception):
    pass

@retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=60.0)
def _openai_chat_request(url: str, headers: dict, body: dict, timeout: int):
    """
    Internal function to make the actual HTTP request.
    Separated for retry logic.
    """
    r = requests.post(url, headers=headers, data=json.dumps(body), timeout=timeout)
    r.raise_for_status()
    return r.json()

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
    # 影響的模型: Gemini, MiniMax-M2, GLM-4.6 等

    # 根據模型特性設置最小 token 數
    if model_id.startswith("zai/glm"):
        # GLM-4.6: 使用推理模式 (類似 OpenAI o1)，reasoning_content + content 都需要大量空間
        # 實測: max_tokens < 10000 會導致 finish_reason=length 且 content 為空
        # Stream 模式支持最大 20872 tokens
        min_tokens = 10000
    elif model_id.startswith("minimaxi/"):
        # MiniMax-M2: 需要較大空間，否則返回空 content
        min_tokens = 500
    elif model_id.startswith("google/"):
        # Gemini: 需要基本保護
        min_tokens = 100
    elif model_id.startswith("groq/moonshotai/"):
        # Kimi-K2: 表現良好，只需最小保護
        min_tokens = 50
    else:
        # 其他模型: 通用建議值
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
    if model_id.startswith("google/") and kw.get("system_instruction"):
        body["system_instruction"] = kw["system_instruction"]

    # Only add seed for models that support it (not Gemini)
    if not model_id.startswith("google/"):
        body["seed"] = kw.get("seed", 7)

    # Make request with retry logic
    j = _openai_chat_request(url, headers, body, kw.get("timeout", 90))

    # Extract content from response
    message = j["choices"][0]["message"]
    content = message.get("content", "")

    # Handle empty content (some models may return empty for various reasons)
    if not content:
        # Try alternative content fields
        if "text" in message:
            content = message["text"]
        # GLM-4.6 推理模式: content 可能為空，但 reasoning_content 有內容
        # 這種情況下我們優先使用 content，如果為空才使用 reasoning_content
        elif "reasoning_content" in message and message.get("reasoning_content"):
            # 注意: reasoning_content 包含推理過程，不是最終答案
            # 但當 content 為空時，至少返回推理內容而不是完全空白
            content = message["reasoning_content"]

    return content


def _process_messages_for_model(messages: list, model_id: str, kwargs: dict) -> list:
    """
    Process messages based on model compatibility.

    For Gemini:
    - Remove system role messages (not supported)
    - Merge system content into first user message
    - Or use native system_instruction parameter

    Args:
        messages: Original message list
        model_id: Model identifier
        kwargs: Additional parameters (may contain use_case for auto-loading prompts)

    Returns:
        Processed message list
    """
    # For Gemini, handle system messages specially
    if model_id.startswith("google/"):
        processed = []
        system_content = None

        for msg in messages:
            if msg.get("role") == "system":
                # Extract system content but don't add as message
                system_content = msg.get("content", "")
            else:
                processed.append(msg)

        # If we have system content and it's not being used as native system_instruction,
        # merge it into the first user message
        if system_content and not kwargs.get("system_instruction"):
            for i, msg in enumerate(processed):
                if msg.get("role") == "user":
                    # Merge system content into first user message
                    processed[i] = {
                        "role": "user",
                        "content": f"{system_content}\n\n{msg['content']}"
                    }
                    break

        return processed

    # For other models, return messages as-is
    return messages
