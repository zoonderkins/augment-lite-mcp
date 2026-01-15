# mcp_bridge_lazy.py — ultra-fast startup MCP stdio server (lazy imports)
# uv pip install "mcp>=1.1,<2"

import asyncio
import json
import os
import traceback
from typing import Any
from pathlib import Path

# Debug mode - set AUGMENT_DEBUG=true to expose stack traces
DEBUG = os.getenv("AUGMENT_DEBUG", "false").lower() == "true"

# Load environment variables from .env file (if exists)
# This allows using .env for development while still supporting
# environment variable overrides (e.g., from Claude MCP config)
try:
    from dotenv import load_dotenv
    load_dotenv(override=False)  # Don't override existing env vars
except ImportError:
    pass  # python-dotenv not installed, skip

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
from mcp.server.lowlevel import NotificationOptions
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

BASE = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("AUGMENT_DB_DIR", BASE / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# DO NOT change working directory - respect caller's CWD
# os.chdir(BASE)  # Removed: This breaks Claude Code's working directory context

# Server instructions - guide AI on when and how to use this MCP server
SERVER_INSTRUCTIONS = """
🔍 augment-lite: Zero-Maintenance AI Code Assistant

CORE CAPABILITIES:
1. Semantic code search (hybrid BM25 + vector embeddings)
2. Question answering with source citations
3. Multi-project support with AUTO-INIT & AUTO-INDEX
4. Long-term memory for architectural decisions (Serena-style)
5. Task management across sessions

═══════════════════════════════════════════════════════════════
ZERO-CONFIGURATION WORKFLOW (v1.2.0+)
═══════════════════════════════════════════════════════════════

rag.search will automatically:
1. AUTO-INIT: Register project if not exists
2. AUTO-INDEX: Build index if not exists, or incremental update
3. Execute search

NO MANUAL project.init NEEDED for basic usage!

═══════════════════════════════════════════════════════════════
UNIFIED SEARCH (auggie + augment-lite orchestration)
═══════════════════════════════════════════════════════════════

answer.unified returns execution plan for multi-MCP search:

Usage:
  answer.unified query="Analyze architecture, DB, metrics..."

Returns execution plan:
  Step 1: auggie-mcp semantic search
  Step 2: augment-lite RAG search
  Step 3-N: Sub-query searches
  Step N+1: Synthesize with route model (GLM-4.7/MiniMax)

Claude executes steps and merges results automatically.

Models used:
  • minimax-m2.1: Query decomposition + RAG re-ranking
  • route param: Final answer (default: reason-large = GLM-4.7)

═══════════════════════════════════════════════════════════════
ANSWER TOOL SELECTION GUIDE
═══════════════════════════════════════════════════════════════

| Scenario | Tool | Why |
|----------|------|-----|
| Simple question | answer.generate | Single search, fast |
| Complex multi-aspect | answer.accumulated | Multi-round evidence accumulation |
| Previous "不知道" | answer.accumulated | Re-search with sub-queries |
| Need auggie + local | answer.unified | Returns plan for dual-MCP |
| Search only (no answer) | dual.search | Returns hits + auggie hint |

TRIGGER KEYWORDS:
• "analyze architecture, database, metrics..." → answer.accumulated
• "comprehensive analysis" → answer.accumulated
• "search both auggie and local" → answer.unified
• "返回不知道/incomplete" → retry with answer.accumulated

═══════════════════════════════════════════════════════════════
PROACTIVE MEMORY PATTERNS (Serena-style)
═══════════════════════════════════════════════════════════════

When starting work on a project, auto-create these memories:

📋 project_overview (REQUIRED on first interaction):
   → memory.set key="project_overview" value="..."
   → Content: project name, version, purpose, core modules, tech stack

📝 code_style (detect from codebase or user input):
   → memory.set key="code_style" value="..."
   → Content: line length, formatter, naming conventions, import style

🔧 suggested_commands (from README/docs or discovery):
   → memory.set key="suggested_commands" value="..."
   → Content: setup, build, test, lint commands

🏗️ architecture_decisions (when user explains design):
   → memory.set key="architecture_decisions" value="..."
   → Content: patterns, frameworks, API conventions

═══════════════════════════════════════════════════════════════
MEMORY STORAGE TRIGGERS (auto-detect & store)
═══════════════════════════════════════════════════════════════

ALWAYS store when user mentions:
- Architecture: "The system uses..." → architecture_decisions
- Conventions: "All endpoints should..." → api_conventions
- Code style: "We use ruff..." → code_style
- Deployment: "To deploy, run..." → deployment_notes
- Bug patterns: "This error happens when..." → known_issues
- Design decisions: "We chose X over Y because..." → architecture_decisions

═══════════════════════════════════════════════════════════════
TASK MANAGEMENT (auto-track progress)
═══════════════════════════════════════════════════════════════

✅ Auto-create tasks when:
- User lists steps: "First..., then..., finally..."
- User says "TODO" or "need to"
- User outlines plan: "1. Do X, 2. Do Y, 3. Do Z"

✅ Auto-update tasks:
- Mark in_progress when starting work
- Mark completed when done
- Add blockers as new tasks

═══════════════════════════════════════════════════════════════
INTELLIGENT WORKFLOWS
═══════════════════════════════════════════════════════════════

1. First-Time Project Setup:
   rag.search (auto-init + auto-index) → detect code_style → memory.set

2. Code Exploration:
   rag.search → (if insufficient) → rag.search use_iterative=true

3. Question Answering:
   rag.search → answer.generate (auto-cites sources)

4. Knowledge Persistence:
   Detect important info → memory.set (store automatically)

5. Task Tracking:
   Detect multi-step work → task.add → task.update → task.complete

═══════════════════════════════════════════════════════════════
AUGGIE MCP 協同模式 (如果已安裝 auggie-mcp)
═══════════════════════════════════════════════════════════════

當 Claude Code 同時有 augment-lite 和 auggie-mcp 兩個 MCP 服務器時：

模式 A: augment-lite 初篩 → auggie 精排
┌─────────────────────────────────────────────────────────────┐
│ 1. augment-lite rag.search k=20 use_subagent=false         │
│    → 返回 20 個候選 (BM25+Vector 本地處理)                  │
│                                                             │
│ 2. auggie-mcp codebase-retrieval                           │
│    → 用 Augment 語義引擎對候選排序                          │
│                                                             │
│ 3. 返回最終 Top-5 結果給用戶                                │
└─────────────────────────────────────────────────────────────┘

模式 B: auggie 語義搜索 → augment-lite 存儲
┌─────────────────────────────────────────────────────────────┐
│ 1. auggie-mcp codebase-retrieval query="..."               │
│    → Augment 語義搜索                                       │
│                                                             │
│ 2. 發現重要架構信息?                                        │
│    → augment-lite memory.set key="architecture_decisions"  │
│                                                             │
│ 3. 下次搜索時可以參考 memory                                │
└─────────────────────────────────────────────────────────────┘

模式 C: 純 augment-lite (無 auggie)
┌─────────────────────────────────────────────────────────────┐
│ augment-lite rag.search use_subagent=true                  │
│ → 內建 LLM 過濾 (GLM-4.7/MiniMax-M2.1)                     │
│ → 完全獨立運作，不依賴 auggie                               │
└─────────────────────────────────────────────────────────────┘

協同判斷規則:
- 檢測到 auggie-mcp 可用 → 優先使用模式 A (節省 token)
- auggie-mcp 不可用或失敗 → 自動 fallback 到模式 C
- 需要持久化信息 → 無論哪種模式都存入 augment-lite memory

═══════════════════════════════════════════════════════════════
STANDARD MEMORY KEYS (use these consistently)
═══════════════════════════════════════════════════════════════

| Key | Purpose |
|-----|---------|
| project_overview | Project summary, version, purpose |
| code_style | Formatting, linting, naming conventions |
| suggested_commands | Setup, build, test commands |
| architecture_decisions | Design patterns, framework choices |
| api_conventions | REST/GraphQL patterns, error formats |
| deployment_notes | Deploy steps, environment configs |
| known_issues | Common bugs, workarounds |
| task_completion_checklist | Release/feature checklists |
"""

server = Server("augment-lite", instructions=SERVER_INSTRUCTIONS)

TOOLS = [
    Tool(
        name="rag.search",
        description="""Search codebase using hybrid BM25 + vector embeddings.

WHEN TO USE:
• User asks "where is...", "how does...", "show me..."
• Need to find code examples, patterns, or implementations
• Exploring unfamiliar codebase or feature

AUTO-INCREMENTAL INDEX (NEW in v0.7.0):
• Automatically detects file changes before every search
• Only re-indexes modified/added/deleted files (fast!)
• Zero manual maintenance - just search and index stays current
• Disable with auto_index=false if needed

AUTO-RETRY: If results insufficient (LOW_QUALITY, NO_RESULTS), retry with use_iterative=true

RETURNS: {text, source, score} - source includes file:line for easy navigation""",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "k": {"type": "integer", "default": 8},
                "use_subagent": {"type": "boolean", "default": True, "description": "Use LLM to filter and re-rank results (ACE-like)"},
                "use_iterative": {"type": "boolean", "default": False, "description": "Enable multi-round retrieval with query expansion"},
                "auto_index": {"type": "boolean", "default": True, "description": "Auto-detect and index file changes before search (acemcp-style)"}
            },
            "required": ["query"],
        },
        # outputSchema omitted for token efficiency - Claude understands JSON responses naturally
    ),
    Tool(
        name="dual.search",
        description="""Combined search across augment-lite + auggie-mcp engines.

WHEN TO USE:
• Need comprehensive code search from multiple sources
• Want both local (BM25+vector) and semantic (auggie) results
• Following CLAUDE.md Phase 1 dual-MCP workflow

INTEGRATION:
• Always runs augment-lite locally
• Calls auggie-mcp HTTP if AUGGIE_API_URL is configured
• Returns auggie_hint if manual orchestration needed
• Auto-rebuilds stale index when auggie finds missing files (v1.3.2+)

RETURNS: {hits, sources, auggie_available, auggie_hint, index_rebuilt}""",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "k": {"type": "integer", "default": 8},
                "use_subagent": {"type": "boolean", "default": True},
                "use_iterative": {"type": "boolean", "default": False},
                "include_auggie": {"type": "boolean", "default": True, "description": "Try to include auggie results"},
                "auto_rebuild": {"type": "boolean", "default": True, "description": "Auto-rebuild index if stale (auggie finds files augment-lite missed)"}
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="answer.generate",
        description="""Answer questions with citations from codebase.

WHEN TO USE:
• User asks conceptual questions: "why...", "explain...", "what is..."
• Need synthesized explanation (not just raw code)
• Want automatic source citations

WORKFLOW: Automatically calls rag.search internally → synthesizes answer → cites sources

AUTO-SUGGEST: Use this after rag.search when user needs explanation, not just code snippets""",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "task_type": {"type": "string", "default": "lookup"},
                "route": {
                    "type": "string",
                    "default": "auto",
                    "enum": ["auto", "small-fast", "reason-large", "general", "big-mid", "long-context"],
                },
                "temperature": {"type": "number", "default": 0.2},
            },
            "required": ["query"],
        },
        # outputSchema omitted for token efficiency
    ),
    Tool(
        name="answer.accumulated",
        description="""Answer complex questions with multi-aspect evidence accumulation.

WHEN TO USE:
• Complex queries covering multiple aspects (architecture, database, metrics, etc.)
• Previous answer.generate returned "不知道" for some aspects
• Need comprehensive coverage across different code areas

WORKFLOW:
1. Decompose query into 3-5 sub-queries (uses minimax for speed)
2. Execute targeted search for each sub-query
3. Accumulate all evidence (deduplicated)
4. Generate comprehensive answer with full evidence

ADVANTAGE: Solves incomplete index problem by searching multiple aspects separately""",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Complex question covering multiple aspects"},
                "sub_queries": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional: pre-defined sub-queries (auto-generated if not provided)"
                },
                "k_per_query": {"type": "integer", "default": 5, "description": "Results per sub-query"},
                "route": {
                    "type": "string",
                    "default": "reason-large",
                    "enum": ["auto", "small-fast", "reason-large", "general", "big-mid", "long-context"],
                    "description": "Model route for final answer generation"
                },
                "temperature": {"type": "number", "default": 0.2},
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="answer.unified",
        description="""Orchestrate multi-MCP search combining auggie + augment-lite.

WHEN TO USE:
• Need comprehensive results from BOTH semantic (auggie) and RAG (augment-lite) engines
• Complex analysis requiring multiple search rounds
• Following CLAUDE.md Phase 1 dual-MCP workflow

RETURNS: Execution plan with steps for Claude to follow:
1. Call auggie-mcp for semantic search
2. Call augment-lite RAG for local search
3. Execute targeted sub-queries
4. Synthesize final answer with merged evidence

Claude should execute the returned steps in order and merge results.""",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Complex question for multi-engine search"},
                "sub_queries": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional: pre-defined sub-queries"
                },
                "include_auggie": {"type": "boolean", "default": True, "description": "Include auggie-mcp in plan"},
                "route": {
                    "type": "string",
                    "default": "reason-large",
                    "enum": ["auto", "small-fast", "reason-large", "general", "big-mid", "long-context"],
                    "description": "Model route for final synthesis"
                }
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="memory.get",
        description="Get a long-term key. Use project='auto' for active project, or specify project name.",
        inputSchema={
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "project": {"type": "string", "default": "auto", "description": "Project name ('auto' for active project, null for global)"}
            },
            "required": ["key"]
        },
        # outputSchema omitted for token efficiency
    ),
    Tool(
        name="memory.set",
        description="""Store important information for future sessions.

WHEN TO AUTO-SUGGEST:
• User explains architecture: "The system uses microservices..."
• API conventions: "All endpoints return {status, data}..."
• Deployment steps: "To deploy, first... then..."
• Design decisions: "We chose X because..."
• Bug patterns: "This error happens when..."

PROACTIVE: Detect valuable info and suggest storing it automatically""",
        inputSchema={
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "value": {"type": "string"},
                "project": {"type": "string", "default": "auto", "description": "Project name ('auto' for active project, null for global)"}
            },
            "required": ["key", "value"]
        },
        # outputSchema omitted for token efficiency
    ),
    Tool(
        name="task.add",
        description="""Create a new task for tracking multi-step work.

WHEN TO AUTO-SUGGEST:
• User lists steps: "First X, then Y, finally Z"
• User says "TODO", "need to", "remember to"
• User outlines plan: "1. Do A 2. Do B 3. Do C"
• Starting complex feature implementation

PROACTIVE: Auto-create tasks from user's outlined work""",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Task title (required)"},
                "description": {"type": "string", "default": "", "description": "Task description"},
                "priority": {"type": "integer", "default": 0, "description": "Task priority (higher = more important)"},
                "parent_id": {"type": "integer", "description": "Parent task ID (for subtasks)"},
                "project": {"type": "string", "default": "auto", "description": "Project name ('auto' for active project)"}
            },
            "required": ["title"]
        },
        # outputSchema omitted for token efficiency
    ),
    Tool(
        name="task.list",
        description="List tasks with optional filtering.",
        inputSchema={
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["pending", "in_progress", "done", "cancelled"], "description": "Filter by status"},
                "parent_id": {"type": "integer", "description": "Filter by parent ID (null for root tasks)"},
                "project": {"type": "string", "default": "auto", "description": "Project name ('auto' for active project)"}
            },
        },
        # outputSchema omitted for token efficiency
    ),
    Tool(
        name="task.get",
        description="Get a task by ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {"type": "integer", "description": "Task ID"},
                "project": {"type": "string", "default": "auto", "description": "Project name ('auto' for active project)"}
            },
            "required": ["task_id"]
        },
        # outputSchema omitted for token efficiency
    ),
    Tool(
        name="task.update",
        description="Update a task.",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {"type": "integer", "description": "Task ID"},
                "title": {"type": "string", "description": "New title"},
                "description": {"type": "string", "description": "New description"},
                "status": {"type": "string", "enum": ["pending", "in_progress", "done", "cancelled"], "description": "New status"},
                "priority": {"type": "integer", "description": "New priority"},
                "project": {"type": "string", "default": "auto", "description": "Project name ('auto' for active project)"}
            },
            "required": ["task_id"]
        },
        # outputSchema omitted for token efficiency
    ),
    Tool(
        name="task.delete",
        description="Delete a task.",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {"type": "integer", "description": "Task ID"},
                "delete_subtasks": {"type": "boolean", "default": False, "description": "Also delete all subtasks"},
                "project": {"type": "string", "default": "auto", "description": "Project name ('auto' for active project)"}
            },
            "required": ["task_id"]
        },
        # outputSchema omitted for token efficiency
    ),
    Tool(
        name="task.current",
        description="Get the current in-progress task (highest priority).",
        inputSchema={
            "type": "object",
            "properties": {
                "project": {"type": "string", "default": "auto", "description": "Project name ('auto' for active project)"}
            },
        },
        # outputSchema omitted for token efficiency
    ),
    Tool(
        name="task.resume",
        description="Resume a task (set status to in_progress).",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {"type": "integer", "description": "Task ID"},
                "project": {"type": "string", "default": "auto", "description": "Project name ('auto' for active project)"}
            },
            "required": ["task_id"]
        },
        # outputSchema omitted for token efficiency
    ),
    Tool(
        name="task.stats",
        description="Get task statistics (counts by status).",
        inputSchema={
            "type": "object",
            "properties": {
                "project": {"type": "string", "default": "auto", "description": "Project name ('auto' for active project)"}
            },
        },
        # outputSchema omitted for token efficiency
    ),
    # Project Management Tools
    # 專案管理工具 / Project Management Tools
    Tool(
        name="project.status",
        description="Check project initialization status (index, cache, memory)",  # 檢查專案初始化狀態
        inputSchema={
            "type": "object",
            "properties": {
                "project": {"type": "string", "default": "auto", "description": "Project name ('auto' for active project)"}
            },
        },
        # outputSchema omitted for token efficiency
    ),
    Tool(
        name="project.init",
        description="""Initialize and index a project for fast semantic search.

WHEN TO AUTO-SUGGEST:
• User starts work in new directory (detect .git or typical project structure)
• Search returns NO_RESULTS and project not indexed
• User mentions "this codebase" but no index exists

PROACTIVE: Detect unindexed projects and auto-suggest initialization

NOTE: Indexing takes 10-60s depending on codebase size""",  # 初始化專案（自動建立索引）
        inputSchema={
            "type": "object",
            "properties": {
                "project": {"type": "string", "default": "auto", "description": "Project name ('auto' for active project)"},
                "build_vector": {"type": "boolean", "default": True, "description": "Build vector index (if dependencies installed)"}
            },
        },
        # outputSchema omitted for token efficiency
    ),
    Tool(
        name="cache.clear",
        description="Clear cache (exact + semantic cache)",  # 清空快取（精確快取 + 語義快取）
        inputSchema={
            "type": "object",
            "properties": {
                "project": {"type": "string", "default": "auto", "description": "Project name ('auto' for active project)"}
            },
        },
        # outputSchema omitted for token efficiency
    ),
    Tool(
        name="cache.status",
        description="Check cache status (size)",  # 檢查快取狀態（大小）
        inputSchema={
            "type": "object",
            "properties": {
                "project": {"type": "string", "default": "auto", "description": "Project name ('auto' for active project)"}
            },
        },
        # outputSchema omitted for token efficiency
    ),
    Tool(
        name="memory.delete",
        description="Delete a specific memory key. Use project='auto' for active project.",
        inputSchema={
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Memory key to delete"},
                "project": {"type": "string", "default": "auto", "description": "Project name ('auto' for active project, null for global)"}
            },
            "required": ["key"]
        },
        # outputSchema omitted for token efficiency
    ),
    Tool(
        name="memory.list",
        description="List all memory keys for a project. Use project='auto' for active project.",
        inputSchema={
            "type": "object",
            "properties": {
                "project": {"type": "string", "default": "auto", "description": "Project name ('auto' for active project, null for global)"}
            },
        },
        # outputSchema omitted for token efficiency
    ),
    Tool(
        name="memory.clear",
        description="Clear long-term memory",  # 清空長期記憶
        inputSchema={
            "type": "object",
            "properties": {
                "project": {"type": "string", "default": "auto", "description": "Project name ('auto' for active project)"}
            },
        },
        # outputSchema omitted for token efficiency
    ),
    Tool(
        name="index.status",
        description="Check index status (BM25 + vector index)",  # 檢查索引狀態（BM25 + 向量索引）
        inputSchema={
            "type": "object",
            "properties": {
                "project": {"type": "string", "default": "auto", "description": "Project name ('auto' for active project)"}
            },
        },
        # outputSchema omitted for token efficiency
    ),
    Tool(
        name="index.rebuild",
        description="Rebuild index",  # 重建索引
        inputSchema={
            "type": "object",
            "properties": {
                "project": {"type": "string", "default": "auto", "description": "Project name ('auto' for active project)"},
                "vector_only": {"type": "boolean", "default": False, "description": "Only rebuild vector index"}
            },
        },
        # outputSchema omitted for token efficiency
    ),
    # ============================================================
    # Code Analysis Tools (Serena-like)
    # ============================================================
    Tool(
        name="code.symbols",
        description="""Get code symbols overview (classes, functions, methods) from a file.

WHEN TO USE:
• Understanding file structure before editing
• Finding specific class or function definitions
• Navigating unfamiliar code

Returns symbol hierarchy with line numbers.""",
        inputSchema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "File path (relative to project root or absolute)"},
                "depth": {"type": "integer", "default": 2, "description": "Symbol depth (1=top-level, 2=include methods)"},
                "include_body": {"type": "boolean", "default": False, "description": "Include source code body"},
                "project": {"type": "string", "default": "auto"}
            },
            "required": ["file_path"]
        },
    ),
    Tool(
        name="code.find_symbol",
        description="""Find symbol definition by name pattern.

WHEN TO USE:
• Looking for specific class/function by name
• Exploring codebase structure
• Before making cross-file changes

Searches all Python files in project.""",
        inputSchema={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Symbol name or prefix (e.g., 'MyClass', 'handle_')"},
                "file_path": {"type": "string", "description": "Optional: limit search to specific file"},
                "include_body": {"type": "boolean", "default": True, "description": "Include source code"},
                "project": {"type": "string", "default": "auto"}
            },
            "required": ["pattern"]
        },
    ),
    Tool(
        name="code.references",
        description="""Find all references to a symbol in the codebase.

WHEN TO USE:
• Before renaming or refactoring
• Understanding symbol usage patterns
• Finding all call sites

Returns file, line, and context for each reference.""",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Symbol name to find references for"},
                "context_lines": {"type": "integer", "default": 2, "description": "Lines of context"},
                "project": {"type": "string", "default": "auto"}
            },
            "required": ["symbol"]
        },
    ),
    Tool(
        name="search.pattern",
        description="""Search files using regex pattern (complements rag.search semantic search).

WHEN TO USE:
• Exact pattern matching (regex)
• Finding specific code patterns
• When semantic search is too fuzzy

Unlike rag.search, this is literal/regex match, not semantic.""",
        inputSchema={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Regex pattern to search"},
                "file_glob": {"type": "string", "default": "**/*", "description": "File filter (e.g., '**/*.py')"},
                "context_lines": {"type": "integer", "default": 2},
                "case_sensitive": {"type": "boolean", "default": True},
                "project": {"type": "string", "default": "auto"}
            },
            "required": ["pattern"]
        },
    ),
    # ============================================================
    # File Operations Tools (Serena-like)
    # ============================================================
    Tool(
        name="file.read",
        description="""Read file content with optional line range.

WHEN TO USE:
• Reading specific file sections
• Viewing code around specific line numbers
• Getting file content for analysis""",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
                "start_line": {"type": "integer", "description": "Start line (1-indexed)"},
                "end_line": {"type": "integer", "description": "End line (1-indexed)"},
                "project": {"type": "string", "default": "auto"}
            },
            "required": ["path"]
        },
    ),
    Tool(
        name="file.list",
        description="""List directory contents.

WHEN TO USE:
• Exploring project structure
• Finding files in a directory
• Understanding folder organization""",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "default": ".", "description": "Directory path"},
                "recursive": {"type": "boolean", "default": False},
                "pattern": {"type": "string", "description": "Glob pattern filter (e.g., '*.py')"},
                "project": {"type": "string", "default": "auto"}
            },
        },
    ),
    Tool(
        name="file.find",
        description="""Find files by glob pattern.

WHEN TO USE:
• Finding all files of a type
• Locating specific files
• Understanding project file distribution""",
        inputSchema={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Glob pattern (e.g., '**/*.py', 'src/**/*.ts')"},
                "project": {"type": "string", "default": "auto"}
            },
            "required": ["pattern"]
        },
    ),
]

