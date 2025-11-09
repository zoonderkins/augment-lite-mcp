# --- add at top ---
from pathlib import Path
BASE = Path(__file__).resolve().parent
# -------------------

import yaml

with open(BASE / "config" / "models.yaml","r",encoding="utf-8") as f:
    CFG = yaml.safe_load(f)

def choose(task_type: str):
    if task_type in ("lookup", "small_fix"): return CFG["routes"]["small-fast"]["model"]
    if task_type in ("refactor","reason"):   return CFG["routes"]["reason-large"]["model"]
    return CFG["routes"]["general"]["model"]

def pick_route(task_type: str, total_tokens_est: int, route_override: str | None = None):
    """
    Pick the best route based on task type and token count.

    Returns:
        str: Model alias
    """
    if route_override and route_override != "auto":
        if route_override in CFG["routes"]:
            return CFG["routes"][route_override]["model"]
        if route_override in CFG["providers"]:
            return route_override

    th_small = int(CFG.get("routing_thresholds",{}).get("small_max_tokens", 200_000))
    th_big   = int(CFG.get("routing_thresholds",{}).get("big_mid_max_tokens", 400_000))
    th_long  = int(CFG.get("routing_thresholds",{}).get("long_context_max_tokens", 1_000_000))

    if total_tokens_est > th_long:
        return CFG["routes"]["ultra-long-context"]["model"]
    if total_tokens_est > th_big:
        return CFG["routes"]["long-context"]["model"]
    if total_tokens_est > th_small:
        return CFG["routes"]["big-mid"]["model"]
    return choose(task_type)

def get_route_config(task_type: str, total_tokens_est: int, route_override: str | None = None):
    """
    Get the full route configuration including max_output_tokens.

    Returns:
        dict: {
            "model": str,
            "max_output_tokens": int
        }
    """
    # Determine which route to use
    if route_override and route_override != "auto":
        if route_override in CFG["routes"]:
            route_name = route_override
        elif route_override in CFG["providers"]:
            # Direct provider override, use defaults
            return {
                "model": route_override,
                "max_output_tokens": CFG.get("defaults", {}).get("max_output_tokens", 4096)
            }
        else:
            route_name = "general"
    else:
        # Auto routing based on token count
        th_small = int(CFG.get("routing_thresholds",{}).get("small_max_tokens", 200_000))
        th_big   = int(CFG.get("routing_thresholds",{}).get("big_mid_max_tokens", 400_000))
        th_long  = int(CFG.get("routing_thresholds",{}).get("long_context_max_tokens", 1_000_000))

        if total_tokens_est > th_long:
            route_name = "ultra-long-context"  # >1M tokens → Qwen3 Coder Plus
        elif total_tokens_est > th_big:
            route_name = "long-context"        # 400k~1M → Gemini
        elif total_tokens_est > th_small:
            route_name = "big-mid"             # 200k~400k → GPT-5
        else:
            # Choose based on task type
            if task_type in ("lookup", "small_fix"):
                route_name = "small-fast"
            elif task_type in ("refactor", "reason"):
                route_name = "reason-large"
            else:
                route_name = "general"

    # Get route config
    route_cfg = CFG["routes"].get(route_name, CFG["routes"]["general"])

    return {
        "model": route_cfg["model"],
        "max_output_tokens": route_cfg.get("max_output_tokens", CFG.get("defaults", {}).get("max_output_tokens", 4096))
    }
