#!/usr/bin/env python
"""
MCP API 完整性驗證測試
測試所有 MCP 工具的功能是否正常

使用方式:
    python scripts/test_mcp_apis.py

依賴:
    - .venv 已安裝所有依賴
    - 當前目錄有可索引的文件
"""

import sys
import os
import json
from pathlib import Path

# 添加專案根目錄到 path
BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

def test_imports():
    """測試所有必要的導入"""
    print("\n" + "=" * 80)
    print("測試 1: 檢查依賴導入")
    print("=" * 80)

    results = {}

    # 基礎依賴
    try:
        import duckdb
        results["duckdb"] = f"✅ {duckdb.__version__}"
    except ImportError as e:
        results["duckdb"] = f"❌ {e}"

    try:
        from memory.longterm import get_mem, set_mem
        results["memory"] = "✅ 長期記憶模組"
    except Exception as e:
        results["memory"] = f"❌ {e}"

    try:
        from retrieval.search import hybrid_search
        results["retrieval"] = "✅ 檢索模組"
    except Exception as e:
        results["retrieval"] = f"❌ {e}"

    try:
        from cache import get as cache_get, set as cache_set
        results["cache"] = "✅ 快取模組"
    except Exception as e:
        results["cache"] = f"❌ {e}"

    try:
        from memory.tasks import TaskManager
        results["tasks"] = "✅ 任務管理模組"
    except Exception as e:
        results["tasks"] = f"❌ {e}"

    # 向量檢索依賴（可選）
    try:
        import torch
        import faiss
        import sentence_transformers
        results["vector"] = f"✅ PyTorch {torch.__version__}, FAISS {faiss.__version__}, sentence-transformers {sentence_transformers.__version__}"
    except ImportError as e:
        results["vector"] = f"⚠️  未安裝（可選）: {e}"

    for module, status in results.items():
        print(f"{module:20s}: {status}")

    all_ok = all("✅" in v for v in results.values() if "vector" not in v)
    return all_ok

