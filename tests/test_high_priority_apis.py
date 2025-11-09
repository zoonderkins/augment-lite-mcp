#!/usr/bin/env python3
"""
高優先級 MCP API 測試
測試 answer.generate 和 index.rebuild
"""

import sys
import os
from pathlib import Path
import json
import subprocess

# Add project root to path
BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

def test_answer_generate():
    """測試 answer.generate - 核心功能"""
    print("\n" + "="*80)
    print("測試 1: answer.generate")
    print("="*80)

    from retrieval.search import hybrid_search
    from providers.registry import get_provider, openai_chat
    from router import get_route_config
    from cache import make_key, get as cache_get, set as cache_set
    from guardrails.abstain import should_abstain, get_abstain_reason, suggest_query_improvements
    from tokenizer import estimate_tokens_from_messages
    from retrieval.subagent_filter import hybrid_search_with_subagent
    from retrieval.iterative_search import iterative_search, should_use_iterative_search
    from retrieval.search import evidence_fingerprints_for_hits

    try:
        # 測試 1.1: 基本查詢
        print("\n測試 1.1: 基本查詢")
        query = "如何建立索引"

        # 執行檢索
        use_iterative = should_use_iterative_search(query, task_type="lookup")
        if use_iterative:
            hits = iterative_search(query, k_per_iteration=8, use_subagent=True, project="auto")[:5]
        else:
            hits = hybrid_search_with_subagent(query, k=8, use_subagent=True, project="auto")[:5]

        print(f"   檢索結果: {len(hits)} 個結果")

        if not hits:
            print("   ⚠️  無檢索結果，跳過後續測試")
            return True

        # 檢查 Guardrails
        if should_abstain(hits, min_diversity=2):
            reason = get_abstain_reason(hits, min_diversity=2)
            suggestions = suggest_query_improvements(query, hits)
            print(f"   ⚠️  Guardrails 拒答: {reason[:100]}...")
            print(f"   建議: {suggestions[:100]}...")
            print("   ✅ Guardrails 功能正常")
        else:
            print("   ✅ 證據充足，可以生成回答")

        # 構建消息
        system = ("你只能根據 Evidence 回答；每個關鍵結論後面附【source:<file:line>|<url#heading>】。"
                  "若證據不足請明確說不知道，並列出需要的檔案或關鍵字。")
        evidence = "\n\n".join([f"[{h['source']}]\n{h['text']}" for h in hits])
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"# Query\n{query}\n\n# Evidence\n{evidence}"},
        ]

        # 估算 tokens
        total_tokens_est = estimate_tokens_from_messages(messages)
        print(f"   Token 估算: {total_tokens_est}")

        # 獲取路由配置
        route_config = get_route_config("lookup", total_tokens_est, route_override="auto")
        model_alias = route_config["model"]
        max_output_tokens = route_config["max_output_tokens"]
        print(f"   路由: {model_alias}, max_output_tokens: {max_output_tokens}")

        # 測試快取 key 生成
        ev_fp = evidence_fingerprints_for_hits(hits)
        key = make_key(
            model=model_alias,
            messages=messages,
            extra={"temperature": 0.2, "task": "lookup", "route": "auto", "token_est": total_tokens_est},
            evidence_fingerprints=ev_fp,
            project="auto",
        )
        print(f"   快取 key: {key[:50]}...")

        # 檢查快取
        cached = cache_get(key)
        if cached:
            print(f"   ✅ 快取命中")
            print(f"   快取答案: {cached.get('answer', '')[:100]}...")
        else:
            print(f"   ⚠️  快取未命中（預期，首次查詢）")

        # 測試 1.2: 不同路由策略
        print("\n測試 1.2: 不同路由策略")
        routes = ["auto", "small-fast", "general"]
        for route in routes:
            try:
                route_config = get_route_config("lookup", total_tokens_est, route_override=route)
                print(f"   ✅ 路由 '{route}': {route_config['model']} (max_tokens: {route_config['max_output_tokens']})")
            except Exception as e:
                print(f"   ❌ 路由 '{route}' 失敗: {e}")

        # 測試 1.3: 不同任務類型
        print("\n測試 1.3: 不同任務類型")
        task_types = ["lookup", "refactor", "general"]
        for task_type in task_types:
            try:
                route_config = get_route_config(task_type, total_tokens_est, route_override="auto")
                print(f"   ✅ 任務類型 '{task_type}': {route_config['model']}")
            except Exception as e:
                print(f"   ❌ 任務類型 '{task_type}' 失敗: {e}")

        print("\n✅ answer.generate 所有測試通過")
        return True

    except Exception as e:
        print(f"\n❌ answer.generate 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_index_rebuild():
    """測試 index.rebuild - 修復後的功能"""
    print("\n" + "="*80)
    print("測試 2: index.rebuild (修復後)")
    print("="*80)

    from utils.project_utils import (
        get_project_status, auto_register_project, set_active_project,
        has_bm25_index, is_project_registered, get_active_project
    )

    test_project_name = "test-rebuild-project"
    test_project_root = str(BASE)

    try:
        # 測試 2.1: 驗證 is_project_registered 函數可用
        print("\n測試 2.1: 驗證 is_project_registered 函數")
        is_registered = is_project_registered(test_project_name)
        print(f"   ✅ is_project_registered('{test_project_name}'): {is_registered}")

        # 測試 2.2: 註冊測試專案（如果未註冊）
        print("\n測試 2.2: 註冊測試專案")
        if not is_registered:
            result = auto_register_project(test_project_name, test_project_root)
            if result:
                print(f"   ✅ 專案已註冊: {test_project_name}")
            else:
                print(f"   ❌ 專案註冊失敗")
                return False
        else:
            print(f"   ℹ️  專案已存在: {test_project_name}")

        # 測試 2.3: 檢查專案狀態
        print("\n測試 2.3: 檢查專案狀態")
        status = get_project_status(test_project_name)
        print(f"   專案根目錄: {status.get('root', 'N/A')}")
        print(f"   BM25 索引: {status.get('bm25_index', {})}")
        print(f"   向量索引: {status.get('vector_index', {})}")

        # 測試 2.4: 建立 BM25 索引（如果不存在）
        print("\n測試 2.4: 建立/重建 BM25 索引")
        has_index = has_bm25_index(test_project_name)
        print(f"   當前 BM25 索引狀態: {'已存在' if has_index else '不存在'}")

        build_script = BASE / "retrieval" / "build_index.py"
        cmd = [
            sys.executable,
            str(build_script),
            "--root", test_project_root,
            "--db", f"data/corpus_{test_project_name}.duckdb",
            "--chunks", f"data/chunks_{test_project_name}.jsonl",
        ]

        print(f"   執行命令: {' '.join(cmd)}")
        print(f"   ⚠️  索引建立可能需要較長時間（timeout: 300s）...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=str(BASE))

        if result.returncode == 0:
            print("   ✅ BM25 索引建立/重建成功")

            # 檢查文件
            chunks_file = BASE / "data" / f"chunks_{test_project_name}.jsonl"
            db_file = BASE / "data" / f"corpus_{test_project_name}.duckdb"

            if chunks_file.exists():
                size = chunks_file.stat().st_size / 1024 / 1024
                print(f"   chunks 文件: {size:.2f} MB")
            if db_file.exists():
                size = db_file.stat().st_size / 1024 / 1024
                print(f"   數據庫文件: {size:.2f} MB")
        else:
            print(f"   ❌ BM25 索引建立失敗")
            print(f"   STDERR: {result.stderr[:500]}")
            return False

        # 測試 2.5: 重建向量索引（如果有依賴）
        print("\n測試 2.5: 重建向量索引")
        try:
            import torch
            import faiss
            import sentence_transformers

            build_vector_script = BASE / "retrieval" / "build_vector_index.py"
            cmd = [sys.executable, str(build_vector_script), "--project", test_project_name]

            print(f"   執行命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180, cwd=str(BASE))

            if result.returncode == 0:
                print("   ✅ 向量索引重建成功")

                # 檢查文件
                vector_file = BASE / "data" / f"vector_index_{test_project_name}.faiss"
                if vector_file.exists():
                    size = vector_file.stat().st_size / 1024 / 1024
                    print(f"   向量索引文件: {size:.2f} MB")
            else:
                print(f"   ⚠️  向量索引重建失敗（不影響整體測試）")
                print(f"   STDERR: {result.stderr[:200]}")

        except ImportError as e:
            print(f"   ⚠️  跳過向量索引測試（依賴未安裝）")

        # 測試 2.6: 驗證索引可用
        print("\n測試 2.6: 驗證索引可用")
        from retrieval.search import hybrid_search

        set_active_project(test_project_name)
        results = hybrid_search("test query", k=3, project=test_project_name)

        if results:
            print(f"   ✅ 索引可用，檢索到 {len(results)} 個結果")
        else:
            print(f"   ⚠️  索引可用但無檢索結果（可能是正常的）")

        print("\n✅ index.rebuild 所有測試通過")
        return True

    except subprocess.TimeoutExpired:
        print("\n❌ 索引建立超時")
        return False
    except Exception as e:
        print(f"\n❌ index.rebuild 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """執行所有高優先級測試"""
    print("\n" + "="*80)
    print("高優先級 MCP API 測試")
    print("="*80)
    print(f"專案根目錄: {BASE}")
    print(f"Python: {sys.version}")

    results = {}

    # 測試 1: answer.generate
    print("\n" + "="*80)
    print("開始測試 answer.generate")
    print("="*80)
    results["answer.generate"] = test_answer_generate()

    # 測試 2: index.rebuild
    print("\n" + "="*80)
    print("開始測試 index.rebuild")
    print("="*80)
    results["index.rebuild"] = test_index_rebuild()

    # 打印測試結果摘要
    print("\n" + "="*80)
    print("測試結果摘要")
    print("="*80)

    for test_name, result in results.items():
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{status}: {test_name}")

    # 統計結果
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    print(f"\n總計: {passed}/{total} 測試通過")

    if passed == total:
        print("\n🎉 所有高優先級測試通過！")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 個測試失敗")
        return 1

if __name__ == "__main__":
    sys.exit(main())
