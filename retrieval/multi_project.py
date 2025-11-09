#!/usr/bin/env python3
"""
Multi-project index management for augment-lite-mcp

Usage:
    # Add/update a project
    python retrieval/multi_project.py add miceai /Users/lol/temp/rd00010-miceai
    
    # List all projects
    python retrieval/multi_project.py list
    
    # Remove a project
    python retrieval/multi_project.py remove miceai
    
    # Rebuild all projects
    python retrieval/multi_project.py rebuild
    
    # Set active project (for search)
    python retrieval/multi_project.py activate miceai
"""

import argparse
import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional
import hashlib

BASE = Path(__file__).resolve().parents[1]
PROJECTS_CONFIG = BASE / "data" / "projects.json"
DATA_DIR = BASE / "data"


def load_projects() -> Dict[str, dict]:
    """Load projects configuration."""
    if not PROJECTS_CONFIG.exists():
        return {}
    try:
        with open(PROJECTS_CONFIG, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_projects(projects: Dict[str, dict]):
    """Save projects configuration."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROJECTS_CONFIG, "w", encoding="utf-8") as f:
        json.dump(projects, indent=2, ensure_ascii=False, fp=f)


def generate_project_id(name: str, root: str) -> str:
    """Generate a unique project ID based on name and root path."""
    # Use first 8 characters of hash for short ID
    content = f"{name}:{root}"
    return hashlib.sha256(content.encode()).hexdigest()[:8]


def find_project_by_id_or_name(identifier: str) -> Optional[tuple]:
    """Find project by ID or name. Returns (name, config) or None."""
    projects = load_projects()

    # Try exact name match first
    if identifier in projects:
        return (identifier, projects[identifier])

    # Try ID match
    for name, config in projects.items():
        if config.get("id") == identifier:
            return (name, config)

    return None


def resolve_project_name(name_or_id_or_auto: str) -> Optional[str]:
    """Resolve project name from name, ID, or 'auto' (current directory)."""
    if name_or_id_or_auto == "auto":
        # Detect from current working directory
        cwd = Path(os.getcwd()).resolve()
        detected_name = cwd.name

        # Check if this project is registered
        result = find_project_by_id_or_name(detected_name)
        if result:
            return result[0]

        # Not registered, return detected name for potential registration
        return detected_name

    # Try to find by ID or name
    result = find_project_by_id_or_name(name_or_id_or_auto)
    if result:
        return result[0]

    # If not found, return as-is (might be a new project name)
    return name_or_id_or_auto


def add_project(name_or_auto: str, root_path: str):
    """Add or update a project. Use 'auto' for name to detect from current directory."""
    root = Path(root_path).resolve()
    if not root.exists():
        print(f"❌ Error: Path does not exist: {root}")
        sys.exit(1)

    if not root.is_dir():
        print(f"❌ Error: Path is not a directory: {root}")
        sys.exit(1)

    # Resolve 'auto' to actual project name
    if name_or_auto == "auto":
        # Use current directory name or the root_path directory name
        if root_path == ".":
            name = Path(os.getcwd()).name
        else:
            name = root.name
        print(f"🔍 Auto-detected project name: {name}")
    else:
        name = name_or_auto

    projects = load_projects()

    # Check if project already exists
    is_update = name in projects
    if is_update:
        print(f"⚠️  Project '{name}' already exists. Updating...")
        # Preserve existing ID if updating
        project_id = projects[name].get("id", generate_project_id(name, str(root)))
    else:
        # Generate new ID for new project
        project_id = generate_project_id(name, str(root))

    projects[name] = {
        "id": project_id,
        "root": str(root),
        "db": f"data/corpus_{name}.duckdb",
        "chunks": f"data/chunks_{name}.jsonl",
        "active": len(projects) == 0,  # First project is active by default
    }
    
    save_projects(projects)
    action = "Updated" if is_update else "Added"
    print(f"✅ {action} project: {name}")
    print(f"   ID: {project_id}")
    print(f"   Root: {root}")
    print(f"   DB: {projects[name]['db']}")
    print(f"   Chunks: {projects[name]['chunks']}")
    
    # Build index for this project
    print(f"\n🔨 Building index for '{name}'...")
    build_project_index(name, projects[name])


def build_project_index(name: str, config: dict):
    """Build index for a specific project."""
    import sys
    import subprocess

    # Use subprocess to call build_index.py directly
    build_script = BASE / "retrieval" / "build_index.py"

    cmd = [
        sys.executable,
        str(build_script),
        "--root", config["root"],
        "--db", config["db"],
        "--chunks", config["chunks"],
    ]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        print(f"✅ Index built for '{name}'")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error building index: {e}")
        if e.stderr:
            print(e.stderr)


def list_projects():
    """List all projects."""
    import datetime

    projects = load_projects()

    if not projects:
        print("📭 No projects configured.")
        print("\nAdd a project with:")
        print("  python retrieval/multi_project.py add <name> <path>")
        print("  # or use 'auto' to detect from current directory:")
        print("  cd /path/to/project && python retrieval/multi_project.py add auto .")
        return

    # Detect current directory project
    cwd = Path(os.getcwd()).resolve()
    current_project = cwd.name

    print("📚 Configured Projects:\n")
    for idx, (name, config) in enumerate(projects.items(), 1):
        active = "🟢 ACTIVE" if config.get("active", False) else "⚪"
        current = "📍 CURRENT" if name == current_project else ""
        project_id = config.get("id", "N/A")

        status_line = f"{active} [{idx}] {name} {current}"
        print(status_line)
        print(f"   ID: {project_id}")
        print(f"   Root: {config['root']}")
        print(f"   DB: {config['db']}")
        print(f"   Chunks: {config['chunks']}")

        # Check if files exist and get last modified time
        db_path = BASE / config['db']
        chunks_path = BASE / config['chunks']
        db_status = "✅" if db_path.exists() else "❌"
        chunks_status = "✅" if chunks_path.exists() else "❌"

        # Get last modified time
        last_modified = "N/A"
        if db_path.exists():
            mtime = db_path.stat().st_mtime
            last_modified = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")

        print(f"   Status: DB {db_status} | Chunks {chunks_status}")
        print(f"   Last Modified: {last_modified}")
        print()


def remove_project(name_or_id: str):
    """Remove a project by name or ID."""
    # Resolve name from ID or 'auto'
    name = resolve_project_name(name_or_id)

    projects = load_projects()

    if name not in projects:
        print(f"❌ Error: Project '{name_or_id}' not found.")
        list_projects()
        sys.exit(1)
    
    config = projects[name]
    
    # Ask for confirmation
    print(f"⚠️  About to remove project: {name}")
    print(f"   Root: {config['root']}")
    print(f"   DB: {config['db']}")
    print(f"   Chunks: {config['chunks']}")
    
    response = input("\nDelete index files? (y/N): ").strip().lower()
    
    if response == 'y':
        # Delete files
        db_path = BASE / config['db']
        chunks_path = BASE / config['chunks']
        
        if db_path.exists():
            db_path.unlink()
            print(f"🗑️  Deleted: {config['db']}")
        
        if chunks_path.exists():
            chunks_path.unlink()
            print(f"🗑️  Deleted: {config['chunks']}")
    
    # Remove from config
    del projects[name]
    
    # If this was the active project, activate another one
    if config.get("active", False) and projects:
        first_project = next(iter(projects.keys()))
        projects[first_project]["active"] = True
        print(f"🔄 Activated project: {first_project}")
    
    save_projects(projects)
    print(f"✅ Removed project: {name}")


def activate_project(name_or_id: str):
    """Set a project as active by name or ID."""
    # Resolve name from ID or 'auto'
    name = resolve_project_name(name_or_id)

    projects = load_projects()

    if name not in projects:
        print(f"❌ Error: Project '{name_or_id}' not found.")
        list_projects()
        sys.exit(1)
    
    # Deactivate all projects
    for proj_name in projects:
        projects[proj_name]["active"] = False
    
    # Activate the specified project
    projects[name]["active"] = True
    
    save_projects(projects)
    print(f"✅ Activated project: {name}")
    
    # Create symlinks for backward compatibility
    create_symlinks(name, projects[name])


def create_symlinks(name: str, config: dict):
    """Create symlinks to active project's files."""
    db_link = DATA_DIR / "corpus.duckdb"
    chunks_link = DATA_DIR / "chunks.jsonl"
    
    db_target = BASE / config['db']
    chunks_target = BASE / config['chunks']
    
    # Remove old symlinks if they exist
    if db_link.exists() or db_link.is_symlink():
        db_link.unlink()
    if chunks_link.exists() or chunks_link.is_symlink():
        chunks_link.unlink()
    
    # Create new symlinks
    if db_target.exists():
        db_link.symlink_to(db_target.name)
        print(f"🔗 Linked: corpus.duckdb → {config['db']}")
    
    if chunks_target.exists():
        chunks_link.symlink_to(chunks_target.name)
        print(f"🔗 Linked: chunks.jsonl → {config['chunks']}")


def rebuild_single_project(name_or_id: str):
    """Rebuild index for a single project by name or ID."""
    # Resolve name from ID or 'auto'
    name = resolve_project_name(name_or_id)

    projects = load_projects()

    if name not in projects:
        print(f"❌ Project '{name_or_id}' not found.")
        print("\n📋 Available projects:")
        list_projects()
        sys.exit(1)

    config = projects[name]
    print(f"🔨 Rebuilding index for '{name}'...")
    build_project_index(name, config)
    print(f"✅ Index rebuilt for '{name}'")


def rebuild_all():
    """Rebuild indexes for all projects."""
    projects = load_projects()

    if not projects:
        print("📭 No projects configured.")
        return

    print(f"🔨 Rebuilding {len(projects)} project(s)...\n")

    for name, config in projects.items():
        print(f"Building: {name}")
        build_project_index(name, config)
        print()

    print("✅ All projects rebuilt!")


def main():
    parser = argparse.ArgumentParser(description="Multi-project index management")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Add command
    add_parser = subparsers.add_parser("add", help="Add or update a project")
    add_parser.add_argument("name", help="Project name")
    add_parser.add_argument("root", help="Project root directory")
    
    # List command
    subparsers.add_parser("list", help="List all projects")
    
    # Remove command
    remove_parser = subparsers.add_parser("remove", help="Remove a project")
    remove_parser.add_argument("name", help="Project name")
    
    # Activate command
    activate_parser = subparsers.add_parser("activate", help="Set active project")
    activate_parser.add_argument("name", help="Project name")
    
    # Rebuild command
    rebuild_parser = subparsers.add_parser("rebuild", help="Rebuild project index(es)")
    rebuild_parser.add_argument("name", nargs="?", help="Project name (optional, rebuilds all if not specified)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "add":
        add_project(args.name, args.root)
    elif args.command == "list":
        list_projects()
    elif args.command == "remove":
        remove_project(args.name)
    elif args.command == "activate":
        activate_project(args.name)
    elif args.command == "rebuild":
        if args.name:
            rebuild_single_project(args.name)
        else:
            rebuild_all()


if __name__ == "__main__":
    main()

