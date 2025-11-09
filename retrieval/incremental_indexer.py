#!/usr/bin/env python3
"""
Incremental Indexer - Automatic file change detection and incremental indexing.
Inspired by acemcp's zero-maintenance approach.

Features:
- Automatic file change detection (added/modified/deleted)
- Only indexes changed files (much faster than rebuild)
- Maintains index state in JSON
- Integrates seamlessly with existing hybrid_search
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
import hashlib
import time

# Import existing indexing functions
from retrieval.build_index import (
    parse_file_with_tree_sitter,
    load_gitignore,
    should_skip_file,
)


class IncrementalIndexer:
    """
    Manages incremental indexing for a project.

    Tracks file state (mtime, size, hash) and only re-indexes changed files.
    """

    def __init__(self, project_name: str, project_root: str):
        self.project_name = project_name
        self.project_root = Path(project_root).resolve()

        # State file stores metadata about indexed files
        base_dir = Path(__file__).resolve().parents[1]
        self.data_dir = base_dir / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.state_file = self.data_dir / f"index_state_{project_name}.json"
        self.chunks_file = self.data_dir / f"chunks_{project_name}.jsonl"
        self.db_file = self.data_dir / f"corpus_{project_name}.duckdb"

        # Load previous state
        self.previous_state = self._load_state()

        # Gitignore
        self.gitignore = load_gitignore(self.project_root)

    def _load_state(self) -> Dict[str, dict]:
        """Load previous index state from JSON."""
        if not self.state_file.exists():
            return {}

        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Failed to load index state: {e}", file=sys.stderr)
            return {}

    def _save_state(self, state: Dict[str, dict]):
        """Save current index state to JSON."""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, indent=2, ensure_ascii=False, fp=f)
        except Exception as e:
            print(f"[ERROR] Failed to save index state: {e}", file=sys.stderr)

    def _get_file_metadata(self, file_path: Path) -> dict:
        """Get file metadata for change detection."""
        try:
            stat = file_path.stat()

            # Quick check: mtime + size
            metadata = {
                "mtime": stat.st_mtime,
                "size": stat.st_size,
            }

            # Optional: content hash for more accuracy (slower)
            # Only compute hash for small files to avoid performance hit
            if stat.st_size < 1024 * 1024:  # < 1MB
                try:
                    with open(file_path, 'rb') as f:
                        content = f.read()
                        metadata["hash"] = hashlib.md5(content).hexdigest()
                except Exception:
                    pass  # Hash optional

            return metadata
        except Exception as e:
            print(f"[WARN] Failed to get metadata for {file_path}: {e}", file=sys.stderr)
            return {}

    def _has_changed(self, file_path: str, metadata: dict) -> bool:
        """Check if file has changed since last index."""
        if file_path not in self.previous_state:
            return True  # New file

        prev = self.previous_state[file_path]

        # Check mtime and size first (fast)
        if prev.get("mtime") != metadata.get("mtime"):
            return True
        if prev.get("size") != metadata.get("size"):
            return True

        # If hash available, check it (more accurate)
        if "hash" in metadata and "hash" in prev:
            return prev["hash"] != metadata["hash"]

        return False

    def detect_changes(self) -> Dict[str, List[str]]:
        """
        Detect file changes since last index.

        Returns:
            {
                "added": [...],      # New files
                "modified": [...],   # Changed files
                "deleted": [...],    # Removed files
            }
        """
        print(f"[INCREMENTAL] Detecting changes in {self.project_root}...", file=sys.stderr)
        start_time = time.time()

        changes = {
            "added": [],
            "modified": [],
            "deleted": [],
        }

        current_files = {}

        # Scan current files
        extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".cpp", ".c", ".h"}

        for ext in extensions:
            for file_path in self.project_root.rglob(f"*{ext}"):
                # Skip if gitignore or should skip
                if self.gitignore and self.gitignore(file_path):
                    continue
                if should_skip_file(file_path):
                    continue

                rel_path = str(file_path.relative_to(self.project_root))
                metadata = self._get_file_metadata(file_path)

                if metadata:
                    current_files[rel_path] = metadata

                    # Check if changed
                    if self._has_changed(rel_path, metadata):
                        if rel_path in self.previous_state:
                            changes["modified"].append(rel_path)
                        else:
                            changes["added"].append(rel_path)

        # Detect deleted files
        for rel_path in self.previous_state:
            if rel_path not in current_files:
                changes["deleted"].append(rel_path)

        elapsed = time.time() - start_time
        total_changes = len(changes["added"]) + len(changes["modified"]) + len(changes["deleted"])

        print(f"[INCREMENTAL] Detected {total_changes} changes in {elapsed:.2f}s:", file=sys.stderr)
        print(f"  - Added: {len(changes['added'])}", file=sys.stderr)
        print(f"  - Modified: {len(changes['modified'])}", file=sys.stderr)
        print(f"  - Deleted: {len(changes['deleted'])}", file=sys.stderr)

        # Update state
        self.current_files = current_files

        return changes

    def incremental_update(self, changes: Dict[str, List[str]]) -> Dict[str, int]:
        """
        Perform incremental index update.

        Only re-indexes changed files, keeping unchanged files as-is.

        Returns:
            Statistics: {"chunks_added": N, "chunks_removed": M, "chunks_total": T}
        """
        print(f"[INCREMENTAL] Starting incremental update...", file=sys.stderr)
        start_time = time.time()

        stats = {
            "chunks_added": 0,
            "chunks_removed": 0,
            "chunks_total": 0,
        }

        # Load existing chunks
        existing_chunks = []
        if self.chunks_file.exists():
            try:
                with open(self.chunks_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            existing_chunks.append(json.loads(line))
            except Exception as e:
                print(f"[ERROR] Failed to load existing chunks: {e}", file=sys.stderr)
                return stats

        # Remove deleted and modified files' chunks
        files_to_remove = set(changes["deleted"] + changes["modified"])
        filtered_chunks = []

        for chunk in existing_chunks:
            source = chunk.get("source", "")
            # Extract filename from source (format: "file:line")
            if ":" in source:
                filename = source.split(":")[0]
                if filename not in files_to_remove:
                    filtered_chunks.append(chunk)
                else:
                    stats["chunks_removed"] += 1

        print(f"[INCREMENTAL] Removed {stats['chunks_removed']} chunks from {len(files_to_remove)} files", file=sys.stderr)

        # Add chunks from added and modified files
        new_chunks = []
        files_to_add = changes["added"] + changes["modified"]

        for rel_path in files_to_add:
            file_path = self.project_root / rel_path

            try:
                # Parse file and extract chunks
                chunks = parse_file_with_tree_sitter(file_path, self.project_root)

                if chunks:
                    new_chunks.extend(chunks)
                    print(f"[INCREMENTAL]   Indexed {rel_path}: {len(chunks)} chunks", file=sys.stderr)

            except Exception as e:
                print(f"[WARN] Failed to parse {rel_path}: {e}", file=sys.stderr)
                continue

        stats["chunks_added"] = len(new_chunks)

        # Combine: filtered old + new
        all_chunks = filtered_chunks + new_chunks
        stats["chunks_total"] = len(all_chunks)

        # Write updated chunks
        try:
            with open(self.chunks_file, 'w', encoding='utf-8') as f:
                for chunk in all_chunks:
                    f.write(json.dumps(chunk, ensure_ascii=False) + '\n')

            print(f"[INCREMENTAL] Wrote {stats['chunks_total']} chunks to {self.chunks_file.name}", file=sys.stderr)

        except Exception as e:
            print(f"[ERROR] Failed to write chunks: {e}", file=sys.stderr)
            return stats

        # Update BM25 index (DuckDB)
        try:
            self._update_bm25_index(all_chunks)
        except Exception as e:
            print(f"[ERROR] Failed to update BM25 index: {e}", file=sys.stderr)

        # Save new state
        self._save_state(self.current_files)

        elapsed = time.time() - start_time
        print(f"[INCREMENTAL] Update complete in {elapsed:.2f}s", file=sys.stderr)

        return stats

    def _update_bm25_index(self, chunks: List[dict]):
        """Update DuckDB BM25 index with new chunks."""
        import duckdb

        # Remove old database and create fresh
        # (DuckDB BM25 extension doesn't support incremental updates easily)
        if self.db_file.exists():
            self.db_file.unlink()

        conn = duckdb.connect(str(self.db_file))

        try:
            # Install FTS extension
            conn.execute("INSTALL fts")
            conn.execute("LOAD fts")

            # Create table
            conn.execute("""
                CREATE TABLE corpus (
                    id INTEGER PRIMARY KEY,
                    text TEXT,
                    source TEXT
                )
            """)

            # Insert chunks
            for i, chunk in enumerate(chunks):
                conn.execute(
                    "INSERT INTO corpus (id, text, source) VALUES (?, ?, ?)",
                    (i, chunk["text"], chunk["source"])
                )

            # Create FTS index
            conn.execute("""
                PRAGMA create_fts_index(
                    'corpus', 'id', 'text',
                    stemmer='porter',
                    stopwords='english',
                    ignore='(\\.|[^a-z])+',
                    strip_accents=1,
                    lower=1,
                    overwrite=1
                )
            """)

            print(f"[INCREMENTAL] Updated BM25 index with {len(chunks)} chunks", file=sys.stderr)

        finally:
            conn.close()

    def needs_update(self) -> bool:
        """Quick check if any files have changed."""
        changes = self.detect_changes()
        total = len(changes["added"]) + len(changes["modified"]) + len(changes["deleted"])
        return total > 0


def auto_index_if_needed(project_name: str, project_root: str) -> Optional[Dict[str, int]]:
    """
    Automatically detect and index changes if needed.

    This is the main entry point for auto-incremental indexing.
    Call this before every search to ensure index is up-to-date.

    Returns:
        Statistics if update was performed, None if no update needed.
    """
    indexer = IncrementalIndexer(project_name, project_root)

    # Detect changes
    changes = indexer.detect_changes()
    total_changes = len(changes["added"]) + len(changes["modified"]) + len(changes["deleted"])

    if total_changes == 0:
        print(f"[INCREMENTAL] No changes detected, index is up-to-date", file=sys.stderr)
        return None

    # Perform incremental update
    stats = indexer.incremental_update(changes)
    return stats


# CLI for testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Incremental indexer for code repositories")
    parser.add_argument("--project", required=True, help="Project name")
    parser.add_argument("--root", required=True, help="Project root directory")
    parser.add_argument("--force", action="store_true", help="Force full re-index")

    args = parser.parse_args()

    if args.force:
        print("[INCREMENTAL] Force re-index requested, removing old state...", file=sys.stderr)
        indexer = IncrementalIndexer(args.project, args.root)
        if indexer.state_file.exists():
            indexer.state_file.unlink()
        indexer.previous_state = {}

    stats = auto_index_if_needed(args.project, args.root)

    if stats:
        print(f"\n[INCREMENTAL] Statistics:")
        print(f"  Chunks added: {stats['chunks_added']}")
        print(f"  Chunks removed: {stats['chunks_removed']}")
        print(f"  Total chunks: {stats['chunks_total']}")
    else:
        print("\n[INCREMENTAL] Index already up-to-date")