def test_project_utils():
    """測試專案管理工具"""
    print("\n" + "=" * 80)
    print("測試 2: 專案管理工具")
    print("=" * 80)

    from utils.project_utils import (
        get_project_status, auto_register_project, set_active_project,
        has_bm25_index, get_active_project
    )

    project_name = "augment-lite-mcp-test"
    project_root = str(BASE)

    try:
        # 測試自動註冊
        print(f"測試自動註冊: {project_name}")
        result = auto_register_project(project_name, project_root)
        print(f"  註冊結果: {'✅ 成功' if result else '❌ 失敗'}")

        # 測試設為活動專案
        print(f"測試設為活動專案")
        set_active_project(project_name)
        active = get_active_project()
        print(f"  活動專案: {active} {'✅' if active == project_name else '❌'}")

        # 測試專案狀態
        print(f"測試專案狀態")
        status = get_project_status(project_name)
        print(f"  專案根目錄: {status.get('root', 'N/A')}")
        print(f"  註冊時間: {status.get('registered', 'N/A')}")

        # 測試 BM25 索引狀態
        has_index = has_bm25_index(project_name)
        print(f"  BM25 索引: {'✅ 已建立' if has_index else '❌ 未建立'}")

        return True
    except Exception as e:
        print(f"❌ 專案管理工具測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_bm25_index():
    """測試 BM25 索引建立"""
    print("\n" + "=" * 80)
    print("測試 3: BM25 索引建立")
    print("=" * 80)

    import subprocess

    project_name = "augment-lite-mcp-test"

    try:
        build_script = BASE / "retrieval" / "build_index.py"
        cmd = [
            sys.executable,
            str(build_script),
            "--root", str(BASE),
            "--db", f"data/corpus_{project_name}.duckdb",
            "--chunks", f"data/chunks_{project_name}.jsonl",
        ]

        print(f"執行命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode == 0:
            print("✅ BM25 索引建立成功")
            # 檢查生成的文件
            chunks_file = BASE / "data" / f"chunks_{project_name}.jsonl"
            db_file = BASE / "data" / f"corpus_{project_name}.duckdb"

            if chunks_file.exists():
                size = chunks_file.stat().st_size / 1024 / 1024
                print(f"  chunks 文件: {chunks_file} ({size:.2f} MB)")
            if db_file.exists():
                size = db_file.stat().st_size / 1024 / 1024
                print(f"  數據庫文件: {db_file} ({size:.2f} MB)")
            return True
        else:
            print(f"❌ BM25 索引建立失敗")
            print(f"  STDERR: {result.stderr[:500]}")
            return False

    except subprocess.TimeoutExpired:
        print("❌ BM25 索引建立超時 (>120s)")
        return False
    except Exception as e:
        print(f"❌ BM25 索引建立失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_vector_index():
    """測試向量索引建立（可選）"""
    print("\n" + "=" * 80)
    print("測試 4: 向量索引建立 (可選)")
    print("=" * 80)

    try:
        import torch
        import faiss
        import sentence_transformers
    except ImportError as e:
        print(f"⚠️  跳過: 向量檢索依賴未安裝")
        print(f"   安裝方法: bash scripts/install_vector_deps.sh")
        return True  # 不影響整體測試

    import subprocess

    project_name = "augment-lite-mcp-test"

    try:
        build_script = BASE / "retrieval" / "build_vector_index.py"
        cmd = [sys.executable, str(build_script), "--project", project_name]

        print(f"執行命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)

        if result.returncode == 0:
            print("✅ 向量索引建立成功")
            # 檢查生成的文件
            vector_file = BASE / "data" / f"vector_index_{project_name}.faiss"
            if vector_file.exists():
                size = vector_file.stat().st_size / 1024 / 1024
                print(f"  向量索引文件: {vector_file} ({size:.2f} MB)")
            return True
        else:
            print(f"❌ 向量索引建立失敗")
            print(f"  STDOUT: {result.stdout[:500]}")
            print(f"  STDERR: {result.stderr[:500]}")
            return False

    except subprocess.TimeoutExpired:
        print("❌ 向量索引建立超時 (>180s)")
        return False
    except Exception as e:
        print(f"❌ 向量索引建立失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_rag_search():
    """測試 RAG 檢索"""
    print("\n" + "=" * 80)
    print("測試 5: RAG 檢索")
    print("=" * 80)

    from retrieval.search import hybrid_search
    from utils.project_utils import set_active_project

    project_name = "augment-lite-mcp-test"
    set_active_project(project_name)

    try:
        query = "如何初始化專案"
        print(f"測試查詢: '{query}'")

        results = hybrid_search(query, k=5, project=project_name)

        if results and len(results) > 0:
            print(f"✅ 檢索成功，返回 {len(results)} 個結果")
            for i, result in enumerate(results[:3], 1):
                source = result.get("source", "unknown")
                score = result.get("score", 0.0)
                text_preview = result.get("text", "")[:100]
                print(f"  {i}. {source} (score: {score:.3f})")
                print(f"     {text_preview}...")
            return True
        else:
            print("❌ 檢索失敗，返回空結果")
            return False

    except Exception as e:
        print(f"❌ RAG 檢索失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_memory():
    """測試長期記憶"""
    print("\n" + "=" * 80)
    print("測試 6: 長期記憶")
    print("=" * 80)

    from memory.longterm import get_mem, set_mem

    project_name = "augment-lite-mcp-test"

    try:
        # 測試寫入
        key = "test_key"
        value = "test_value_123"
        print(f"測試寫入: set_mem('{key}', '{value}')")
        set_mem(key, value, project=project_name)
        print("  ✅ 寫入成功")

        # 測試讀取
        print(f"測試讀取: get_mem('{key}')")
        retrieved = get_mem(key, project=project_name)
        print(f"  讀取結果: '{retrieved}'")

        if retrieved == value:
            print("  ✅ 讀取成功，值匹配")
            return True
        else:
            print(f"  ❌ 讀取失敗，期望 '{value}'，實際 '{retrieved}'")
            return False

    except Exception as e:
        print(f"❌ 長期記憶測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_tasks():
    """測試任務管理"""
    print("\n" + "=" * 80)
    print("測試 7: 任務管理")
    print("=" * 80)

    from memory.tasks import TaskManager

    project_name = "augment-lite-mcp-test"
    tm = TaskManager(project=project_name)

    try:
        # 測試添加任務
        print("測試添加任務")
        task_id = tm.add_task(
            title="測試任務",
            description="這是一個測試任務",
            priority=1
        )
        print(f"  ✅ 任務已添加, ID: {task_id}")

        # 測試列出任務
        print("測試列出任務")
        tasks = tm.list_tasks()
        print(f"  任務總數: {len(tasks)}")
        if tasks:
            print(f"  最新任務: {tasks[0]}")

        # 測試更新任務
        print("測試更新任務狀態")
        tm.update_task(task_id, status="in_progress")
        task = tm.get_task(task_id)
        print(f"  任務狀態: {task.get('status')}")

        # 測試完成任務
        print("測試完成任務")
        tm.update_task(task_id, status="done")
        task = tm.get_task(task_id)
        print(f"  ✅ 任務已完成")

        return True

    except Exception as e:
        print(f"❌ 任務管理測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cache():
    """測試快取系統"""
    print("\n" + "=" * 80)
    print("測試 8: 快取系統")
    print("=" * 80)

    from cache import make_key, get as cache_get, set as cache_set

    project_name = "augment-lite-mcp-test"

    try:
        # 測試快取 key 生成
        query = "test query"
        route = "small-fast"
        key = make_key(query, route, project=project_name)
        print(f"快取 key: {key}")

        # 測試寫入快取
        value = {"answer": "test answer", "cached": False}
        print(f"測試寫入快取")
        cache_set(key, value, ttl=60)
        print("  ✅ 寫入成功")

        # 測試讀取快取
        print(f"測試讀取快取")
        retrieved = cache_get(key)

        if retrieved:
            print(f"  ✅ 快取命中")
            print(f"  快取內容: {retrieved}")
            return True
        else:
            print(f"  ❌ 快取未命中")
            return False

    except Exception as e:
        print(f"❌ 快取系統測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主測試函數"""
    print("\n" + "=" * 80)
    print("MCP API 完整性驗證測試")
    print("=" * 80)
    print(f"專案根目錄: {BASE}")
    print(f"Python: {sys.version}")

    tests = [
        ("依賴導入", test_imports),
        ("專案管理工具", test_project_utils),
        ("BM25 索引建立", test_bm25_index),
        ("向量索引建立", test_vector_index),
        ("RAG 檢索", test_rag_search),
        ("長期記憶", test_memory),
        ("任務管理", test_tasks),
        ("快取系統", test_cache),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = "✅ 通過" if result else "❌ 失敗"
        except Exception as e:
            results[test_name] = f"❌ 異常: {str(e)[:50]}"

    # 打印測試結果摘要
    print("\n" + "=" * 80)
    print("測試結果摘要")
    print("=" * 80)

    for test_name, result in results.items():
        print(f"{test_name:20s}: {result}")

    # 統計結果
    passed = sum(1 for r in results.values() if "✅" in r)
    total = len(results)
    print("\n" + "=" * 80)
    print(f"總計: {passed}/{total} 測試通過")
    print("=" * 80)

    if passed == total:
        print("\n🎉 所有測試通過！MCP API 功能完整。")
        return 0
    else:
        print("\n⚠️  部分測試失敗，請檢查上面的錯誤信息。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