@server.list_tools()
async def _list_tools() -> list[Tool]:
    return TOOLS

@server.list_resources()
async def _list_resources() -> list[dict[str, Any]]:
    """
    Expose available projects and memory as discoverable resources.
    This allows AI to see what data is available without calling tools.
    """
    from mcp.types import Resource

    resources = []

    try:
        # Import lazily to avoid startup delays
        from utils.project_utils import get_all_projects
        from memory.longterm import list_mem

        # Expose registered projects as resources
        projects = get_all_projects()
        for proj_name, proj_info in projects.items():
            root = proj_info.get("root", "")
            chunks_file = DATA_DIR / f"chunks_{proj_name}.jsonl"
            chunks_count = 0
            if chunks_file.exists():
                with open(chunks_file) as f:
                    chunks_count = sum(1 for _ in f)

            resources.append(Resource(
                uri=f"project://{proj_name}",
                name=f"📁 Project: {proj_name}",
                description=f"Code index at {root} ({chunks_count} chunks indexed)",
                mimeType="application/json",
            ))

        # Expose memory as a resource
        try:
            mem_items = list_mem(project="auto")
            mem_count = len(mem_items)
            if mem_count > 0:
                resources.append(Resource(
                    uri="memory://current",
                    name=f"💾 Long-term Memory ({mem_count} items)",
                    description="Stored architectural decisions, API conventions, and important facts",
                    mimeType="application/json",
                ))
        except Exception:
            pass  # Memory might not be initialized yet

        # Expose current directory status
        cwd = os.getcwd()
        cwd_name = Path(cwd).name
        resources.append(Resource(
            uri=f"cwd://{cwd}",
            name=f"📂 Current Directory: {cwd_name}",
            description=f"Working directory: {cwd} (use project.init to index)",
            mimeType="text/plain",
        ))

    except Exception as e:
        # If something fails, still return partial results
        import sys
        print(f"[WARN] Error listing resources: {e}", file=sys.stderr)

    return resources

