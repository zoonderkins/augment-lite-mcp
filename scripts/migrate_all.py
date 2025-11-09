#!/usr/bin/env python3
"""
Migrate all databases to support multi-project.

This script runs all migration scripts in order:
1. Memory database migration
2. Cache database migration
"""

import sys
import subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

def run_migration(script_name: str) -> bool:
    """Run a migration script."""
    script_path = BASE / "scripts" / script_name
    
    if not script_path.exists():
        print(f"❌ Migration script not found: {script_name}")
        return False
    
    print(f"\n{'=' * 60}")
    print(f"Running: {script_name}")
    print('=' * 60)
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            check=False,
            capture_output=False,
            text=True
        )
        
        if result.returncode != 0:
            print(f"⚠️  {script_name} returned non-zero exit code: {result.returncode}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Error running {script_name}: {e}")
        return False

def main():
    print("=" * 60)
    print("Multi-Project Migration Tool")
    print("=" * 60)
    print()
    print("This script will migrate all databases to support multi-project:")
    print("  1. Memory database (memory.sqlite)")
    print("  2. Cache database (response_cache.sqlite)")
    print()
    
    # Ask for confirmation
    response = input("Continue? [y/N]: ").strip().lower()
    if response not in ('y', 'yes'):
        print("❌ Migration cancelled.")
        return 1
    
    print()
    
    # Run migrations
    migrations = [
        "migrate_memory.py",
        "migrate_cache.py",
    ]
    
    results = {}
    for migration in migrations:
        results[migration] = run_migration(migration)
    
    # Summary
    print()
    print("=" * 60)
    print("Migration Summary")
    print("=" * 60)
    
    all_success = True
    for migration, success in results.items():
        status = "✅ Success" if success else "❌ Failed"
        print(f"{status}: {migration}")
        if not success:
            all_success = False
    
    print()
    
    if all_success:
        print("🎉 All migrations completed successfully!")
        print()
        print("Next steps:")
        print("  1. Restart your MCP server (if running)")
        print("  2. Test multi-project functionality:")
        print()
        print("     # Switch projects")
        print("     python retrieval/multi_project.py activate miceai")
        print()
        print("     # Use project-specific memory")
        print("     memory.set(key='status', value='...', project='auto')")
        print()
        print("     # Cache is now project-aware")
        print("     # (automatically handled by answer.generate)")
        print()
        return 0
    else:
        print("⚠️  Some migrations failed. Please check the errors above.")
        print("   Your data is safe (backups were created).")
        return 1

if __name__ == "__main__":
    exit(main())

