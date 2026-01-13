#!/usr/bin/env python3
"""
Build vector index from existing chunks.

Usage:
    python retrieval/build_vector_index.py [project_name]
    
Examples:
    # Build for active project
    python retrieval/build_vector_index.py
    
    # Build for specific project
    python retrieval/build_vector_index.py myproject
    
    # Build for global (no project)
    python retrieval/build_vector_index.py --global
"""

import sys
import json
import logging
from pathlib import Path

# Add parent directory to path
BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from retrieval.vector_search import VectorSearchEngine
from utils.project_utils import resolve_auto_project

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

DATA_DIR = BASE / "data"

def load_chunks(project: str = None) -> list:
    """
    Load chunks from chunks.jsonl or chunks_{project}.jsonl.
    
    Args:
        project: Project name (None for global)
    
    Returns:
        List of chunk dicts
    """
    if project:
        chunks_file = DATA_DIR / f"chunks_{project}.jsonl"
    else:
        chunks_file = DATA_DIR / "chunks.jsonl"
    
    if not chunks_file.exists():
        logger.error(f"Chunks file not found: {chunks_file}")
        return []
    
    chunks = []
    with open(chunks_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    
    logger.info(f"Loaded {len(chunks)} chunks from {chunks_file}")
    return chunks

def build_vector_index(project: str = None):
    """
    Build vector index for a project.
    
    Args:
        project: Project name (None for global)
    """
    logger.info(f"Building vector index for project: {project or 'global'}")
    
    # Load chunks
    chunks = load_chunks(project)
    if not chunks:
        logger.error("No chunks to index")
        return
    
    # Create vector search engine
    engine = VectorSearchEngine(project=project)
    
    # Build index
    engine.build_index(chunks)
    
    logger.info("✅ Vector index built successfully!")

def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Build vector index from existing chunks")
    parser.add_argument("--project", type=str, default=None, help="Project name (default: auto-detect active project)")
    parser.add_argument("--global", dest="use_global", action="store_true", help="Build global index (no project)")
    # Also support positional argument for backward compatibility
    parser.add_argument("project_name", nargs="?", type=str, help="Project name (positional argument)")

    args = parser.parse_args()

    # Determine project from arguments
    if args.use_global:
        project = None
    elif args.project:
        project = args.project
    elif args.project_name:
        project = args.project_name
    else:
        # Use active project
        project = resolve_auto_project()
        if project is None:
            logger.warning("No active project found. Building global index.")

    build_vector_index(project)

if __name__ == "__main__":
    main()

