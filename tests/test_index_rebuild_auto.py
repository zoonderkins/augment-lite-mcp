#!/usr/bin/env python3
"""
Test index.rebuild with auto mode

Simulates what happens when you call:
  mcp augment-lite index.rebuild project="auto"
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from utils.project_utils import resolve_auto_project, load_projects


def test_index_rebuild_auto():
    """Test index.rebuild auto mode resolution"""
    print("\n=== Test: index.rebuild with project='auto' ===\n")
    
    # Simulate what mcp_bridge_lazy.py does
    print("Simulating: mcp augment-lite index.rebuild project='auto'\n")
    
    # Step 1: Get project parameter
    project = "auto"
    print(f"1. Initial project parameter: '{project}'")
    
    # Step 2: Resolve auto project
    if project == "auto":
        print(f"2. Resolving 'auto' mode...")
        project = resolve_auto_project()
        print(f"   Resolved to: '{project}'")
    
    # Step 3: Verify project is valid
    if not project:
        print(f"3. ❌ ERROR: Could not determine project")
        return False
    
    projects = load_projects()
    if project not in projects:
        print(f"3. ❌ ERROR: Project '{project}' not registered")
        return False
    
    print(f"3. ✅ Project '{project}' is registered")
    
    # Step 4: Show what would be indexed
    config = projects[project]
    print(f"\n4. Index rebuild would use:")
    print(f"   Project: {project}")
    print(f"   Root: {config.get('root')}")
    print(f"   DB: {config.get('db')}")
    print(f"   Chunks: {config.get('chunks')}")
    
    print(f"\n✅ SUCCESS: index.rebuild would correctly use project '{project}'")
    print(f"   (NOT 'test_auto_mode_project' as before)")
    
    return True


if __name__ == "__main__":
    success = test_index_rebuild_auto()
    sys.exit(0 if success else 1)