@server.read_resource()
async def _read_resource(uri: str) -> str:
    """
    Read resource contents. AI can inspect project status and memory.
    """
    import json
    from utils.project_utils import get_project_status
    from memory.longterm import list_mem

    if uri.startswith("project://"):
        project_name = uri.replace("project://", "")
        status = get_project_status(project_name)
        return json.dumps(status, indent=2)

    elif uri == "memory://current":
        mem_items = list_mem(project="auto")
        memory_dict = {
            "count": len(mem_items),
            "items": [{"key": k, "value": v, "updated_at": updated_at} for k, v, updated_at in mem_items]
        }
        return json.dumps(memory_dict, indent=2)

    elif uri.startswith("cwd://"):
        cwd = uri.replace("cwd://", "")
        from utils.project_utils import is_project_registered
        cwd_name = Path(cwd).name

        info = {
            "path": cwd,
            "name": cwd_name,
            "is_indexed": is_project_registered(cwd_name),
            "suggestion": "Run project.init project='auto' to index this directory" if not is_project_registered(cwd_name) else "Already indexed"
        }
        return json.dumps(info, indent=2)

    return json.dumps({"error": "Unknown resource URI"})

def _lazy_engine():
    """Import heavy deps only when needed."""
    # 全部延後到這裡才 import（避免啟動逾時）
    from retrieval.search import hybrid_search, evidence_fingerprints_for_hits
    from providers.registry import get_provider, chat  # 會讀 config/models.yaml（已改成絕對路徑）
    from router import pick_route, get_route_config
    from cache import make_key, get as cache_get, set as cache_set
    from guardrails.abstain import should_abstain
    from memory.longterm import get_mem, set_mem, delete_mem, list_mem
    from tokenizer import estimate_tokens_from_messages
    from memory.tasks import TaskManager
    from retrieval.subagent_filter import hybrid_search_with_subagent
    from retrieval.iterative_search import iterative_search, should_use_iterative_search
    from guardrails.abstain import get_abstain_reason, suggest_query_improvements
    from utils.project_utils import (
        get_project_status, auto_register_project, set_active_project,
        has_bm25_index, clear_cache, clear_memory, get_active_project,
        is_project_registered
    )
    return {
        "hybrid_search": hybrid_search,
        "hybrid_search_with_subagent": hybrid_search_with_subagent,
        "iterative_search": iterative_search,
        "should_use_iterative_search": should_use_iterative_search,
        "evidence_fingerprints_for_hits": evidence_fingerprints_for_hits,
        "get_provider": get_provider,
        "chat": chat,
        "pick_route": pick_route,
        "get_route_config": get_route_config,
        "make_key": make_key,
        "cache_get": cache_get,
        "cache_set": cache_set,
        "should_abstain": should_abstain,
        "get_abstain_reason": get_abstain_reason,
        "suggest_query_improvements": suggest_query_improvements,
        "get_mem": get_mem,
        "set_mem": set_mem,
        "delete_mem": delete_mem,
        "list_mem": list_mem,
        "estimate_tokens_from_messages": estimate_tokens_from_messages,
        "TaskManager": TaskManager,
        "get_project_status": get_project_status,
        "auto_register_project": auto_register_project,
        "set_active_project": set_active_project,
        "has_bm25_index": has_bm25_index,
        "clear_cache": clear_cache,
        "clear_memory": clear_memory,
        "get_active_project": get_active_project,
        "is_project_registered": is_project_registered,
    }

