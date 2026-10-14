"""Adversarial runner: drive the live AMIT 2.0 server through a full debate with a suite of opposition speeches.

    uv run python adversarial/run.py adversarial/suites/01-real-opposition-playbook.json [only-provider]

Uses the real flow (slots, memory, summary mode) so the output is what Andrew would see on the night.
Writes adversarial/out/<suite>-<timestamp>.md with each passage, winner, latency, word count, and numbers used.
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

import os
BASE = os.environ.get("AMIT_BASE", "http://127.0.0.1:8765")
HERE = Path(__file__).parent


def gen(mode: str, only: str | None) -> dict:
    """Trigger a generation and collect it from the SSE stream."""
    out, meta = "", {}
    with httpx.stream("GET", f"{BASE}/events", timeout=90) as es:
        httpx.post(f"{BASE}/generate", json={"mode": mode, "stop_stt": True, "only": only}, timeout=10)
        started = time.time()
        for line in es.iter_lines():
            if not line.startswith("data:"):
                if time.time() - started > 60:
                    break
                continue
            ev = json.loads(line[5:])
            if ev["type"] == "gen_winner":
                meta.update(provider=ev["provider"], ttft_ms=ev["ttft_ms"])
            elif ev["type"] == "gen_delta":
                out += ev["text"]
            elif ev["type"] == "gen_error":
                meta.setdefault("errors", []).append(f"{ev['provider']}: {ev['error'][:120]}")
            elif ev["type"] == "gen_done":
                meta["total_ms"] = ev["total_ms"]
                break
    meta["text"] = out.strip()
    meta["words"] = len(out.split())
    meta["numbers"] = re.findall(r"\d[\d,.]*\s?%?", out)
    return meta


def main() -> None:
    suite = json.loads(Path(sys.argv[1]).read_text())
    only = next((a for a in sys.argv[2:] if not a.startswith("--")), None)
    httpx.post(f"{BASE}/history/clear", timeout=10)
    report = [f"# Adversarial run: {suite['name']}", f"Provider filter: {only or 'race'}  ·  {datetime.now():%Y-%m-%d %H:%M}", ""]
    for sp in suite["speeches"]:
        idx = sp["slot"]                      # 0-based slot index of the opposition slot
        httpx.post(f"{BASE}/slot", json={"index": idx, "source": "mic"}, timeout=10)
        httpx.post(f"{BASE}/stt/stop", timeout=10)                       # no live mic during a suite run
        httpx.post(f"{BASE}/transcript", json={"text": sp["text"]}, timeout=10)
        mode = "summary" if idx in (3, 5) else ("speech2" if "--full" in sys.argv else "rebut")
        gen("notes", "local")                                            # prime the local cache like the live notes loop does
        r = gen(mode, only)
        report += [f"## After {sp['label']} -> our {mode}",
                   f"winner: {r.get('provider')} · first word {r.get('ttft_ms')} ms · total {r.get('total_ms')} ms · {r['words']} words · numbers: {r['numbers']}",
                   *(f"errors: {e}" for e in r.get("errors", [])), "", r["text"], ""]
        print(f"[{sp['label']}] {mode}: {r.get('provider')} ttft {r.get('ttft_ms')} total {r.get('total_ms')} words {r['words']}")
    out = HERE / "out" / f"{suite['name']}-{datetime.now():%Y%m%d-%H%M%S}{'-' + only if only else ''}.md"
    out.write_text("\n".join(report))
    print("wrote", out)


if __name__ == "__main__":
    main()
