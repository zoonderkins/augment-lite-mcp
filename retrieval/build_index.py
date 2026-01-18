import os, argparse, duckdb, pathlib, re, json
from pathlib import Path
from typing import List, Dict, Optional, Callable

# Code file extensions (use line-based chunking)
# Source: https://github.com/bigcode-project/bigcode-dataset
CODE_EXTS = {
    # Python
    ".py", ".pyw", ".pyi", ".pyx",
    # JavaScript/TypeScript
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
    # Go
    ".go",
    # Rust
    ".rs",
    # Java/Kotlin/Scala
    ".java", ".kt", ".kts", ".scala", ".sbt",
    # C/C++
    ".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".hxx", ".hh",
    # C#
    ".cs", ".csx",
    # Ruby
    ".rb", ".rake", ".gemspec",
    # PHP
    ".php",
    # Shell/Bash
    ".sh", ".bash", ".zsh", ".fish",
    # Swift/Objective-C
    ".swift", ".m", ".mm",
    # Lua
    ".lua",
    # Perl
    ".pl", ".pm",
    # R
    ".r", ".R",
    # Julia
    ".jl",
    # Elixir/Erlang
    ".ex", ".exs", ".erl",
    # Haskell
    ".hs",
    # Clojure
    ".clj", ".cljs", ".cljc",
    # SQL
    ".sql",
    # Config files
    ".yaml", ".yml", ".toml", ".ini", ".json", ".jsonc",
    # Web
    ".css", ".scss", ".sass", ".less",
    # Other
    ".vue", ".svelte", ".astro",
    ".graphql", ".gql",
    ".proto",
    ".tf", ".hcl",  # Terraform/HCL
    ".dockerfile", ".containerfile",
}

# Documentation file extensions (use token-based chunking)
DOC_EXTS = {
    ".md", ".markdown", ".mkd",
    ".txt",
    ".rst", ".rest",
    ".html", ".htm",
    ".adoc", ".asciidoc",
    ".org",
    ".tex",
}

# All supported text extensions
TEXT_EXTS = CODE_EXTS | DOC_EXTS

# Common directories to ignore (similar to .gitignore)
IGNORE_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", ".nuxt", "coverage",
    ".pytest_cache", ".mypy_cache", ".tox", ".eggs",
    "*.egg-info", ".cache", ".sass-cache", "bower_components"
}

# ============================================================
# Functions for incremental_indexer.py
# ============================================================

def load_gitignore(project_root: Path) -> Optional[Callable[[Path], bool]]:
    """
    Load .gitignore patterns from project root.
    Returns a callable that checks if a path should be ignored.
    """
    gitignore_path = project_root / ".gitignore"
    if not gitignore_path.exists():
        return None

    try:
        import pathspec
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            patterns = f.read().splitlines()
        spec = pathspec.PathSpec.from_lines('gitwildmatch', patterns)

        def matcher(path: Path) -> bool:
            try:
                rel_path = path.relative_to(project_root)
                return spec.match_file(str(rel_path))
            except ValueError:
                return False

        return matcher
    except ImportError:
        # pathspec not installed, return simple matcher
        patterns = []
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    patterns.append(line)

        def simple_matcher(path: Path) -> bool:
            try:
                rel_path = str(path.relative_to(project_root))
                for pattern in patterns:
                    if pattern in rel_path:
                        return True
                return False
            except ValueError:
                return False

        return simple_matcher
    except Exception:
        return None


def should_skip_file(file_path: Path) -> bool:
    """
    Check if a file should be skipped during indexing.
    Combines extension check and directory ignore patterns.
    """
    # Check extension
    if file_path.suffix.lower() not in TEXT_EXTS:
        return True

    # Check ignored directories
    if should_ignore_path(file_path):
        return True

    # Skip hidden files
    if file_path.name.startswith('.'):
        return True

    # Skip very large files (>1MB)
    try:
        if file_path.stat().st_size > 1024 * 1024:
            return True
    except Exception:
        return True

    return False


