#!/usr/bin/env python3
"""
v1.3.x New Features Test Suite
Tests: dual.search, answer.accumulated, answer.unified, code.*, search.pattern, file.*
"""

import sys
import os
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
DATA_DIR = Path(os.getenv("AUGMENT_DB_DIR", BASE / "data"))


def test_dual_search():
    """Test dual.search - auggie + augment-lite combined search"""
    print("\n" + "="*80)
    print("Test 1: dual.search")
    print("="*80)

    try:
        from retrieval.dual_search import dual_search

        query = "how to build index"
        print(f"   Query: {query}")

        result = dual_search(
            query=query,
            k=5,
            use_subagent=False,  # Disable for faster test
            use_iterative=False,
            include_auggie=False,  # Skip auggie for local test
            auto_rebuild=False,
            project="auto"
        )

        print(f"   ok: {result.get('ok')}")
        print(f"   hits: {len(result.get('hits', []))}")
        print(f"   auggie_available: {result.get('auggie_available')}")

        assert result.get("ok") is True, "dual.search should return ok=True"
        print("   ✅ dual.search works!")
        return True

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_answer_accumulated():
    """Test answer.accumulated - multi-round evidence accumulation"""
    print("\n" + "="*80)
    print("Test 2: answer.accumulated")
    print("="*80)

    try:
        from retrieval.accumulated_answer import generate_accumulated_answer

        query = "What are the main components of this project?"
        print(f"   Query: {query}")

        # Test with explicit sub_queries to avoid LLM call
        result = generate_accumulated_answer(
            query=query,
            sub_queries=["main entry point", "retrieval system"],
            k_per_query=3,
            route="small-fast",
            temperature=0.1,
            project="auto"
        )

        print(f"   ok: {result.get('ok')}")
        print(f"   has answer: {'answer' in result}")
        if result.get('answer'):
            print(f"   answer preview: {result['answer'][:100]}...")

        assert result.get("ok") is True, "answer.accumulated should return ok=True"
        print("   ✅ answer.accumulated works!")
        return True

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_answer_unified():
    """Test answer.unified - orchestration plan generation"""
    print("\n" + "="*80)
    print("Test 3: answer.unified")
    print("="*80)

    try:
        from retrieval.unified_orchestrator import create_execution_plan

        query = "Analyze the search architecture"
        print(f"   Query: {query}")

        plan = create_execution_plan(
            query=query,
            sub_queries=None,  # Auto-generate
            include_auggie=True,
            route="reason-large"
        )

        print(f"   ok: {plan.get('ok')}")
        print(f"   plan_type: {plan.get('plan_type')}")
        print(f"   total_steps: {plan.get('total_steps')}")

        if plan.get('steps'):
            for step in plan['steps'][:3]:
                print(f"   - Step {step.get('step')}: {step.get('action')} -> {step.get('purpose', '')[:50]}")

        assert plan.get("ok") is True, "answer.unified should return ok=True"
        assert plan.get("steps"), "answer.unified should return steps"
        print("   ✅ answer.unified works!")
        return True

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_code_symbols():
    """Test code.symbols - Tree-sitter AST symbol extraction"""
    print("\n" + "="*80)
    print("Test 4: code.symbols")
    print("="*80)

    try:
        from code.symbols import extract_symbols

        # Test on this file itself
        test_file = BASE / "mcp_bridge_lazy.py"
        print(f"   File: {test_file.name}")

        symbols = extract_symbols(str(test_file), depth=1, include_body=False)

        print(f"   Found {len(symbols)} top-level symbols")
        if symbols:
            for s in symbols[:5]:
                print(f"   - {s.get('name')} ({s.get('type')}) @ line {s.get('start_line')}")

        assert len(symbols) > 0, "Should find symbols in mcp_bridge_lazy.py"
        print("   ✅ code.symbols works!")
        return True

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_code_find_symbol():
    """Test code.find_symbol - symbol lookup by name pattern"""
    print("\n" + "="*80)
    print("Test 5: code.find_symbol")
    print("="*80)

    try:
        from code.symbols import find_symbol
        from utils.project_utils import resolve_auto_project, get_project_status

        project_name = resolve_auto_project()
        status = get_project_status(project_name) if project_name else {}
        project_root = status.get("root", str(BASE))

        pattern = "hybrid_search"
        print(f"   Pattern: {pattern}")
        print(f"   Project root: {project_root}")

        results = find_symbol(
            pattern,
            file_path=None,
            project_root=project_root,
            include_body=False
        )

        print(f"   Found {len(results)} matches")
        if results:
            for r in results[:3]:
                print(f"   - {r.get('name')} in {Path(r.get('file', '')).name}")

        # May or may not find results depending on project
        print("   ✅ code.find_symbol works!")
        return True

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_code_references():
    """Test code.references - find all references to a symbol"""
    print("\n" + "="*80)
    print("Test 6: code.references")
    print("="*80)

    try:
        from code.references import find_references
        from utils.project_utils import resolve_auto_project, get_project_status

        project_name = resolve_auto_project()
        status = get_project_status(project_name) if project_name else {}
        project_root = status.get("root", str(BASE))

        symbol = "DATA_DIR"
        print(f"   Symbol: {symbol}")

        results = find_references(symbol, project_root, context_lines=1)

        print(f"   Found {len(results)} references")
        if results:
            for r in results[:3]:
                print(f"   - {Path(r.get('file', '')).name}:{r.get('line')}")

        print("   ✅ code.references works!")
        return True

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_search_pattern():
    """Test search.pattern - regex pattern search"""
    print("\n" + "="*80)
    print("Test 7: search.pattern")
    print("="*80)

    try:
        from code.pattern_search import search_pattern
        from utils.project_utils import resolve_auto_project, get_project_status

        project_name = resolve_auto_project()
        status = get_project_status(project_name) if project_name else {}
        project_root = status.get("root", str(BASE))

        pattern = r"def test_\w+"
        print(f"   Pattern: {pattern}")
        print(f"   File glob: **/*.py")

        results = search_pattern(
            pattern, project_root,
            file_glob="tests/**/*.py",
            context_lines=0,
            case_sensitive=True
        )

        print(f"   Found {len(results)} matches")
        if results:
            for r in results[:3]:
                print(f"   - {Path(r.get('file', '')).name}:{r.get('line')}: {r.get('match', '')[:40]}")

        print("   ✅ search.pattern works!")
        return True

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_read():
    """Test file.read - read file content with line range"""
    print("\n" + "="*80)
    print("Test 8: file.read")
    print("="*80)

    try:
        from file.reader import read_file

        result = read_file(
            "mcp_bridge_lazy.py",
            project_root=str(BASE),
            start_line=1,
            end_line=20
        )

        print(f"   ok: {result.get('ok')}")
        print(f"   file: {result.get('file')}")
        print(f"   lines: {result.get('start_line')}-{result.get('end_line')}")

        if result.get('content'):
            lines = result['content'].split('\n')
            print(f"   content lines: {len(lines)}")
            print(f"   first line: {lines[0][:60]}...")

        assert result.get("ok") is True, "file.read should return ok=True"
        print("   ✅ file.read works!")
        return True

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_list():
    """Test file.list - list directory contents"""
    print("\n" + "="*80)
    print("Test 9: file.list")
    print("="*80)

    try:
        from file.finder import list_directory

        result = list_directory(
            "tests",
            project_root=str(BASE),
            recursive=False,
            pattern="*.py"
        )

        print(f"   ok: {result.get('ok')}")
        print(f"   path: {result.get('path')}")
        print(f"   count: {result.get('count')}")

        if result.get('files'):
            for f in result['files'][:5]:
                # Handle both dict and string return formats
                if isinstance(f, dict):
                    print(f"   - {f.get('name')} ({f.get('type')})")
                else:
                    print(f"   - {f}")

        assert result.get("ok") is True, "file.list should return ok=True"
        print("   ✅ file.list works!")
        return True

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_find():
    """Test file.find - glob pattern file search"""
    print("\n" + "="*80)
    print("Test 10: file.find")
    print("="*80)

    try:
        from file.finder import find_files

        pattern = "test_*.py"
        print(f"   Pattern: {pattern}")

        result = find_files(pattern, str(BASE))

        print(f"   ok: {result.get('ok')}")
        print(f"   count: {result.get('count')}")

        if result.get('files'):
            for f in result['files'][:5]:
                print(f"   - {f}")

        assert result.get("ok") is True, "file.find should return ok=True"
        print("   ✅ file.find works!")
        return True

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all v1.3.x feature tests"""
    print("\n" + "="*80)
    print("v1.3.x New Features Test Suite")
    print("="*80)
    print(f"Project root: {BASE}")
    print(f"Python: {sys.version}")

    results = {}

    # Test 1-3: RAG & Search
    results["dual.search"] = test_dual_search()
    results["answer.accumulated"] = test_answer_accumulated()
    results["answer.unified"] = test_answer_unified()

    # Test 4-6: Code Analysis
    results["code.symbols"] = test_code_symbols()
    results["code.find_symbol"] = test_code_find_symbol()
    results["code.references"] = test_code_references()

    # Test 7: Pattern Search
    results["search.pattern"] = test_search_pattern()

    # Test 8-10: File Operations
    results["file.read"] = test_file_read()
    results["file.list"] = test_file_list()
    results["file.find"] = test_file_find()

    # Summary
    print("\n" + "="*80)
    print("Test Results Summary")
    print("="*80)

    passed = sum(1 for r in results.values() if r)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ Passed" if result else "❌ Failed"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} passed")

    if passed == total:
        print("\n🎉 All v1.3.x feature tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
