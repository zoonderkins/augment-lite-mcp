from pathlib import Path
BASE = Path(__file__).resolve().parent

import sys, json, traceback
from cache import make_key, get as cache_get, set as cache_set
from router import pick_route
from providers.registry import get_provider, openai_chat, ProviderError
from retrieval.search import hybrid_search, evidence_fingerprints_for_hits
from guardrails.abstain import should_abstain
from memory.longterm import get_mem, set_mem
from tokenizer import estimate_tokens_from_messages

def _ok(**kw): return {"ok": True, **kw}

def handle(req):
    name = req.get("method") or req.get("tool") or req.get("name")
    p = req.get("params") or req.get("arguments") or {}

    if name == "answer.generate":
        query = p.get("query","")
        task = p.get("task_type","lookup")
        temperature = float(p.get("temperature", 0.2))
        route_override = p.get("route", "auto")

        hits = hybrid_search(query, k=8)[:5]
        if should_abstain(hits):
            return _ok(answer="需要更多相關檔案或關鍵字才能回答。", citations=[])

        system = ("你只能根據 Evidence 回答；每個關鍵結論後面附【source:<file:line>|<url#heading>】。"
                  "若證據不足請明確說不知道，並列出需要的檔案或關鍵字。")
        evidence = "\n\n".join([f"[{h['source']}]\n{h['text']}" for h in hits])
        messages = [
            {"role":"system","content":system},
            {"role":"user","content":f"# Query\n{query}\n\n# Evidence\n{evidence}"}
        ]

        total_tokens_est = estimate_tokens_from_messages(messages)
        model_alias = pick_route(task, total_tokens_est, route_override=route_override)

        ev_fp = evidence_fingerprints_for_hits(hits)
        key = make_key(model=model_alias, messages=messages,
                       extra={"temperature":temperature, "task":task, "route": route_override,
                              "token_est": total_tokens_est},
                       evidence_fingerprints=ev_fp)
        cached = cache_get(key)
        if cached:
            return _ok(answer=cached["answer"], citations=cached["citations"], cached=True)

        provider = get_provider(model_alias)
        try:
            answer = openai_chat(provider, messages, temperature=temperature, seed=7)
        except ProviderError as e:
            # naive fallback chain
            if route_override == "auto":
                # step down one level
                try_alias = "big-mid" if model_alias == "requesty-gemini" else "small-fast"
                # map route name to provider
                from router import CFG
                if try_alias in CFG["routes"]:
                    model_alias = CFG["routes"][try_alias]["model"]
                    provider = get_provider(model_alias)
                    answer = openai_chat(provider, messages, temperature=temperature, seed=7)
                else:
                    raise
            else:
                raise

        cache_set(key, {"answer":answer, "citations":[h["source"] for h in hits]}, ttl_sec=7200)
        return _ok(answer=answer, citations=[h["source"] for h in hits], cached=False)

    if name == "rag.search":
        q = p.get("query","")
        k = int(p.get("k",8))
        return _ok(hits=hybrid_search(q, k=k))

    if name == "memory.get":
        return _ok(value=get_mem(p.get("key","")))

    if name == "memory.set":
        set_mem(p.get("key",""), p.get("value",""))
        return _ok(ok=True)

    if name == "postcheck.code":
        from postcheck.code_checks import run_checks
        return _ok(report=run_checks(p.get("repo_path",".") ))

    return {"ok": False, "error": f"unknown method {name}"}

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line: 
            continue
        try:
            req = json.loads(line)
            res = handle(req)
        except Exception as e:
            res = {"ok": False, "error": str(e), "trace": traceback.format_exc()}
        out = {"id": (req.get("id") if 'req' in locals() else None), **res}
        sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
        sys.stdout.flush()

if __name__ == "__main__":
    main()