def parse_file_with_tree_sitter(file_path: Path, project_root: Path) -> List[Dict]:
    """
    Parse a file and return chunks with metadata.

    Uses different chunking strategies based on file type:
    - Code files: line-based chunking (50 lines, 10 overlap)
    - Doc files: token-based chunking (256 tokens, 32 overlap)

    Returns:
        List of chunks with metadata:
        [{"text": "...", "source": "file:line", "chunking_method": "lines|tokens", "filetype": "py|md|..."}, ...]
    """
    content = read_text(file_path)
    if not content:
        return []

    chunks = []
    try:
        rel_path = str(file_path.relative_to(project_root))
    except ValueError:
        rel_path = str(file_path)

    ext = file_path.suffix.lower()
    filetype = ext.lstrip(".")

    # Choose chunking method based on file type
    if ext in DOC_EXTS:
        # Token-based chunking for documentation
        chunking_method = "tokens"
        for i, chunk_text in enumerate(chunk_text_by_tokens(content, size=256, overlap=32)):
            if chunk_text.strip():
                chunks.append({
                    "text": chunk_text,
                    "source": f"{rel_path}:chunk{i + 1}",
                    "chunking_method": chunking_method,
                    "filetype": filetype
                })
    else:
        # Line-based chunking for code files
        chunking_method = "lines"
        lines = content.split('\n')
        chunk_size = 50  # lines per chunk
        overlap = 10     # overlap lines

        i = 0
        chunk_idx = 0
        while i < len(lines):
            chunk_lines = lines[i:i + chunk_size]
            chunk_text = '\n'.join(chunk_lines)

            if chunk_text.strip():
                chunks.append({
                    "text": chunk_text,
                    "source": f"{rel_path}:{i + 1}",
                    "chunking_method": chunking_method,
                    "filetype": filetype
                })
                chunk_idx += 1

            i += max(1, chunk_size - overlap)

    return chunks


def _simple_tokenize(text: str) -> List[str]:
    """
    Simple tokenizer that handles CJK characters, English words, and symbols.

    - CJK characters (Chinese, Japanese, Korean) are treated as individual tokens
    - English words and numbers are kept as single tokens
    - Symbols are individual tokens

    This avoids the problem where text.split() treats entire Chinese paragraphs as one token.
    """
    # Match: CJK chars | Japanese Hiragana/Katakana | Korean | Words/Numbers | Other non-whitespace
    pattern = r"[\u4e00-\u9fff]|[\u3040-\u30ff]|[\uac00-\ud7af]|[A-Za-z0-9_]+|[^\s\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]"
    return re.findall(pattern, text)


def chunk_text_by_tokens(text: str, size: int = 256, overlap: int = 32):
    """
    Chunk text by tokens with CJK support.

    Args:
        text: Input text
        size: Tokens per chunk
        overlap: Overlap tokens

    Yields:
        Chunk strings
    """
    tokens = _simple_tokenize(text)
    step = max(1, size - overlap)
    for i in range(0, len(tokens), step):
        chunk = tokens[i:i + size]
        if chunk:
            # Join with space, but CJK chars don't need space between them
            # Simple approach: join all with space (acceptable for embedding)
            yield " ".join(chunk)


def should_ignore_path(p: Path) -> bool:
    """Check if path should be ignored based on common patterns."""
    parts = p.parts
    for part in parts:
        if part in IGNORE_DIRS:
            return True
        # Also check for patterns like .egg-info
        if part.endswith('.egg-info'):
            return True
    return False

def read_text(p: Path):
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        try:
            return p.read_text(encoding="latin-1", errors="ignore")
        except Exception:
            return ""

def chunk_text(text, size=256, overlap=32):
    tokens = re.findall(r"\S+|\n", text)
    i = 0
    while i < len(tokens):
        chunk = tokens[i:i+size]
        yield " ".join(chunk)
        i += max(1, size - overlap)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="Directory to index")
    ap.add_argument("--db", default="data/corpus.duckdb", help="DuckDB database path")
    ap.add_argument("--chunks", default="data/chunks.jsonl", help="Output chunks JSONL path")
    args = ap.parse_args()

    root = Path(args.root)
    dbpath = Path(args.db)
    dbpath.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(dbpath))
    con.execute("CREATE TABLE IF NOT EXISTS corpus(path TEXT PRIMARY KEY, mtime DOUBLE, size BIGINT, content TEXT)")

    to_upsert = []
    for p in root.rglob("*"):
        if not p.is_file(): continue
        if should_ignore_path(p): continue  # Skip ignored directories
        if p.suffix.lower() not in TEXT_EXTS: continue
        st = p.stat()
        content = read_text(p)
        to_upsert.append((str(p), st.st_mtime, st.st_size, content))

    if to_upsert:
        con.execute("BEGIN")
        con.execute("DELETE FROM corpus WHERE path LIKE ?", (str(root) + "%",))
        con.executemany("INSERT OR REPLACE INTO corpus VALUES (?, ?, ?, ?)", to_upsert)
        con.execute("COMMIT")

    print(f"Indexed {len(to_upsert)} files under {root}")
    chunks_path = Path(args.chunks)
    chunks_path.parent.mkdir(parents=True, exist_ok=True)
    with open(chunks_path, "w", encoding="utf-8") as w:
        for path, content in con.execute("SELECT path, content FROM corpus").fetchall():
            for part in chunk_text(content, size=256, overlap=32):
                w.write(json.dumps({"path": path, "text": part}, ensure_ascii=False) + "\n")
    print(f"Wrote chunks to {chunks_path}")

if __name__ == "__main__":
    main()