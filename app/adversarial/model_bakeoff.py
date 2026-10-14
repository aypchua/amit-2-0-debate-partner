"""Model bake-off: same prompt, same opposition speeches, several candidate models; automatic compliance score
plus a blind sheet for Andrew to score wit. Runs against providers directly (no server needed; Ollama must be up).

    uv run python adversarial/model_bakeoff.py adversarial/candidates.json [speeches=3]

Compliance checks (all automatic):
  - forbidden words / repeated wording / unverified percentages  -> llm.quality_problems
  - fabricated first-person events ("yesterday I", "last quarter we", "we lost the deal", "I watched a CISO")
  - addressing Andrew, speaker labels, leaked markdown
  - length 150-260 words
  - counters used: how many distinct flips from counters.md / system.md appear (rough proxy for using the bank)
"""
from __future__ import annotations

import asyncio
import json
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import llm  # noqa: E402

HERE = Path(__file__).parent
FABRICATION = re.compile(r"\b(yesterday|last (?:week|month|quarter|year)|we lost (?:a|the) deal|i (?:watched|saw|sat with|met)|our (?:ai|agent|sandbox|portal) (?:already|just|yesterday))\b", re.I)
LEAKS = re.compile(r"(^\s*andrew:|\bandrew\b|\*\*|^#)", re.I | re.M)


def flip_phrases() -> list[str]:
    """Distinctive fragments of our flips, used to count bank usage."""
    frags = []
    for path in (HERE.parent / "prompts" / "counters.md", HERE.parent / "prompts" / "system.md"):
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            if "->" in line:
                right = line.split("->", 1)[1]
                for sent in re.split(r"[.;!?]", right):
                    words = re.findall(r"[a-z']+", sent.lower())
                    if len(words) >= 5:
                        frags.append(" ".join(words[:5]))
    return list(dict.fromkeys(frags))


FLIPS = flip_phrases()


def compliance(text: str, transcript: str) -> dict:
    low = re.sub(r"[^a-z' ]+", " ", text.lower())
    problems = llm.quality_problems(text, [], transcript)
    fab = FABRICATION.findall(text)
    leaks = LEAKS.findall(text)
    words = len(text.split())
    used = sum(1 for f in FLIPS if f in low)
    score = 10
    score -= 3 * len([p for p in problems if "percent" in p])
    score -= 2 * len([p for p in problems if "forbidden" in p])
    score -= 3 * len(fab)
    score -= 1 * len(leaks)
    score -= 0 if 150 <= words <= 260 else 2
    return {"score": max(0, score), "problems": problems, "fabrications": fab, "leaks": len(leaks), "words": words, "flips_used": used}


async def run_one(p: llm.Provider, transcript: str) -> dict:
    messages = llm.build_messages("rebut", transcript)
    t0 = time.perf_counter(); ttft = None; out = ""; err = None
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=10.0)) as client:
            async for d in llm.stream_for(p, messages, client):
                if ttft is None:
                    ttft = time.perf_counter() - t0
                out += d
    except Exception as e:  # noqa: BLE001
        err = str(e)[:200]
    total = time.perf_counter() - t0
    return {"text": out.strip(), "ttft_ms": int((ttft or 0) * 1000), "total_ms": int(total * 1000), "error": err,
            "tps": round(len(out.split()) * 1.3 / max(total - (ttft or 0), 0.01), 1)}


async def main() -> None:
    cands = json.loads(Path(sys.argv[1]).read_text())["candidates"]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    suites = sorted((HERE / "suites").glob("0*.json"))[:n]
    speeches = [(s.stem, json.loads(s.read_text())["speeches"][0]["text"]) for s in suites]
    rows, blind = [], []
    for c in cands:
        p = llm.Provider(**{k: v for k, v in c.items() if not k.startswith("_")})
        if not p.available:
            print(f"skip {p.name}: no key"); continue
        if p.kind == "ollama":
            print(f"warming {p.model} ...", flush=True)
            w = await llm.warm_ollama(p)
            if not w.get("ok"):
                print(f"skip {p.name}: {w}"); continue
        for sid, tr in speeches:
            r = await run_one(p, tr)
            if r["error"]:
                print(f"[{p.name:14s}] {sid[:12]} ERROR {r['error'][:90]}"); rows.append({"cand": p.name, "suite": sid, **r, "score": 0}); continue
            comp = compliance(r["text"], tr)
            rows.append({"cand": p.name, "model": p.model, "suite": sid, **r, **comp})
            blind.append((p.name, sid, r["text"]))
            print(f"[{p.name:14s}] {sid[:12]} ttft {r['ttft_ms']:5d} ms  total {r['total_ms']:5d} ms  ~{r['tps']:>5} tok/s  words {comp['words']:3d}  compliance {comp['score']:2d}/10  flips {comp['flips_used']:2d}  {('PROBLEMS: ' + '; '.join(comp['problems'] + comp['fabrications'])) if (comp['problems'] or comp['fabrications']) else ''}", flush=True)
        if p.kind == "ollama":
            async with httpx.AsyncClient(timeout=60) as cl:   # unload so the next local model fits
                await cl.post(f"{p.base_url}/api/generate", json={"model": p.model, "keep_alive": 0})
    # summary table
    print("\n=== summary (mean over speeches) ===")
    print(f"{'candidate':16s} {'ttft ms':>8s} {'total ms':>9s} {'tok/s':>6s} {'compl':>6s} {'flips':>6s}")
    for c in dict.fromkeys(r["cand"] for r in rows):
        rs = [r for r in rows if r["cand"] == c and not r.get("error")]
        if not rs:
            print(f"{c:16s} {'-':>8s}"); continue
        m = lambda k: sum(r[k] for r in rs) / len(rs)  # noqa: E731
        print(f"{c:16s} {m('ttft_ms'):8.0f} {m('total_ms'):9.0f} {m('tps'):6.1f} {m('score'):6.1f} {m('flips_used'):6.1f}")
    out = HERE / "out" / f"model-bakeoff-{datetime.now():%Y%m%d-%H%M%S}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(rows, indent=1))
    random.shuffle(blind)
    labels = [chr(65 + i) for i in range(len(blind))]
    (out / "blind.md").write_text("# Blind wit sheet: score 1-5, 'would I read this aloud on stage?'\n\n" + "\n\n".join(f"## {lab}\n\n{t}" for lab, (_, _, t) in zip(labels, blind)))
    (out / "key.md").write_text("| Label | Candidate | Speech |\n|---|---|---|\n" + "\n".join(f"| {lab} | {c} | {s} |" for lab, (c, s, _) in zip(labels, blind)))
    print("wrote", out)


if __name__ == "__main__":
    asyncio.run(main())
