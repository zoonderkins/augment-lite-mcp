#!/usr/bin/env python
"""
測試 Gemini local proxy 與 MCP augment-lite 整合
"""
import os
import sys

# 添加當前目錄到 path (必須在 import 之前)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 設置環境變數 (必須在 import providers 之前)
# Port 8084 proxy 使用 "dummy" 即可
os.environ['GEMINI_LOCAL_KEY'] = 'dummy'

print(f"✓ 環境變數設置: GEMINI_LOCAL_KEY={os.environ.get('GEMINI_LOCAL_KEY')}")

def test_gemini_basic():
    """測試 Gemini 基本調用"""
    print("=" * 60)
    print("TEST 1: Gemini 基本調用")
    print("=" * 60)

    from providers.registry import get_provider, openai_chat

    provider = get_provider('gemini-local')
    print(f"✓ Provider: {provider['model_id']}")
    print(f"✓ Base URL: {provider['base']}")

    response = openai_chat(
        provider,
        [{'role': 'user', 'content': '用中文說一句問候語'}],
        temperature=0.2,
        max_output_tokens=50
    )

    print(f"✓ Response: {response}")
    print(f"✓ Type: {type(response)}")
    assert response is not None, "Response should not be None"
    assert len(response) > 0, "Response should not be empty"
    print("✅ TEST 1 PASSED\n")

def test_rag_search():
    """測試 RAG 搜索"""
    print("=" * 60)
    print("TEST 2: RAG 搜索（不使用 Subagent）")
    print("=" * 60)

    from retrieval.search import hybrid_search

    results = hybrid_search(
        query='Gemini configuration',
        k=3,
        project='auto'
    )

    print(f"✓ 找到 {len(results)} 個結果")
    for i, r in enumerate(results, 1):
        print(f"  {i}. {r['source'][:80]}... (score: {r.get('score', 0):.3f})")

    assert len(results) > 0, "Should find results"
    print("✅ TEST 2 PASSED\n")

def test_subagent_filter():
    """測試 Subagent 過濾"""
    print("=" * 60)
    print("TEST 3: Subagent 過濾（使用 Gemini）")
    print("=" * 60)

    from retrieval.subagent_filter import subagent_filter

    candidates = [
        {'text': 'System prompts 配置支援多模型客製化', 'source': 'config/system_prompts.yaml', 'score': 0.90},
        {'text': 'Gemini local proxy 使用 Port 8084', 'source': 'docs/GEMINI_LOCAL_PROXY.md', 'score': 0.88},
        {'text': 'MCP 專案管理工具', 'source': 'docs/MCP_PROJECT_MANAGEMENT.md', 'score': 0.75},
    ]

    print(f"✓ 候選數: {len(candidates)}")

    filtered = subagent_filter(
        query='Gemini 配置',
        candidates=candidates,
        max_results=2,
        model='gemini-local',
        use_llm=True
    )

    print(f"✓ 過濾後: {len(filtered)} 個結果")
    for i, r in enumerate(filtered, 1):
        print(f"  {i}. {r['source']} (score: {r.get('score', 0):.3f})")

    assert len(filtered) > 0, "Should have filtered results"
    print("✅ TEST 3 PASSED\n")

def test_answer_generation():
    """測試完整的 RAG + 答案生成"""
    print("=" * 60)
    print("TEST 4: 完整 answer.generate 流程")
    print("=" * 60)

    from retrieval.search import hybrid_search
    from providers.registry import get_provider, openai_chat

    # Step 1: RAG 搜索
    query = 'What is Gemini local proxy'
    hits = hybrid_search(query, k=3, project='auto')

    print(f"✓ RAG 搜索: {len(hits)} 個結果")

    # Step 2: 構建上下文
    context = '\n\n'.join([
        f"Source: {h['source']}\n{h['text'][:200]}..."
        for h in hits[:2]
    ])

    # Step 3: 使用 Gemini 生成回答
    provider = get_provider('gemini-local')

    messages = [
        {
            'role': 'user',
            'content': f"""Based on the following context, answer the question concisely.

Context:
{context}

Question: {query}

Answer in 2-3 sentences:"""
        }
    ]

    print("✓ 調用 Gemini...")
    response = openai_chat(
        provider,
        messages,
        temperature=0.2,
        max_output_tokens=200
    )

    print(f"✓ Gemini 回答:\n{response}\n")

    assert response is not None, "Response should not be None"
    assert len(response) > 0, "Response should not be empty"
    print("✅ TEST 4 PASSED\n")

def main():
    """執行所有測試"""
    print("\n🚀 開始測試 Gemini + MCP augment-lite 整合\n")

    try:
        test_gemini_basic()
        test_rag_search()
        test_subagent_filter()
        test_answer_generation()

        print("=" * 60)
        print("🎉 所有測試通過!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
