import os, argparse, duckdb, pathlib, re, json
from pathlib import Path

TEXT_EXTS = {".md",".txt",".rst",".py",".go",".js",".ts",".tsx",".java",".kt",".c",".cpp",".h",".hpp",".cs",".rb",".php",".sh",".yaml",".yml",".toml",".ini",".json"}

# Common directories to ignore (similar to .gitignore)
IGNORE_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", ".nuxt", "coverage",
    ".pytest_cache", ".mypy_cache", ".tox", ".eggs",
    "*.egg-info", ".cache", ".sass-cache", "bower_components"
}

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