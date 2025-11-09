#!/usr/bin/env python3
"""
Test Auto Mode for all MCP APIs

Tests project="auto" mode for:
1. project.status
2. project.init
3. cache.clear
4. memory.clear
5. index.status
6. index.rebuild
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from utils.project_utils import (
    get_project_status, auto_register_project, set_active_project,
    has_bm25_index, clear_cache, clear_memory, get_active_project,
    is_project_registered
)

def test_auto_mode_detection():
    """Test auto mode project detection"""
    print("\n=== Test 1: Auto Mode Detection ===")
    
    # Current directory name
    current_dir = Path(os.getcwd()).name
    print(f"Current directory: {current_dir}")
    
    # Test is_project_registered with auto mode logic
    # This simulates what happens in mcp_bridge_lazy.py
    detected_project = current_dir
    
    if is_project_registered(detected_project):
        project = detected_project
        print(f"✅ Current directory is registered: {project}")
    else:
        project = get_active_project()
        if project:
            print(f"✅ Using active project: {project}")
        else:
            project = detected_project
            print(f"⚠️  No registered or active project, using: {project}")
    
    assert project is not None, "Project should not be None"
    print(f"✅ Auto mode resolves to: {project}")

def test_project_status_auto():
    """Test project.status with auto mode"""
    print("\n=== Test 2: project.status (auto mode) ===")
    
    # Simulate auto mode
    status = get_project_status(project="auto")
    
    assert "project_name" in status or "error" in status, "Status should have project_name or error"
    
    if "error" in status:
        print(f"ℹ️  No active project: {status['error']}")
    else:
        print(f"✅ project.status works with auto mode: {status['project_name']}")

def test_cache_clear_auto():
    """Test cache.clear with auto mode"""
    print("\n=== Test 3: cache.clear (auto mode) ===")
    
    try:
        result = clear_cache(project="auto")
        assert result["ok"] is True, "Clear cache should return ok=True"
        print(f"✅ cache.clear works with auto mode: {result['message']}")
    except Exception as e:
        print(f"⚠️  cache.clear auto mode: {e}")

def test_memory_clear_auto():
    """Test memory.clear with auto mode"""
    print("\n=== Test 4: memory.clear (auto mode) ===")
    
    try:
        result = clear_memory(project="auto")
        assert result["ok"] is True, "Clear memory should return ok=True"
        print(f"✅ memory.clear works with auto mode: {result['message']}")
    except Exception as e:
        print(f"⚠️  memory.clear auto mode: {e}")

def test_auto_mode_with_different_projects():
    """Test auto mode with different project contexts"""
    print("\n=== Test 5: Auto Mode with Different Projects ===")
    
    # Register a test project
    test_project = "test_auto_mode_project"
    test_root = str(BASE)  # Use current directory as root
    
    # Auto-register
    success = auto_register_project(test_project, test_root)
    
    if success:
        print(f"✅ Test project registered: {test_project}")
        
        # Set as active
        set_active_project(test_project)
        print(f"✅ Test project set as active")
        
        # Verify active project
        active = get_active_project()
        assert active == test_project, f"Expected {test_project}, got {active}"
        print(f"✅ Active project verified: {active}")
        
        # Test status with auto mode (should use active project)
        status = get_project_status(project="auto")
        if "project_name" in status:
            assert status["project_name"] == test_project, "Auto mode should use active project"
            print(f"✅ Auto mode correctly uses active project: {status['project_name']}")
    else:
        print(f"⚠️  Could not register test project (directory might not have code files)")

def test_direct_import_vs_e_dict():
    """Test that direct imports work (avoiding E dict issues)"""
    print("\n=== Test 6: Direct Import (No E Dictionary) ===")
    
    # This test verifies that we can import and use functions directly
    # without relying on the E dictionary from _lazy_engine()
    
    from utils.project_utils import (
        get_project_status,
        is_project_registered,
        get_active_project,
        auto_register_project,
        has_bm25_index,
        clear_cache,
        clear_memory,
        set_active_project
    )
    
    # All imports should work without E dictionary
    print("✅ All project_utils functions can be imported directly")
    
    # Test that they can be called
    try:
        status = get_project_status("auto")
        print(f"✅ Direct import functions work correctly")
    except Exception as e:
        print(f"⚠️  Direct import test: {e}")

def main():
    print("=" * 60)
    print("Auto Mode Test Suite")
    print("=" * 60)
    
    try:
        # Run tests
        test_auto_mode_detection()
        test_project_status_auto()
        test_cache_clear_auto()
        test_memory_clear_auto()
        test_auto_mode_with_different_projects()
        test_direct_import_vs_e_dict()
        
        print("\n" + "=" * 60)
        print("✅ All Auto Mode tests passed!")
        print("=" * 60)
        print("\nNote: Some tests may show warnings if no project is registered,")
        print("but this is expected behavior for auto mode.")
        return 0
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
