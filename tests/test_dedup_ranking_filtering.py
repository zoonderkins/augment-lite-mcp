#!/usr/bin/env python3
"""
測試去重、智能排序和 gitignore 過濾功能
"""

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

def test_deduplication():
    """測試去重功能"""
    print("\n" + "="*80)
    print("測試 1: 去重功能")
    print("="*80)

    from retrieval.search import hybrid_search

    try:
        query = "專案管理"

        # 執行檢索
        print(f"\n查詢: '{query}'")
        results = hybrid_search(query, k=20, project="auto")

        print(f"返回結果數: {len(results)}")

        # 檢查去重
        sources = [r['source'] for r in results]
        unique_sources = set(sources)

        print(f"唯一來源數: {len(unique_sources)}")
        print(f"重複項數: {len(sources) - len(unique_sources)}")

        if len(sources) == len(unique_sources):
            print("✅ 去重功能正常 - 無重複結果")

            # 顯示前5個來源
            print("\n前 5 個唯一來源:")
            for i, source in enumerate(list(unique_sources)[:5], 1):
                print(f"  {i}. {source}")

            return True
        else:
            print(f"⚠️  發現重複結果")
            # 找出重複的來源
            from collections import Counter
            source_counts = Counter(sources)
            duplicates = {src: count for src, count in source_counts.items() if count > 1}

            print(f"\n重複的來源:")
            for src, count in duplicates.items():
                print(f"  {src}: {count} 次")

            return False

    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_smart_ranking():
    """測試智能排序功能"""
    print("\n" + "="*80)
    print("測試 2: 智能排序")
    print("="*80)

    from retrieval.search import hybrid_search

    try:
        query = "如何建立索引"

        # 執行檢索
        print(f"\n查詢: '{query}'")
        results = hybrid_search(query, k=10, project="auto")

        print(f"返回結果數: {len(results)}")

        # 檢查排序
        print("\n結果排序（按相關性）:")
        prev_score = float('inf')
        is_sorted = True

        for i, result in enumerate(results, 1):
            source = result.get('source', 'N/A')
            score = result.get('score', 0.0)

            # 檢查是否按分數降序排列
            if score > prev_score:
                is_sorted = False
            prev_score = score

            # 顯示前5個結果
            if i <= 5:
                source_short = source[-60:] if len(source) > 60 else source
                print(f"  {i}. (score: {score:.4f}) {source_short}")

        if is_sorted:
            print("\n✅ 智能排序正常 - 結果按相關性降序排列")
            return True
        else:
            print("\n⚠️  排序可能有問題 - 分數未按降序排列")
            return False

    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_gitignore_filtering():
    """測試 gitignore 和常見過濾功能"""
    print("\n" + "="*80)
    print("測試 3: gitignore 和常見目錄過濾")
    print("="*80)

    from retrieval.search import hybrid_search

    try:
        query = "import"  # 通用查詢，可能匹配很多檔案

        # 執行檢索
        print(f"\n查詢: '{query}'")
        results = hybrid_search(query, k=50, project="auto")

        print(f"返回結果數: {len(results)}")

        # 檢查是否包含應該被過濾的路徑
        filtered_patterns = [
            'node_modules/',
            '.git/',
            '__pycache__/',
            '.venv/',
            'venv/',
            'dist/',
            'build/',
            '.next/',
            '.nuxt/',
            'coverage/',
            '.pytest_cache/',
            '.mypy_cache/',
        ]

        print("\n檢查過濾模式:")
        found_filtered = {}

        for pattern in filtered_patterns:
            matching = [r for r in results if pattern in r['source']]
            if matching:
                found_filtered[pattern] = len(matching)
                print(f"  ❌ {pattern}: 找到 {len(matching)} 個結果（應該被過濾）")
            else:
                print(f"  ✅ {pattern}: 已過濾")

        if not found_filtered:
            print("\n✅ gitignore 過濾正常 - 所有常見目錄已被過濾")

            # 顯示一些實際結果
            print("\n實際結果示例（前 5 個）:")
            for i, result in enumerate(results[:5], 1):
                source = result.get('source', 'N/A')
                print(f"  {i}. {source}")

            return True
        else:
            print(f"\n⚠️  發現 {len(found_filtered)} 個模式未被過濾")

            # 顯示一些未過濾的結果
            for pattern, count in list(found_filtered.items())[:3]:
                matching = [r for r in results if pattern in r['source']]
                print(f"\n{pattern} 的結果示例:")
                for r in matching[:2]:
                    print(f"  - {r['source']}")

            return False

    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_search_quality():
    """測試搜索質量（綜合測試）"""
    print("\n" + "="*80)
    print("測試 4: 搜索質量綜合測試")
    print("="*80)

    from retrieval.search import hybrid_search

    try:
        # 測試不同類型的查詢
        test_cases = [
            {
                "query": "MCP 工具",
                "expected_keywords": ["mcp", "tool", "工具"],
                "min_results": 3
            },
            {
                "query": "索引建立",
                "expected_keywords": ["index", "build", "索引", "建立"],
                "min_results": 3
            },
            {
                "query": "Python 函數",
                "expected_keywords": ["python", "def", "function", "函數"],
                "min_results": 2
            },
        ]

        all_passed = True

        for i, test_case in enumerate(test_cases, 1):
            query = test_case["query"]
            expected_keywords = test_case["expected_keywords"]
            min_results = test_case["min_results"]

            print(f"\n測試案例 {i}: '{query}'")
            results = hybrid_search(query, k=10, project="auto")

            print(f"  結果數: {len(results)}")

            # 檢查結果數量
            if len(results) >= min_results:
                print(f"  ✅ 結果數量充足 (>= {min_results})")
            else:
                print(f"  ⚠️  結果數量不足 (< {min_results})")
                all_passed = False

            # 檢查相關性（是否包含關鍵詞）
            relevant_count = 0
            for result in results[:5]:  # 檢查前5個結果
                text = result.get('text', '').lower()
                source = result.get('source', '').lower()
                combined = text + ' ' + source

                if any(keyword.lower() in combined for keyword in expected_keywords):
                    relevant_count += 1

            relevance_rate = relevant_count / min(5, len(results)) if results else 0
            print(f"  相關性: {relevant_count}/{min(5, len(results))} ({relevance_rate*100:.0f}%)")

            if relevance_rate >= 0.6:
                print(f"  ✅ 相關性良好")
            else:
                print(f"  ⚠️  相關性偏低")
                all_passed = False

        if all_passed:
            print("\n✅ 搜索質量綜合測試通過")
            return True
        else:
            print("\n⚠️  部分測試案例未達標")
            return False

    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """執行所有測試"""
    print("\n" + "="*80)
    print("去重、智能排序和過濾功能測試")
    print("="*80)
    print(f"專案根目錄: {BASE}")

    results = {}

    # 測試 1: 去重
    results["去重功能"] = test_deduplication()

    # 測試 2: 智能排序
    results["智能排序"] = test_smart_ranking()

    # 測試 3: gitignore 過濾
    results["gitignore 過濾"] = test_gitignore_filtering()

    # 測試 4: 搜索質量
    results["搜索質量"] = test_search_quality()

    # 打印測試結果摘要
    print("\n" + "="*80)
    print("測試結果摘要")
    print("="*80)

    for test_name, result in results.items():
        status = "✅ 通過" if result else "⚠️  需改進"
        print(f"{status}: {test_name}")

    # 統計結果
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    print(f"\n總計: {passed}/{total} 測試通過")

    if passed == total:
        print("\n🎉 所有測試通過！")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 個測試需要改進")
        return 1

if __name__ == "__main__":
    sys.exit(main())
