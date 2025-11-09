#!/usr/bin/env python3
"""
測試所有 12 個 MCP API 功能
"""

import sys
from pathlib import Path

# Add project root to path
BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

import json
from retrieval.search import hybrid_search
from memory.longterm import get_mem, set_mem
from memory.tasks import TaskManager

def test_rag_search():
    """測試 1: rag.search"""
    print("\n" + "="*60)
    print("測試 1: rag.search")
    print("="*60)
    
    try:
        results = hybrid_search("golang go version", k=3, project="auto")
        print(f"✅ 成功: 找到 {len(results)} 個結果")
        
        # 檢查結果格式
        if results:
            first = results[0]
            assert "text" in first, "缺少 'text' 欄位"
            assert "source" in first, "缺少 'source' 欄位"
            assert "score" in first, "缺少 'score' 欄位"
            print(f"   第一個結果: {first['source'][:50]}...")
            print(f"   分數: {first['score']:.4f}")
        
        return True
    except Exception as e:
        print(f"❌ 失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_memory_get_set():
    """測試 2-3: memory.get 和 memory.set"""
    print("\n" + "="*60)
    print("測試 2-3: memory.get 和 memory.set")
    print("="*60)
    
    try:
        # 測試 set
        set_mem("test_key", "test_value_123", project="auto")
        print("✅ memory.set 成功")
        
        # 測試 get
        value = get_mem("test_key", project="auto")
        assert value == "test_value_123", f"值不匹配: {value}"
        print(f"✅ memory.get 成功: {value}")
        
        # 清理
        set_mem("test_key", "", project="auto")
        
        return True
    except Exception as e:
        print(f"❌ 失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_task_apis():
    """測試 4-12: 所有 Task API"""
    print("\n" + "="*60)
    print("測試 4-12: Task APIs")
    print("="*60)

    try:
        tm = TaskManager(project="auto")

        # 清理所有現有任務
        existing_tasks = tm.list_tasks()
        for task in existing_tasks:
            tm.delete_task(task["id"], delete_subtasks=True)
        print(f"清理了 {len(existing_tasks)} 個現有任務")
        
        # 測試 4: task.add
        print("\n測試 4: task.add")
        task_id = tm.add_task(
            title="測試任務",
            description="這是一個測試任務",
            priority=5
        )
        print(f"✅ task.add 成功: task_id={task_id}")
        
        # 測試 5: task.list
        print("\n測試 5: task.list")
        tasks = tm.list_tasks()
        print(f"✅ task.list 成功: 找到 {len(tasks)} 個任務")
        
        # 測試 6: task.get
        print("\n測試 6: task.get")
        task = tm.get_task(task_id)
        assert task is not None, "任務不存在"
        assert task["title"] == "測試任務", "標題不匹配"
        print(f"✅ task.get 成功: {task['title']}")
        
        # 測試 7: task.update
        print("\n測試 7: task.update")
        success = tm.update_task(
            task_id=task_id,
            title="更新後的任務",
            status="in_progress"
        )
        assert success, "更新失敗"
        task = tm.get_task(task_id)
        assert task["title"] == "更新後的任務", "標題未更新"
        assert task["status"] == "in_progress", "狀態未更新"
        print(f"✅ task.update 成功")
        
        # 測試 8: task.current
        print("\n測試 8: task.current")
        current = tm.get_current_task()
        assert current is not None, "沒有進行中的任務"
        assert current["id"] == task_id, "當前任務 ID 不匹配"
        print(f"✅ task.current 成功: {current['title']}")
        
        # 測試 9: task.resume (先設為 pending，再 resume)
        print("\n測試 9: task.resume")
        tm.update_task(task_id=task_id, status="pending")
        resumed = tm.resume_task(task_id)
        assert resumed is not None, "恢復失敗"
        assert resumed["status"] == "in_progress", "狀態未恢復"
        print(f"✅ task.resume 成功")
        
        # 測試 10: task.stats
        print("\n測試 10: task.stats")
        stats = tm.get_stats()
        assert "total" in stats, "缺少 total"
        # stats 格式: {"pending": 0, "in_progress": 1, "done": 0, "cancelled": 0, "total": 1}
        assert stats["total"] > 0, "total 應該大於 0"
        print(f"✅ task.stats 成功: total={stats['total']}")
        print(f"   狀態統計: pending={stats.get('pending', 0)}, in_progress={stats.get('in_progress', 0)}, done={stats.get('done', 0)}, cancelled={stats.get('cancelled', 0)}")
        
        # 測試 11: task.add (子任務)
        print("\n測試 11: task.add (子任務)")
        subtask_id = tm.add_task(
            title="子任務",
            description="這是一個子任務",
            parent_id=task_id
        )
        print(f"✅ task.add (子任務) 成功: subtask_id={subtask_id}")
        
        # 測試 12: task.delete
        print("\n測試 12: task.delete")
        success = tm.delete_task(task_id, delete_subtasks=True)
        assert success, "刪除失敗"
        task = tm.get_task(task_id)
        assert task is None, "任務仍然存在"
        print(f"✅ task.delete 成功")
        
        return True
    except Exception as e:
        print(f"❌ 失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """執行所有測試"""
    print("\n" + "="*60)
    print("augment-lite-mcp v0.4.0 - 完整 API 測試")
    print("="*60)
    
    results = []
    
    # 測試 1: rag.search
    results.append(("rag.search", test_rag_search()))
    
    # 測試 2-3: memory APIs
    results.append(("memory.get/set", test_memory_get_set()))
    
    # 測試 4-12: task APIs
    results.append(("task APIs", test_task_apis()))
    
    # 總結
    print("\n" + "="*60)
    print("測試總結")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{status}: {name}")
    
    print(f"\n總計: {passed}/{total} 通過")
    
    if passed == total:
        print("\n🎉 所有測試通過！")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 個測試失敗")
        return 1

if __name__ == "__main__":
    sys.exit(main())

