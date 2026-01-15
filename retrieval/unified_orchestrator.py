"""
Unified Answer Orchestrator

Returns structured execution plan for Claude to orchestrate:
1. auggie-mcp semantic search
2. augment-lite accumulated RAG search
3. Merge results and generate final answer

This enables automatic multi-MCP coordination without direct inter-MCP calls.
"""

import logging
from typing import List, Dict, Optional
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

logger = logging.getLogger(__name__)


def create_execution_plan(
    query: str,
    sub_queries: Optional[List[str]] = None,
    include_auggie: bool = True,
    route: str = "reason-large"
) -> Dict:
    """
    Create structured execution plan for Claude to follow.

    Args:
        query: User's complex question
        sub_queries: Optional pre-defined sub-queries
        include_auggie: Whether to include auggie in the plan
        route: Model route for final answer

    Returns:
        Execution plan with steps for Claude
    """
    from retrieval.accumulated_answer import decompose_query

    # Auto-decompose query if not provided
    if not sub_queries:
        sub_queries = decompose_query(query)

    steps = []
    step_num = 1

    # Step 1: Auggie semantic search (if enabled)
    if include_auggie:
        safe_query = query.replace('"', "'")
        steps.append({
            "step": step_num,
            "action": "call_mcp",
            "tool": "mcp__auggie-mcp__codebase-retrieval",
            "params": {
                "information_request": safe_query
            },
            "purpose": "Semantic code understanding from Auggie",
            "store_as": "auggie_results"
        })
        step_num += 1

    # Step 2: Augment-lite accumulated search
    steps.append({
        "step": step_num,
        "action": "call_mcp",
        "tool": "mcp__augment-lite__rag_search",
        "params": {
            "query": query,
            "k": 8,
            "use_subagent": True,
            "use_iterative": True
        },
        "purpose": "Local RAG search with BM25 + vector",
        "store_as": "rag_results"
    })
    step_num += 1

    # Step 3: Additional sub-query searches for comprehensive coverage
    for i, sub_q in enumerate(sub_queries[:3]):  # Max 3 additional
        steps.append({
            "step": step_num,
            "action": "call_mcp",
            "tool": "mcp__augment-lite__rag_search",
            "params": {
                "query": sub_q,
                "k": 5,
                "use_subagent": True
            },
            "purpose": f"Targeted search: {sub_q[:40]}...",
            "store_as": f"sub_results_{i+1}"
        })
        step_num += 1

    # Step 4: Final answer generation with merged evidence
    steps.append({
        "step": step_num,
        "action": "synthesize",
        "instruction": (
            "Merge all results from previous steps (auggie_results, rag_results, sub_results_*). "
            "Deduplicate by source file. "
            "Generate comprehensive answer addressing all aspects of the query. "
            "Cite sources as [source:file:line]."
        ),
        "route": route,
        "purpose": "Generate final answer with all accumulated evidence"
    })

    return {
        "ok": True,
        "plan_type": "unified_search",
        "query": query,
        "sub_queries": sub_queries,
        "total_steps": len(steps),
        "steps": steps,
        "execution_hint": (
            "Execute steps 1-{} in order. Store results from each step. "
            "In the final synthesize step, combine all stored results to generate answer."
        ).format(step_num - 1),
        "auto_rebuild_hint": (
            "If auggie returns files that rag_search misses (>50% difference), "
            "call mcp__augment-lite__index_rebuild(project='auto') before synthesize step."
        )
    }


def format_plan_as_instructions(plan: Dict) -> str:
    """
    Format execution plan as human-readable instructions.

    Args:
        plan: Execution plan from create_execution_plan

    Returns:
        Formatted instruction string
    """
    lines = [
        f"## Unified Search Execution Plan",
        f"Query: {plan['query']}",
        f"Total Steps: {plan['total_steps']}",
        "",
        "### Steps:"
    ]

    for step in plan["steps"]:
        if step["action"] == "call_mcp":
            lines.append(f"\n**Step {step['step']}**: {step['purpose']}")
            lines.append(f"Tool: `{step['tool']}`")
            lines.append(f"Params: `{step['params']}`")
            lines.append(f"Store result as: `{step['store_as']}`")
        elif step["action"] == "synthesize":
            lines.append(f"\n**Step {step['step']}**: {step['purpose']}")
            lines.append(f"Route: `{step['route']}`")
            lines.append(f"Instruction: {step['instruction']}")

    lines.append(f"\n### Execution Hint")
    lines.append(plan["execution_hint"])

    return "\n".join(lines)
