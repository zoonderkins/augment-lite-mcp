#!/usr/bin/env python3
"""
Test Memory API (memory.get, memory.set, memory.delete, memory.list, memory.clear)

Tests:
1. memory.set - 设置 memory
2. memory.get - 获取 memory
3. memory.list - 列出所有 memory
4. memory.delete - 删除单个 memory
5. memory.clear - 清空所有 memory
6. Project isolation - 项目隔离测试
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from memory.longterm import get_mem, set_mem, delete_mem, list_mem
from utils.project_utils import clear_memory

def test_memory_set_get():
    """Test memory.set and memory.get"""
    print("\n=== Test 1: memory.set & memory.get ===")
    
    # Set memory
    set_mem("test_key", "test_value", project="test_project")
    
    # Get memory
    value = get_mem("test_key", project="test_project")
    
    assert value == "test_value", f"Expected 'test_value', got '{value}'"
    print("✅ memory.set & memory.get works correctly")

def test_memory_list():
    """Test memory.list"""
    print("\n=== Test 2: memory.list ===")
    
    # Set multiple memories
    set_mem("key1", "value1", project="test_project")
    set_mem("key2", "value2", project="test_project")
    set_mem("key3", "value3", project="test_project")
    
    # List memories
    items = list_mem(project="test_project")
    
    # Convert to dict for easier checking
    mem_dict = {k: v for k, v, _ in items}
    
    assert len(mem_dict) >= 3, f"Expected at least 3 items, got {len(mem_dict)}"
    assert mem_dict["key1"] == "value1", "key1 value mismatch"
    assert mem_dict["key2"] == "value2", "key2 value mismatch"
    assert mem_dict["key3"] == "value3", "key3 value mismatch"
    
    print(f"✅ memory.list returns {len(mem_dict)} items correctly")

def test_memory_delete():
    """Test memory.delete"""
    print("\n=== Test 3: memory.delete ===")
    
    # Set memory
    set_mem("to_delete", "delete_me", project="test_project")
    
    # Verify it exists
    value = get_mem("to_delete", project="test_project")
    assert value == "delete_me", "Memory not set correctly"
    
    # Delete memory
    delete_mem("to_delete", project="test_project")
    
    # Verify it's deleted
    value = get_mem("to_delete", project="test_project")
    assert value is None, f"Expected None after delete, got '{value}'"
    
    print("✅ memory.delete works correctly")

def test_memory_clear():
    """Test memory.clear"""
    print("\n=== Test 4: memory.clear ===")
    
    # Set some memories
    set_mem("clear1", "value1", project="test_project")
    set_mem("clear2", "value2", project="test_project")
    
    # Verify they exist
    items = list_mem(project="test_project")
    assert len(items) >= 2, "Memories not set correctly"
    
    # Clear all memories
    result = clear_memory(project="test_project")
    assert result["ok"] is True, "Clear memory failed"
    
    # Verify they're cleared
    items = list_mem(project="test_project")
    assert len(items) == 0, f"Expected 0 items after clear, got {len(items)}"
    
    print("✅ memory.clear works correctly")

def test_project_isolation():
    """Test project isolation"""
    print("\n=== Test 5: Project Isolation ===")
    
    # Set memories in different projects
    set_mem("shared_key", "project_a_value", project="project_a")
    set_mem("shared_key", "project_b_value", project="project_b")
    
    # Get memories from different projects
    value_a = get_mem("shared_key", project="project_a")
    value_b = get_mem("shared_key", project="project_b")
    
    assert value_a == "project_a_value", f"Project A value mismatch: {value_a}"
    assert value_b == "project_b_value", f"Project B value mismatch: {value_b}"
    
    # List memories for each project
    items_a = list_mem(project="project_a")
    items_b = list_mem(project="project_b")
    
    mem_dict_a = {k: v for k, v, _ in items_a}
    mem_dict_b = {k: v for k, v, _ in items_b}
    
    assert mem_dict_a["shared_key"] == "project_a_value", "Project A list mismatch"
    assert mem_dict_b["shared_key"] == "project_b_value", "Project B list mismatch"
    
    # Clear project A should not affect project B
    clear_memory(project="project_a")
    
    items_a = list_mem(project="project_a")
    items_b = list_mem(project="project_b")
    
    assert len(items_a) == 0, "Project A should be cleared"
    assert len(items_b) >= 1, "Project B should not be affected"
    
    # Cleanup project B
    clear_memory(project="project_b")
    
    print("✅ Project isolation works correctly")

def test_global_memory():
    """Test global memory (project=None)"""
    print("\n=== Test 6: Global Memory ===")
    
    # Set global memory
    set_mem("global_key", "global_value", project=None)
    
    # Get global memory
    value = get_mem("global_key", project=None)
    assert value == "global_value", f"Expected 'global_value', got '{value}'"
    
    # List global memory
    items = list_mem(project=None)
    mem_dict = {k: v for k, v, _ in items}
    assert "global_key" in mem_dict, "Global key not found in list"
    
    # Delete global memory
    delete_mem("global_key", project=None)
    value = get_mem("global_key", project=None)
    assert value is None, "Global memory not deleted"
    
    print("✅ Global memory works correctly")

def cleanup():
    """Cleanup test data"""
    print("\n=== Cleanup ===")
    
    # Clear all test projects
    clear_memory(project="test_project")
    clear_memory(project="project_a")
    clear_memory(project="project_b")
    clear_memory(project=None)
    
    print("✅ Cleanup completed")

def main():
    print("=" * 60)
    print("Memory API Test Suite")
    print("=" * 60)
    
    try:
        # Run tests
        test_memory_set_get()
        test_memory_list()
        test_memory_delete()
        test_memory_clear()
        test_project_isolation()
        test_global_memory()
        
        # Cleanup
        cleanup()
        
        print("\n" + "=" * 60)
        print("✅ All Memory API tests passed!")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        cleanup()
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        cleanup()
        return 1

if __name__ == "__main__":
    sys.exit(main())