@server.call_tool()
async def _call_tool(name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
    args = arguments or {}

    # 延遲載入
    E = _lazy_engine()

    if name == "rag.search":
        q = str(args.get("query", ""))
        k = int(args.get("k", 8))
        use_subagent = bool(args.get("use_subagent", True))
        use_iterative = bool(args.get("use_iterative", False))
        auto_index = bool(args.get("auto_index", True))  # NEW: Enable auto-indexing by default

        # AUTO-INCREMENTAL INDEXING (acemcp-style)
        if auto_index:
            try:
                import sys
                from retrieval.incremental_indexer import auto_index_if_needed
                from utils.project_utils import resolve_auto_project, get_project_status, load_projects, save_projects

                # Resolve project
                project_name = resolve_auto_project()

                # AUTO-INIT: If no project registered for current directory, auto-init it
                if not project_name and cwd:
                    cwd_path = Path(cwd).resolve()
                    # Use directory name as project name (sanitized)
                    import re
                    raw_name = cwd_path.name
                    # Sanitize: only alphanumeric, underscore, hyphen
                    project_name = re.sub(r'[^a-zA-Z0-9_-]', '-', raw_name)

                    print(f"[AUTO-INIT] Project not registered, auto-initializing: {project_name}", file=sys.stderr)

                    # Register project
                    import hashlib
                    projects = load_projects()
                    project_id = hashlib.md5(str(cwd_path).encode()).hexdigest()[:8]
                    projects[project_name] = {
                        "id": project_id,
                        "root": str(cwd_path),
                        "db": f"data/corpus_{project_name}.duckdb",
                        "chunks": f"data/chunks_{project_name}.jsonl",
                        "active": True,
                    }
                    # Deactivate other projects
                    for name in projects:
                        if name != project_name:
                            projects[name]["active"] = False
                    save_projects(projects)
                    print(f"[AUTO-INIT] Registered project: {project_name} -> {cwd_path}", file=sys.stderr)

                if project_name:
                    status = get_project_status(project_name)
                    project_root = status.get("root")

                    if project_root:
                        # Auto-detect and index changes
                        stats = auto_index_if_needed(project_name, project_root)

                        if stats:
                            print(f"[AUTO-INDEX] Updated index: +{stats['chunks_added']} -{stats['chunks_removed']} ={stats['chunks_total']} total",
                                  file=sys.stderr)
                    else:
                        print(f"[AUTO-INDEX] Project {project_name} not found, skipping auto-index", file=sys.stderr)
                else:
                    print(f"[AUTO-INDEX] No active project and no cwd, skipping auto-index", file=sys.stderr)

            except Exception as e:
                # Don't fail search if auto-index fails
                print(f"[WARN] Auto-index failed: {e}", file=sys.stderr)

        # Auto-enable iterative search for complex queries
        if not use_iterative and E["should_use_iterative_search"](q, task_type="lookup"):
            use_iterative = True

        # Execute search based on mode
        if use_iterative:
            hits = E["iterative_search"](q, k_per_iteration=k, use_subagent=use_subagent, project="auto")
        elif use_subagent:
            hits = E["hybrid_search_with_subagent"](q, k=k, use_subagent=True, project="auto")
        else:
            hits = E["hybrid_search"](q, k=k, project="auto")

        return {"ok": True, "hits": hits}

    if name == "dual.search":
        from retrieval.dual_search import dual_search
        q = str(args.get("query", ""))
        k = int(args.get("k", 8))
        use_subagent = bool(args.get("use_subagent", True))
        use_iterative = bool(args.get("use_iterative", False))
        include_auggie = bool(args.get("include_auggie", True))
        auto_rebuild = bool(args.get("auto_rebuild", True))
        result = dual_search(
            query=q,
            k=k,
            use_subagent=use_subagent,
            use_iterative=use_iterative,
            include_auggie=include_auggie,
            auto_rebuild=auto_rebuild,
            project="auto"
        )
        return result

    if name == "memory.get":
        key = str(args.get("key", ""))
        project = args.get("project", "auto")
        val = E["get_mem"](key, project=project)
        return {"ok": True, "value": val, "project": project}

    if name == "memory.set":
        key = str(args.get("key", ""))
        value = str(args.get("value", ""))
        project = args.get("project", "auto")
        E["set_mem"](key, value, project=project)
        return {"ok": True, "project": project}

    if name == "memory.delete":
        key = str(args.get("key", ""))
        project = args.get("project", "auto")
        E["delete_mem"](key, project=project)
        return {"ok": True, "message": f"Deleted key: {key}", "project": project}

    if name == "memory.list":
        project = args.get("project", "auto")
        items = E["list_mem"](project=project)
        # Convert to list of dicts for better JSON output
        result = [{"key": k, "value": v, "updated_at": updated_at} for k, v, updated_at in items]
        return {"ok": True, "items": result, "count": len(result), "project": project}

    if name == "task.add":
        project = args.get("project", "auto")
        tm = E["TaskManager"](project=project)
        task_id = tm.add_task(
            title=str(args.get("title", "")),
            description=str(args.get("description", "")),
            priority=int(args.get("priority", 0)),
            parent_id=args.get("parent_id")
        )
        return {"ok": True, "task_id": task_id, "project": project}

    if name == "task.list":
        project = args.get("project", "auto")
        tm = E["TaskManager"](project=project)
        tasks = tm.list_tasks(
            status=args.get("status"),
            parent_id=args.get("parent_id")
        )
        return {"ok": True, "tasks": tasks, "count": len(tasks)}

    if name == "task.get":
        project = args.get("project", "auto")
        tm = E["TaskManager"](project=project)
        task = tm.get_task(int(args.get("task_id", 0)))
        if task:
            return {"ok": True, "task": task}
        else:
            return {"ok": False, "error": "Task not found"}

    if name == "task.update":
        project = args.get("project", "auto")
        tm = E["TaskManager"](project=project)
        success = tm.update_task(
            task_id=int(args.get("task_id", 0)),
            title=args.get("title"),
            description=args.get("description"),
            status=args.get("status"),
            priority=args.get("priority")
        )
        if success:
            task = tm.get_task(int(args.get("task_id", 0)))
            return {"ok": True, "task": task}
        else:
            return {"ok": False, "error": "Task not found or update failed"}

    if name == "task.delete":
        project = args.get("project", "auto")
        tm = E["TaskManager"](project=project)
        success = tm.delete_task(
            task_id=int(args.get("task_id", 0)),
            delete_subtasks=bool(args.get("delete_subtasks", False))
        )
        return {"ok": success}

    if name == "task.current":
        project = args.get("project", "auto")
        tm = E["TaskManager"](project=project)
        task = tm.get_current_task()
        if task:
            return {"ok": True, "task": task}
        else:
            return {"ok": True, "task": None, "message": "No in-progress tasks"}

    if name == "task.resume":
        project = args.get("project", "auto")
        tm = E["TaskManager"](project=project)
        task = tm.resume_task(int(args.get("task_id", 0)))
        if task:
            return {"ok": True, "task": task}
        else:
            return {"ok": False, "error": "Task not found"}

    if name == "task.stats":
        project = args.get("project", "auto")
        tm = E["TaskManager"](project=project)
        stats = tm.get_stats()
        return {"ok": True, "stats": stats}

    if name == "answer.generate":
        query = str(args.get("query", ""))
        task = str(args.get("task_type", "lookup"))
        route_override = str(args.get("route", "auto"))
        temperature = float(args.get("temperature", 0.2))

        # Use enhanced search with subagent filtering
        # Automatically use iterative search for complex tasks
        use_iterative = E["should_use_iterative_search"](query, task_type=task)

        if use_iterative:
            hits = E["iterative_search"](query, k_per_iteration=8, use_subagent=True, project="auto")[:5]
        else:
            hits = E["hybrid_search_with_subagent"](query, k=8, use_subagent=True, project="auto")[:5]

        # Enhanced abstain check - concise error codes for LLM
        if E["should_abstain"](hits, min_diversity=2):
            error_code = E["get_abstain_reason"](hits, min_diversity=2)
            E["suggest_query_improvements"](query, hits)  # Logs to stderr only
            return {"ok": True, "answer": f"Search failed: {error_code}", "citations": [], "abstained": True}

        system = ("你只能根據 Evidence 回答；每個關鍵結論後面附【source:<file:line>|<url#heading>】。"
                  "若證據不足請明確說不知道，並列出需要的檔案或關鍵字。")
        evidence = "\n\n".join([f"[{h['source']}]\n{h['text']}" for h in hits])
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"# Query\n{query}\n\n# Evidence\n{evidence}"},
        ]

        total_tokens_est = E["estimate_tokens_from_messages"](messages)

        # Get route config (includes model and max_output_tokens)
        route_config = E["get_route_config"](task, total_tokens_est, route_override=route_override)
        model_alias = route_config["model"]
        max_output_tokens = route_config["max_output_tokens"]

        ev_fp = E["evidence_fingerprints_for_hits"](hits)
        key = E["make_key"](
            model=model_alias,
            messages=messages,
            extra={"temperature": temperature, "task": task, "route": route_override, "token_est": total_tokens_est},
            evidence_fingerprints=ev_fp,
            project="auto",  # Use active project for cache
        )
        cached = E["cache_get"](key)
        if cached:
            return {"ok": True, **cached, "cached": True}

        provider = E["get_provider"](model_alias)
        answer = E["chat"](provider, messages, temperature=temperature, seed=7, max_output_tokens=max_output_tokens)
        payload = {"answer": answer, "citations": [h["source"] for h in hits]}
        E["cache_set"](key, payload, ttl_sec=7200)
        return {"ok": True, **payload, "cached": False}

    if name == "answer.accumulated":
        from retrieval.accumulated_answer import generate_accumulated_answer
        query = str(args.get("query", ""))
        sub_queries = args.get("sub_queries")  # Optional list
        k_per_query = int(args.get("k_per_query", 5))
        route = str(args.get("route", "reason-large"))
        temperature = float(args.get("temperature", 0.2))
        result = generate_accumulated_answer(
            query=query,
            sub_queries=sub_queries,
            k_per_query=k_per_query,
            route=route,
            temperature=temperature,
            project="auto"
        )
        return result

    if name == "answer.unified":
        from retrieval.unified_orchestrator import create_execution_plan
        query = str(args.get("query", ""))
        sub_queries = args.get("sub_queries")  # Optional list
        include_auggie = bool(args.get("include_auggie", True))
        route = str(args.get("route", "reason-large"))
        plan = create_execution_plan(
            query=query,
            sub_queries=sub_queries,
            include_auggie=include_auggie,
            route=route
        )
        return plan

    # Project Management Tools
    if name == "project.status":
        project = args.get("project", "auto")
        # Direct import to avoid E dictionary issues
        from utils.project_utils import get_project_status
        status = get_project_status(project)
        return {"ok": True, "status": status}

    if name == "project.init":
        import subprocess
        import sys
        from utils.validators import validate_project_path, validate_project_name

        project = args.get("project", "auto")
        build_vector = bool(args.get("build_vector", True))

        # Get current working directory as project root
        cwd = os.getcwd()

        # Validate path (security: prevent command injection)
        try:
            validated_cwd = validate_project_path(cwd)
            cwd = str(validated_cwd)
        except ValueError as e:
            return {"ok": False, "error": f"Invalid project path: {e}"}

        # Auto-detect project name if needed
        if project == "auto":
            project = Path(cwd).name

        # Validate project name (security: prevent injection)
        try:
            project = validate_project_name(project, allow_auto=False)
        except ValueError as e:
            return {"ok": False, "error": f"Invalid project name: {e}"}

        # Direct import to avoid E dictionary issues
        from utils.project_utils import auto_register_project, has_bm25_index, get_project_status

        # Register project
        if not auto_register_project(project, cwd):
            return {
                "ok": False,
                "error": f"Invalid project directory: {cwd}",
                "suggestion": "Ensure directory contains code files"
            }

        # Build BM25 index
        if not has_bm25_index(project):
            build_script = BASE / "retrieval" / "build_index.py"
            projects = get_project_status(project)

            # Use DATA_DIR for consistent storage location
            db_path = DATA_DIR / f"corpus_{project}.duckdb"
            chunks_path = DATA_DIR / f"chunks_{project}.jsonl"

            cmd = [
                sys.executable,
                str(build_script),
                "--root", cwd,
                "--db", str(db_path),
                "--chunks", str(chunks_path),
            ]

            try:
                # Run in MCP server directory context
                subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=str(BASE))
            except subprocess.CalledProcessError as e:
                return {
                    "ok": False,
                    "error": f"Failed to build BM25 index: {e}",
                    "stderr": e.stderr if e.stderr else ""
                }

        # Build vector index if requested and dependencies available
        vector_build_error = None
        if build_vector:
            try:
                import faiss
                import sentence_transformers

                build_vector_script = BASE / "retrieval" / "build_vector_index.py"
                cmd = [sys.executable, str(build_vector_script), "--project", project]

                # Run in MCP server directory context
                result = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=str(BASE))
                if result.returncode != 0:
                    vector_build_error = f"Vector index build failed: {result.stderr}"
            except ImportError as e:
                vector_build_error = f"Vector dependencies not installed: {e}"
            except subprocess.CalledProcessError as e:
                vector_build_error = f"Failed to build vector index: {e.stderr if e.stderr else str(e)}"
            except Exception as e:
                vector_build_error = f"Unexpected error building vector index: {str(e)}"

        # Set as active project
        from utils.project_utils import set_active_project
        set_active_project(project)

        response_data = {
            "ok": True,
            "message": f"Project initialized: {project}",
            "project": project,
            "bm25_index": "created" if not has_bm25_index(project) else "already exists"
        }

        if build_vector:
            if vector_build_error:
                response_data["vector_index"] = "failed"
                response_data["vector_error"] = vector_build_error
            else:
                response_data["vector_index"] = "created"

        return response_data

    if name == "cache.clear":
        project = args.get("project", "auto")
        # Direct import to avoid E dictionary issues
        from utils.project_utils import clear_cache
        result = clear_cache(project)
        return result

    if name == "cache.status":
        project = args.get("project", "auto")
        from utils.project_utils import get_cache_size
        size = get_cache_size(project)
        return {
            "ok": True,
            "cache_size": size
        }

    if name == "memory.clear":
        project = args.get("project", "auto")
        # Direct import to avoid E dictionary issues
        from utils.project_utils import clear_memory
        result = clear_memory(project)
        return result

    if name == "index.status":
        project = args.get("project", "auto")
        # Direct import to avoid E dictionary issues
        from utils.project_utils import get_project_status
        status = get_project_status(project)

        index_status = {
            "bm25": status.get("bm25_index", {}),
            "vector": status.get("vector_index", {})
        }

        return {
            "ok": True,
            "status": index_status
        }

    if name == "index.rebuild":
        import subprocess
        import sys
        from utils.validators import validate_project_name, validate_project_path

        # Direct import to avoid E dictionary issues - import at the beginning
        from utils.project_utils import is_project_registered, get_active_project, get_project_status

        try:
            project = args.get("project", "auto")
            vector_only = bool(args.get("vector_only", False))

            if project == "auto":
                # Use unified auto project resolution
                from utils.project_utils import resolve_auto_project
                project = resolve_auto_project()

                if not project:
                    return {
                        "ok": False,
                        "error": "Cannot determine project: no active project and current directory not registered"
                    }

            # Validate project name (security)
            project = validate_project_name(project, allow_auto=False)

        except ValueError as e:
            return {"ok": False, "error": f"Invalid project name: {e}"}
        except Exception as e:
            return {
                "ok": False,
                "error": f"Failed to determine project: {str(e)}" if DEBUG else "Failed to determine project"
            }

        if not project:
            return {
                "ok": False,
                "error": "No active project and cannot detect from current directory"
            }

        # Now get_project_status is properly imported
        status = get_project_status(project)
        root = status.get("root")

        # Validate root path (security)
        if root:
            try:
                root = str(validate_project_path(root))
            except ValueError as e:
                return {"ok": False, "error": f"Invalid project root: {e}"}

        # If project not registered yet, use current directory as root
        if not root:
            root = cwd

        if not root:
            return {
                "ok": False,
                "error": f"Project not found: {project}"
            }

        # Rebuild BM25 index
        if not vector_only:
            build_script = BASE / "retrieval" / "build_index.py"

            # Use DATA_DIR for consistent storage location
            db_path = DATA_DIR / f"corpus_{project}.duckdb"
            chunks_path = DATA_DIR / f"chunks_{project}.jsonl"

            # Prefer venv Python (has duckdb installed) over system Python
            venv_python = BASE / ".venv" / "bin" / "python"
            python_exe = str(venv_python) if venv_python.exists() else sys.executable

            cmd = [
                python_exe,
                str(build_script),
                "--root", root,
                "--db", str(db_path),
                "--chunks", str(chunks_path),
            ]

            try:
                # Run in MCP server directory context
                result = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=str(BASE))
            except subprocess.CalledProcessError as e:
                return {
                    "ok": False,
                    "error": f"Failed to rebuild BM25 index: {e}",
                    "stderr": e.stderr if e.stderr else "",
                    "stdout": e.stdout if e.stdout else "",
                    "cmd": " ".join(cmd),
                    "hint": "Check if duckdb is installed in the Python environment"
                }

        # Rebuild vector index
        vector_rebuild_error = None
        try:
            import faiss
            import sentence_transformers

            build_vector_script = BASE / "retrieval" / "build_vector_index.py"
            # Reuse venv_python if defined, otherwise detect
            if 'python_exe' not in locals():
                venv_python = BASE / ".venv" / "bin" / "python"
                python_exe = str(venv_python) if venv_python.exists() else sys.executable
            cmd = [python_exe, str(build_vector_script), "--project", project]

            # Run in MCP server directory context
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=str(BASE))
        except ImportError as e:
            vector_rebuild_error = f"Vector dependencies not installed: {e}"
            if vector_only:
                return {
                    "ok": False,
                    "error": vector_rebuild_error,
                    "suggestion": "Run: bash scripts/install_vector_deps.sh"
                }
        except subprocess.CalledProcessError as e:
            vector_rebuild_error = f"Failed to rebuild vector index: {e.stderr if e.stderr else str(e)}"
            return {
                "ok": False,
                "error": vector_rebuild_error,
                "stderr": e.stderr if e.stderr else ""
            }
        except Exception as e:
            vector_rebuild_error = f"Unexpected error: {str(e)}"
            return {
                "ok": False,
                "error": vector_rebuild_error
            }

        response_data = {
            "ok": True,
            "message": f"Index rebuilt for project: {project}"
        }

        if vector_only:
            response_data["bm25_index"] = "skipped"
            response_data["vector_index"] = "rebuilt" if not vector_rebuild_error else "failed"
        else:
            response_data["bm25_index"] = "rebuilt"
            response_data["vector_index"] = "rebuilt" if not vector_rebuild_error else "failed"

        if vector_rebuild_error:
            response_data["vector_error"] = vector_rebuild_error

        return response_data

    # ============================================================
    # Code Analysis Tools (Serena-like)
    # ============================================================
    if name == "code.symbols":
        from code.symbols import extract_symbols
        from utils.project_utils import get_project_status, resolve_auto_project

        file_path = str(args.get("file_path", ""))
        depth = int(args.get("depth", 2))
        include_body = bool(args.get("include_body", False))
        project = args.get("project", "auto")

        # Resolve project root
        project_name = resolve_auto_project() if project == "auto" else project
        status = get_project_status(project_name) if project_name else {}
        project_root = status.get("root", os.getcwd())

        # Resolve file path
        full_path = Path(file_path)
        if not full_path.is_absolute():
            full_path = Path(project_root) / file_path

        if not full_path.exists():
            return {"ok": False, "error": f"File not found: {file_path}"}

        symbols = extract_symbols(str(full_path), depth=depth, include_body=include_body)
        return {"ok": True, "file": str(full_path), "symbols": symbols, "count": len(symbols)}

    if name == "code.find_symbol":
        from code.symbols import find_symbol
        from utils.project_utils import get_project_status, resolve_auto_project

        pattern = str(args.get("pattern", ""))
        file_path = args.get("file_path")
        include_body = bool(args.get("include_body", True))
        project = args.get("project", "auto")

        # Resolve project root
        project_name = resolve_auto_project() if project == "auto" else project
        status = get_project_status(project_name) if project_name else {}
        project_root = status.get("root", os.getcwd())

        results = find_symbol(
            pattern,
            file_path=file_path,
            project_root=project_root,
            include_body=include_body
        )
        return {"ok": True, "pattern": pattern, "results": results, "count": len(results)}

    if name == "code.references":
        from code.references import find_references
        from utils.project_utils import get_project_status, resolve_auto_project

        symbol = str(args.get("symbol", ""))
        context_lines = int(args.get("context_lines", 2))
        project = args.get("project", "auto")

        # Resolve project root
        project_name = resolve_auto_project() if project == "auto" else project
        status = get_project_status(project_name) if project_name else {}
        project_root = status.get("root", os.getcwd())

        results = find_references(symbol, project_root, context_lines=context_lines)
        return {"ok": True, "symbol": symbol, "references": results, "count": len(results)}

    if name == "search.pattern":
        from code.pattern_search import search_pattern
        from utils.project_utils import get_project_status, resolve_auto_project

        pattern = str(args.get("pattern", ""))
        file_glob = str(args.get("file_glob", "**/*"))
        context_lines = int(args.get("context_lines", 2))
        case_sensitive = bool(args.get("case_sensitive", True))
        project = args.get("project", "auto")

        # Resolve project root
        project_name = resolve_auto_project() if project == "auto" else project
        status = get_project_status(project_name) if project_name else {}
        project_root = status.get("root", os.getcwd())

        results = search_pattern(
            pattern, project_root,
            file_glob=file_glob,
            context_lines=context_lines,
            case_sensitive=case_sensitive
        )
        return {"ok": True, "pattern": pattern, "matches": results, "count": len(results)}

    # ============================================================
    # File Operations Tools (Serena-like)
    # ============================================================
    if name == "file.read":
        from file.reader import read_file
        from utils.project_utils import get_project_status, resolve_auto_project

        path = str(args.get("path", ""))
        start_line = args.get("start_line")
        end_line = args.get("end_line")
        project = args.get("project", "auto")

        # Resolve project root
        project_name = resolve_auto_project() if project == "auto" else project
        status = get_project_status(project_name) if project_name else {}
        project_root = status.get("root", os.getcwd())

        result = read_file(path, project_root=project_root, start_line=start_line, end_line=end_line)
        return result

    if name == "file.list":
        from file.finder import list_directory
        from utils.project_utils import get_project_status, resolve_auto_project

        path = str(args.get("path", "."))
        recursive = bool(args.get("recursive", False))
        pattern = args.get("pattern")
        project = args.get("project", "auto")

        # Resolve project root
        project_name = resolve_auto_project() if project == "auto" else project
        status = get_project_status(project_name) if project_name else {}
        project_root = status.get("root", os.getcwd())

        result = list_directory(path, project_root=project_root, recursive=recursive, pattern=pattern)
        return result

    if name == "file.find":
        from file.finder import find_files
        from utils.project_utils import get_project_status, resolve_auto_project

        pattern = str(args.get("pattern", ""))
        project = args.get("project", "auto")

        # Resolve project root
        project_name = resolve_auto_project() if project == "auto" else project
        status = get_project_status(project_name) if project_name else {}
        project_root = status.get("root", os.getcwd())

        result = find_files(pattern, project_root)
        return result

    return {"ok": False, "error": f"unknown tool {name}"}

async def amain():
    async with stdio_server() as (read, write):
        init_options = InitializationOptions(
            server_name="augment-lite",
            server_version="1.3.2",
            capabilities=server.get_capabilities(
                notification_options=NotificationOptions(),
                experimental_capabilities={},
            ),
        )
        await server.run(read, write, init_options)

def _clear_pycache():
    """Clear __pycache__ directories on startup to avoid stale bytecode."""
    import shutil
    base = Path(__file__).parent
    for pycache in base.rglob("__pycache__"):
        if ".venv" not in str(pycache):
            shutil.rmtree(pycache, ignore_errors=True)

if __name__ == "__main__":
    _clear_pycache()
    asyncio.run(amain())
