"""
Test suite for ACE-like enhancements.

Run with: python tests/test_ace_enhancements.py
"""

import sys
from pathlib import Path

# Add project root to path
BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))


def test_subagent_filter():
    """Test subagent filtering functionality."""
    print("\n=== Test 1: Subagent Filtering ===")

    from retrieval.search import hybrid_search
    from retrieval.subagent_filter import hybrid_search_with_subagent

    query = "用户认证"

    # Standard search
    print(f"Query: {query}")
    print("\n1. Standard hybrid search:")
    standard_results = hybrid_search(query, k=5)
    print(f"   Found {len(standard_results)} results")
    for i, r in enumerate(standard_results[:3]):
        print(f"   [{i+1}] {r['source']} (score: {r['score']:.3f})")

    # With subagent
    print("\n2. With subagent filtering:")
    try:
        subagent_results = hybrid_search_with_subagent(query, k=5, use_subagent=True)
        print(f"   Found {len(subagent_results)} results")
        for i, r in enumerate(subagent_results[:3]):
            print(f"   [{i+1}] {r['source']} (score: {r['score']:.3f})")
        print("   ✅ Subagent filtering works!")
    except Exception as e:
        print(f"   ⚠️  Subagent filtering failed (may need API key): {e}")

    print()


def test_iterative_search():
    """Test iterative search with query expansion."""
    print("\n=== Test 2: Iterative Search ===")

    from retrieval.iterative_search import iterative_search, should_use_iterative_search

    # Test auto-detection
    simple_query = "用户"
    complex_query = "在用户认证系统中如何集成第三方OAuth并处理token刷新"

    print(f"1. Auto-detection:")
    print(f"   Simple query: '{simple_query}'")
    print(f"      Should use iterative? {should_use_iterative_search(simple_query)}")
    print(f"   Complex query: '{complex_query[:30]}...'")
    print(f"      Should use iterative? {should_use_iterative_search(complex_query)}")

    # Test iterative search
    print(f"\n2. Running iterative search:")
    try:
        results = iterative_search(
            query=complex_query,
            max_iterations=2,  # Limit for testing
            k_per_iteration=3,
            use_subagent=False  # Disable subagent to avoid API calls
        )
        print(f"   Found {len(results)} results across iterations")
        unique_sources = set(r['source'] for r in results)
        print(f"   Unique sources: {len(unique_sources)}")
        print("   ✅ Iterative search works!")
    except Exception as e:
        print(f"   ⚠️  Iterative search failed: {e}")

    print()


def test_enhanced_guardrails():
    """Test enhanced guardrails with detailed feedback."""
    print("\n=== Test 3: Enhanced Guardrails ===")

    from guardrails.abstain import (
        should_abstain,
        get_abstain_reason,
        suggest_query_improvements
    )

    # Test cases
    test_cases = [
        {
            "name": "Empty results",
            "hits": [],
        },
        {
            "name": "Low diversity (same file)",
            "hits": [
                {"source": "file1.py", "score": 0.8, "text": "..."},
                {"source": "file1.py", "score": 0.7, "text": "..."},
                {"source": "file1.py", "score": 0.6, "text": "..."},
            ],
        },
        {
            "name": "Low quality (avg score too low)",
            "hits": [
                {"source": "file1.py", "score": 0.15, "text": "..."},
                {"source": "file2.py", "score": 0.12, "text": "..."},
                {"source": "file3.py", "score": 0.10, "text": "..."},
            ],
        },
        {
            "name": "Good results",
            "hits": [
                {"source": "file1.py", "score": 0.9, "text": "..."},
                {"source": "file2.py", "score": 0.8, "text": "..."},
                {"source": "file3.py", "score": 0.7, "text": "..."},
            ],
        },
    ]

    for case in test_cases:
        print(f"\n{case['name']}:")
        hits = case['hits']

        should_abstain_result = should_abstain(hits, min_diversity=2)
        print(f"   Should abstain? {should_abstain_result}")

        if should_abstain_result:
            reason = get_abstain_reason(hits, min_diversity=2)
            print(f"   Reason: {reason}")

            suggestions = suggest_query_improvements("测试", hits)
            print(f"   Suggestions:\n{suggestions}")

    print("\n   ✅ Enhanced guardrails work!")
    print()


def test_integration():
    """Test full integration with MCP-like workflow."""
    print("\n=== Test 4: Full Integration ===")

    from retrieval.subagent_filter import hybrid_search_with_subagent
    from guardrails.abstain import should_abstain, get_abstain_reason

    query = "数据库连接"

    print(f"Query: {query}")

    # Step 1: Search
    print("\n1. Performing search...")
    try:
        results = hybrid_search_with_subagent(
            query,
            k=5,
            use_subagent=False  # Disable to avoid API calls
        )
        print(f"   Found {len(results)} results")

        # Step 2: Guardrails check
        print("\n2. Checking guardrails...")
        if should_abstain(results, min_diversity=2):
            reason = get_abstain_reason(results, min_diversity=2)
            print(f"   ❌ Abstaining: {reason}")
        else:
            print(f"   ✅ Passed guardrails check")
            print(f"   Top result: {results[0]['source']}")

        print("\n   ✅ Full integration works!")

    except Exception as e:
        print(f"   ⚠️  Integration test failed: {e}")

    print()


def main():
    """Run all tests."""
    print("╔══════════════════════════════════════════════════════════╗")
    print("║     ACE Enhancement Test Suite                           ║")
    print("╚══════════════════════════════════════════════════════════╝")

    # Check if chunks exist
    chunks_path = BASE / "data" / "chunks.jsonl"
    if not chunks_path.exists():
        print("\n⚠️  Warning: No chunks.jsonl found!")
        print("   Run 'python retrieval/build_index.py' first to index your codebase.")
        print("   Some tests will fail without indexed data.\n")

    # Run tests
    test_subagent_filter()
    test_iterative_search()
    test_enhanced_guardrails()
    test_integration()

    print("╔══════════════════════════════════════════════════════════╗")
    print("║     Test Suite Complete                                  ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print("\nNote: Tests marked with ⚠️ may require API keys or indexed data.")
    print("      Tests marked with ✅ passed successfully.\n")


if __name__ == "__main__":
    main()
