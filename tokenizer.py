import math

def estimate_tokens_from_text(s: str) -> int:
    if not s:
        return 0
    return math.ceil(len(s) / 4)

def estimate_tokens_from_messages(messages) -> int:
    total = 0
    for m in messages or []:
        c = m.get("content", "")
        if isinstance(c, str):
            total += estimate_tokens_from_text(c)
        elif isinstance(c, list):
            for part in c:
                if isinstance(part, dict) and part.get("type") == "text":
                    total += estimate_tokens_from_text(part.get("text",""))
        else:
            total += estimate_tokens_from_text(str(c))
    return total