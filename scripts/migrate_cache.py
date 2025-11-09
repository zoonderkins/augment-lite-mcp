#!/usr/bin/env python3
"""
Migrate existing response_cache.sqlite to support multi-project.

This script:
1. Backs up the existing response_cache.sqlite
2. Migrates data to new schema with project column
3. All existing data is moved to global cache (project="")
"""

import sqlite3
import shutil
import os
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parents[1]
DB_PATH = BASE / "data" / "response_cache.sqlite"

def backup_database():
    """Create a backup of the existing database."""
    if not DB_PATH.exists():
        print("ℹ️  No existing response_cache.sqlite found. Nothing to migrate.")
        return False
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = DB_PATH.parent / f"response_cache.sqlite.backup_{timestamp}"
    
    shutil.copy2(DB_PATH, backup_path)
    print(f"✅ Backup created: {backup_path}")
    return True

def check_schema():
    """Check if migration is needed."""
    if not DB_PATH.exists():
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Check if 'project' column exists
    cur.execute("PRAGMA table_info(cache)")
    columns = [row[1] for row in cur.fetchall()]
    conn.close()
    
    if "project" in columns:
        print("ℹ️  Database already migrated. No action needed.")
        return False
    
    return True

def migrate():
    """Migrate the database schema."""
    print("🔄 Starting migration...")
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # 1. Rename old table
    cur.execute("ALTER TABLE cache RENAME TO cache_old")
    print("  ✓ Renamed old table")
    
    # 2. Create new table with project column
    cur.execute("""CREATE TABLE cache (
        project TEXT NOT NULL,
        k TEXT NOT NULL,
        v TEXT NOT NULL,
        expire_at INTEGER NOT NULL,
        PRIMARY KEY (project, k)
    )""")
    print("  ✓ Created new table")
    
    # 3. Migrate data (all to global cache, project="")
    cur.execute("""
        INSERT INTO cache (project, k, v, expire_at)
        SELECT '', k, v, expire_at FROM cache_old
    """)
    migrated_count = cur.rowcount
    print(f"  ✓ Migrated {migrated_count} records to global cache")
    
    # 4. Drop old table
    cur.execute("DROP TABLE cache_old")
    print("  ✓ Dropped old table")
    
    conn.commit()
    conn.close()
    
    print("✅ Migration completed successfully!")
    print(f"   {migrated_count} records migrated to global cache (project='')")

def main():
    print("=" * 60)
    print("Response Cache Database Migration Tool")
    print("=" * 60)
    print()
    
    # Check if migration is needed
    if not check_schema():
        return
    
    # Backup
    if not backup_database():
        return
    
    # Migrate
    try:
        migrate()
        print()
        print("=" * 60)
        print("Migration Summary:")
        print("=" * 60)
        print("✅ All existing cache entries are now in global cache")
        print("✅ Cache is now project-aware:")
        print()
        print("   # Global cache (all projects)")
        print("   cache.set(key, value, project=None)")
        print()
        print("   # Active project cache")
        print("   cache.set(key, value, project='auto')")
        print()
        print("   # Specific project cache")
        print("   cache.set(key, value, project='miceai')")
        print()
        print("⚠️  Note: Cache keys now include project information")
        print("   Old cache entries will not be hit after switching projects")
        print()
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        print("   Your backup is safe. Please check the error and try again.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())

