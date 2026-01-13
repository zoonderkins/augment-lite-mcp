#!/usr/bin/env python3
"""
Test dynamic max_output_tokens configuration.

This script verifies that different routes use different max_output_tokens values.
"""

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from router import get_route_config

def test_route_config():
    """Test that each route has the correct max_output_tokens."""
    
    print("=" * 60)
    print("Testing Dynamic max_output_tokens Configuration")
    print("=" * 60)
    print()
    
    test_cases = [
        # (task_type, total_tokens_est, route_override, expected_model, expected_max_tokens)
        ("lookup", 50000, None, "minimax-m2.1", 2048),         # small-fast
        ("small_fix", 50000, None, "minimax-m2.1", 2048),      # small-fast
        ("refactor", 50000, None, "glm-4.7", 8192),            # reason-large
        ("reason", 50000, None, "glm-4.7", 8192),              # reason-large
        ("general", 50000, None, "glm-4.7", 4096),             # general
        ("lookup", 250000, None, "glm-4.7", 8192),             # big-mid (>200k)
        ("lookup", 450000, None, "requesty-qwen3-coder", 8192),  # long-context (>400k)

        # Test route overrides
        ("lookup", 50000, "small-fast", "minimax-m2.1", 2048),
        ("lookup", 50000, "reason-large", "glm-4.7", 8192),
        ("lookup", 50000, "general", "glm-4.7", 4096),
        ("lookup", 50000, "big-mid", "glm-4.7", 8192),
        ("lookup", 50000, "long-context", "requesty-qwen3-coder", 8192),
    ]
    
    all_passed = True
    
    for i, (task, tokens, route, expected_model, expected_max_tokens) in enumerate(test_cases, 1):
        route_str = route or "auto"
        config = get_route_config(task, tokens, route_override=route)
        
        model = config["model"]
        max_tokens = config["max_output_tokens"]
        
        passed = (model == expected_model and max_tokens == expected_max_tokens)
        status = "✅ PASS" if passed else "❌ FAIL"
        
        print(f"Test {i:2d}: {status}")
        print(f"  Task: {task:12s} | Tokens: {tokens:7d} | Route: {route_str:15s}")
        print(f"  Expected: model={expected_model:20s} max_tokens={expected_max_tokens}")
        print(f"  Got:      model={model:20s} max_tokens={max_tokens}")
        
        if not passed:
            all_passed = False
            print(f"  ⚠️  Mismatch!")
        
        print()
    
    print("=" * 60)
    if all_passed:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1

def show_route_summary():
    """Show summary of all routes and their max_output_tokens."""
    
    print()
    print("=" * 60)
    print("Route Configuration Summary")
    print("=" * 60)
    print()
    
    routes = [
        ("small-fast", "lookup", 50000),
        ("reason-large", "refactor", 50000),
        ("general", "general", 50000),
        ("big-mid", "lookup", 250000),
        ("long-context", "lookup", 450000),
    ]
    
    print(f"{'Route':<15} {'Model':<20} {'max_output_tokens':<20} {'Use Case'}")
    print("-" * 80)
    
    for route_name, task, tokens in routes:
        config = get_route_config(task, tokens, route_override=route_name)
        model = config["model"]
        max_tokens = config["max_output_tokens"]
        
        use_cases = {
            "small-fast": "快速查詢，短回答",
            "reason-large": "推理任務，中等長度",
            "general": "一般查詢，中等長度",
            "big-mid": "大型任務，長回答",
            "long-context": "長上下文，長回答",
        }
        
        print(f"{route_name:<15} {model:<20} {max_tokens:<20} {use_cases[route_name]}")
    
    print()

def main():
    """Run all tests."""
    
    # Show route summary
    show_route_summary()
    
    # Run tests
    result = test_route_config()
    
    if result == 0:
        print()
        print("🎉 Dynamic max_output_tokens configuration is working correctly!")
        print()
        print("Usage in Claude:")
        print("  - 快速查詢 (lookup/small_fix): 使用 2048 tokens")
        print("  - 推理任務 (refactor/reason): 使用 4096 tokens")
        print("  - 一般查詢 (general): 使用 4096 tokens")
        print("  - 大型任務 (>200k tokens): 使用 8192 tokens")
        print("  - 長上下文 (>400k tokens): 使用 8192 tokens")
        print()
    
    return result

if __name__ == "__main__":
    exit(main())

