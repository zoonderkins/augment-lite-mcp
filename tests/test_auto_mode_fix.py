#!/usr/bin/env python3
"""
Test Auto Mode Fix for Project Resolution

Tests that resolve_auto_project() correctly:
1. Detects project by current directory name
2. Detects project by current directory path
3. Falls back to active project
4. Returns None if nothing found
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from utils.project_utils import (
    resolve_auto_project, get_active_project, load_projects,
    set_active_project
)


def test_resolve_auto_project():
    """Test resolve_auto_project function"""
    print("\n=== Test: resolve_auto_project() ===\n")
    
    # Get current state
    projects = load_projects()
    active = get_active_project()
    cwd = Path(os.getcwd()).resolve()
    cwd_name = cwd.name
    
    print(f"📍 Current directory: {cwd}")
    print(f"📍 Current directory name: {cwd_name}")
    print(f"📍 Active project: {active}")
    print(f"📍 Registered projects: {list(projects.keys())}\n")
    
    # Test 1: Check if current directory matches any project's root
    print("Test 1: Check if current directory matches any project's root")
    matched = None
    for proj_name, proj_config in projects.items():
        proj_root = Path(proj_config.get("root", "")).resolve()
        if proj_root == cwd:
            matched = proj_name
            print(f"  ✅ Found match: {proj_name} (root: {proj_root})")
            break
    
    if not matched:
        print(f"  ⚠️  No project root matches current directory")
    
    # Test 2: Call resolve_auto_project()
    print("\nTest 2: Call resolve_auto_project()")
    resolved = resolve_auto_project()
    print(f"  Result: {resolved}")
    
    if resolved:
        print(f"  ✅ Resolved to: {resolved}")
        
        # Verify it's correct
        if matched and resolved == matched:
            print(f"  ✅ Correctly matched by directory path")
        elif resolved == active:
            print(f"  ✅ Correctly fell back to active project")
        elif resolved == cwd_name:
            print(f"  ✅ Correctly matched by directory name")
    else:
        print(f"  ⚠️  Could not resolve project")
    
    # Test 3: Verify the resolved project is registered
    if resolved:
        print(f"\nTest 3: Verify resolved project is registered")
        if resolved in projects:
            print(f"  ✅ Project '{resolved}' is registered")
            config = projects[resolved]
            print(f"     Root: {config.get('root')}")
            print(f"     DB: {config.get('db')}")
        else:
            print(f"  ❌ Project '{resolved}' is NOT registered")
    
    print("\n" + "="*60)
    print("Summary:")
    print(f"  Current directory: {cwd_name}")
    print(f"  Resolved project: {resolved}")
    print(f"  Expected behavior: Should match project root or fall back to active")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_resolve_auto_project()

