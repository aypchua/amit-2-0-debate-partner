"""Provider bake-off: same prompt, same transcript, every available provider, N rounds.

Writes bench_out/blind.md (outputs labelled A, B, C... with the provider hidden) for Andrew to score on wit,
and bench_out/key.md (the mapping + latencies). Usage:
    uv run python bench.py [rounds=2] [transcript=../content/99-mock-opposition-speech.txt]
"""
from __future__ import annotations

import asyncio
import random
import sys
import time
from pathlib import Path

import httpx

import llm

HERE = Path(__file__).parent
OUT = HERE / "bench_out"


async def run_one(p: llm.Provider, transcript: str, mode: str = "rebut") -> dict:
    messages = llm.build_messages(mode, transcript)
    t0 = time.perf_counter()
    ttft = None
    text = ""
    err = None
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=5.0)) as client:
            async for delta in llm.stream_for(p, messages, client):
                if ttft is None:
                    ttft = time.perf_counter() - t0
                text += delta
    except Exception as e:  # noqa: BLE001
        err = str(e)
    return {"provider": p.name, "model": p.model, "ttft_ms": int((ttft or 0) * 1000), "total_ms": int((time.perf_counter() - t0) * 1000),
            "text": text.strip(), "error": err}


async def main() -> None:
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    tpath = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE.parent / "content" / "99-mock-opposition-speech.txt"
    transcript = tpath.read_text()
    providers = [p for p in llm.load_providers() if p.available]
    loc = next((p for p in providers if p.kind == "ollama"), None)
    if loc:
        print("warming local:", await llm.warm_ollama(loc))
    results = []
    for r in range(rounds):
        for p in providers:
            res = await run_one(p, transcript)
            res["round"] = r + 1
            results.append(res)
            status = f"ERROR {res['error'][:80]}" if res["error"] else f"ttft {res['ttft_ms']} ms, total {res['total_ms']} ms"
            print(f"[{r+1}] {p.name:9s} {status}")
    OUT.mkdir(exist_ok=True)
    good = [r for r in results if not r["error"]]
    random.shuffle(good)
    labels = [chr(65 + i) for i in range(len(good))]
    blind = ["# Blind bake-off: score each 1-5 on 'would I read this on stage?'\n"]
    key = ["# Key\n", "| Label | Provider | Model | Round | TTFT ms | Total ms |", "|---|---|---|---|---|---|"]
    for lab, r in zip(labels, good):
        blind.append(f"\n## {lab}\n\n{r['text']}\n")
        key.append(f"| {lab} | {r['provider']} | {r['model']} | {r['round']} | {r['ttft_ms']} | {r['total_ms']} |")
    errs = [r for r in results if r["error"]]
    if errs:
        key.append("\n## Errors\n" + "\n".join(f"- {r['provider']}: {r['error'][:200]}" for r in errs))
    (OUT / "blind.md").write_text("\n".join(blind))
    (OUT / "key.md").write_text("\n".join(key))
    print(f"\nwrote {OUT/'blind.md'} and {OUT/'key.md'}")


if __name__ == "__main__":
    asyncio.run(main())
