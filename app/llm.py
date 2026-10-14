"""Provider layer + race.

Every cloud provider is an OpenAI-compatible /chat/completions endpoint (Cerebras, Groq, Gemini, OpenAI...).
Ollama uses its native /api/chat. `race()` fires every enabled provider at once, adopts the first one to
produce a token, cancels the rest, and streams the winner. The system prompt is a fixed prefix so local
KV caches stay warm across calls.
"""
from __future__ import annotations

import asyncio
import json
import re
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import AsyncIterator

import httpx
from dotenv import load_dotenv

HERE = Path(__file__).parent
load_dotenv(HERE / ".env")

def _load_system_prompt() -> str:
    base = (HERE / "prompts" / "system.md").read_text().rstrip()
    facts_path = HERE / "prompts" / "facts.md"
    facts = facts_path.read_text().strip() if facts_path.exists() else ""
    counters_path = HERE / "prompts" / "counters.md"
    counters = counters_path.read_text().strip() if counters_path.exists() else ""
    if counters:
        base += "\n\n" + counters   # static: keeps the whole system prompt a cacheable prefix for the local model
    if facts:
        base += "\n\n## VERIFIED FACTS (the only numbers you may cite; name the source; at most two per answer)\n" + facts
    return base + "\n"


SYSTEM_PROMPT = _load_system_prompt()

_STOP = set("the a an and or of to in is are be for that this with as on at by it its we you they our your their not no".split())


def _load_counter_sections() -> list[tuple[str, set[str], str]]:
    """counters.md -> [(heading, keyword set, full section text)]. Sections start with '### '."""
    path = HERE / "prompts" / "counters.md"
    if not path.exists():
        return []
    text = path.read_text()
    parts = re.split(r"\n(?=### )", text)
    out = []
    for part in parts:
        if not part.startswith("### "):
            continue
        heading = part.splitlines()[0]
        # keywords: words in the heading + the quoted 'their phrase' before each ->
        phrases = [heading] + re.findall(r'^- "?([^"\n]+?)"? ->', part, flags=re.M)
        words = set()
        for ph in phrases:
            for w in re.findall(r"[a-z][a-z\-']{3,}", ph.lower()):
                if w not in _STOP:
                    words.add(w)
        out.append((heading, words, part.strip()))
    return out


COUNTER_SECTIONS = _load_counter_sections()


def select_counters(transcript: str, max_sections: int = 2) -> str:
    """Pick the playbook sections whose vocabulary overlaps most with what the opposition actually said.
    Keeps the prompt short and the model focused; falls back to the two most general sections."""
    if not COUNTER_SECTIONS:
        return ""
    words = set(re.findall(r"[a-z][a-z\-']{3,}", (transcript or "").lower()))
    scored = sorted(COUNTER_SECTIONS, key=lambda sec: -len(sec[1] & words))
    chosen = [sec for sec in scored[:max_sections] if len(sec[1] & words) >= 3] or scored[:1]
    return "## Opposition playbooks that match what they just said (use these flips)\n\n" + "\n\n".join(sec[2] for sec in chosen)

MODE_INSTRUCTIONS = {
    "rebut": (
        "The opposition just finished speaking. Above is the live transcript (may be noisy). "
        "Write Andrew's SHORT rebuttal (about 70 seconds, 150-200 words) in the strict format. End on the zinger."
    ),
    "speech2": (
        "The opposition's first speaker just sat down. Above is their live transcript (may be noisy). "
        "Write Andrew's ENTIRE Second Proposition speech, to be read aloud from the screen: 5 minutes. Target 650-720 words; under 600 is too short, do not stop early. "
        "Structure, in this order, no headings: "
        "(1) BRIDGE, ~70 words: pick up one specific thing they said, in their words, and set the tone; note that everything they cited was about the past. "
        "(2) REBUTTALS, ~260 words: their two or three strongest arguments, each named in their words and turned, using the counters bank and at most two verified facts. "
        "(3) OUR CASE, ~260 words: the PREPARED MATERIAL below, rewritten so each point answers something they actually argued tonight. Keep the ideas, not the wording. "
        "(4) CLOSE, ~80 words: land the definition (the buyer decides without needing us in the room) and end on the zinger. "
        "Short paragraphs (2-4 sentences), a blank line between them. Spoken English, first person, address Speaker A and Speaker B by name where you quote them."
    ),
    "steelman": (
        "Above is the opposition's speech. Pick their single STRONGEST point, state it fairly in one sentence starting with 'Their best point:', "
        "then flip it into evidence FOR the motion, then the zinger. 120-180 words."
    ),
    "notes": (
        "The opposition is STILL speaking; above is the transcript so far. Draft 3-4 provisional rebuttal sentences "
        "Andrew can glance at. Prioritise their most recent points. Under 90 words."
    ),
    "summary": (
        "This is the final summary of the debate. Above: BOTH opposition speeches and what we already said (do not repeat our openings or closings). "
        "Write Andrew's ENTIRE Proposition Summary, read aloud from the screen: 3 minutes. Target 400-440 words; under 360 is too short. "
        "Structure, in this order, no headings: "
        "(1) FRAME, ~60 words: what their whole case came down to, in two or three of their own recurring words. "
        "(2) CONCESSIONS, ~90 words: list what they conceded in their own words ('leaner', 'still', 'human in the loop', 'transformation', 'more productive') and say what each admits. "
        "(3) THEIR NEWEST POINTS, ~110 words: answer the one or two things their second speaker added, using the counters bank; no new statistics unless already used tonight. "
        "(4) DEFINITION AND CLOSE, ~90 words: restate the definition, then the closing line. Use the PREPARED MATERIAL below for the shape of the close. "
        "Short paragraphs, blank line between them. Spoken English, first person."
    ),
    "ask": (
        "Andrew asks you a direct question or hands you an objection from the room. Answer in 60-90 words of spoken prose, cocky, last sentence the zinger."
    ),
}

MAX_TOKENS_BY_MODE = {"rebut": 560, "steelman": 560, "notes": 320, "ask": 400, "speech2": 1400, "summary": 900}
MAX_TOKENS = 560  # default; see MAX_TOKENS_BY_MODE


@dataclass
class Provider:
    name: str
    kind: str  # "openai" | "ollama"
    base_url: str
    model: str
    key_env: str | None = None
    extra: dict = field(default_factory=dict)
    enabled: bool = True
    fallback_model: str | None = None
    priority: int = 0   # >0 marks the preferred racer: others wait this long for it before being adopted

    @property
    def api_key(self) -> str | None:
        return os.environ.get(self.key_env) if self.key_env else None

    @property
    def available(self) -> bool:
        if not self.enabled:
            return False
        if self.kind in ("openai", "anthropic"):
            return bool(self.api_key)
        return True


def load_providers() -> list[Provider]:
    cfg = json.loads((HERE / "providers.json").read_text())
    return [Provider(**{k: v for k, v in p.items() if not k.startswith("_")}) for p in cfg["providers"]]


def grace_ms() -> int:
    try:
        return int(json.loads((HERE / "providers.json").read_text()).get("grace_ms", 2500))
    except Exception:  # noqa: BLE001
        return 2500


FORBIDDEN = ["cathedral", "fortress", "pillar", "house of", "built a", "built an", "rests on", "andrew",
             "twenty minutes", "half-hour", "half an hour", "entire evening", "all night", "whole round"]
SCRUB = {"cathedral": "case", "fortress": "case", "pillars": "points", "pillar": "point", "house of": "case of",
         "built a magnificent ": "made a ", "built an entire ": "made an ", "built a ": "made a ", "built an ": "made an ",
         "rests on": "leans on", "twenty minutes": "five minutes", "half-hour": "five minutes", "half an hour": "five minutes",
         "entire evening": "speech", "all night": "in that speech", "whole round": "speech"}

_NUM_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:%|percent|per cent)", re.I)
_WORDNUM = {"ten": 10, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}


def _percentages(text: str) -> set[str]:
    out = set(m.group(1).replace(",", ".") for m in _NUM_RE.finditer(text))
    for m in re.finditer(r"\b(ten|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)(?:[- ](one|two|three|four|five|six|seven|eight|nine))?\s*(?:%|percent|per cent)", text, re.I):
        n = _WORDNUM[m.group(1).lower()] + {"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,"nine":9}.get((m.group(2) or "").lower(), 0)
        out.add(str(n))
    return out


ALLOWED_FACT_PERCENTS = _percentages((HERE / "prompts" / "facts.md").read_text()) if (HERE / "prompts" / "facts.md").exists() else set()
FACTS_TEXT = (HERE / "prompts" / "facts.md").read_text() if (HERE / "prompts" / "facts.md").exists() else ""


def scrub(text: str, prior: list[str] | None = None) -> str:
    """Last-resort mechanical fixes: replace forbidden tics, strip a stray leading quote mark, and if the closing
    paragraph repeats an earlier passage's closing, drop it so the passage ends on the paragraph before."""
    out = text
    for k, v in SCRUB.items():
        out = re.sub(re.escape(k), v, out, flags=re.I)
    out = re.sub(r'^[\s"“]+', "", out)
    paras = [x.strip() for x in out.strip().split("\n\n") if x.strip()]
    if prior and len(paras) > 2:
        last = _shingles(paras[-1], 5)
        for old in prior:
            old_paras = [x.strip() for x in old.strip().split("\n\n") if x.strip()]
            if old_paras and last & _shingles(old_paras[-1], 5):
                paras = paras[:-1]
                break
    return "\n\n".join(paras)


def _shingles(text: str, n: int = 6) -> set[str]:
    w = re.findall(r"[a-z']+", text.lower())
    return set(" ".join(w[i:i + n]) for i in range(max(0, len(w) - n + 1)))


def quality_problems(text: str, prior: list[str], source_text: str = "") -> list[str]:
    """Return human-readable problems: forbidden words, percentages not in the facts bank or the opposition's
    own words, or wording copied from earlier passages."""
    problems = []
    low = text.lower()
    for f in FORBIDDEN:
        if f in low:
            problems.append(f'used the forbidden word "{f}"')
    allowed = ALLOWED_FACT_PERCENTS | _percentages(source_text)
    bad = sorted(p for p in _percentages(text) if p not in allowed and p.rstrip("0").rstrip(".") not in allowed)
    if bad:
        problems.append("used percentages that are not in VERIFIED FACTS or in the opposition's own words: " + ", ".join(b + "%" for b in bad) + " (drop them or use the exact verified figure)")
    paras = [x.strip() for x in text.strip().split("\n\n") if x.strip()]
    if paras and prior:
        mine = _shingles(text)
        for old in prior:
            shared = mine & _shingles(old)
            if len(shared) >= 1:
                problems.append("repeated wording from an earlier passage: \"" + next(iter(shared)) + "...\"")
                break
    return problems


PREPARED = {
    "speech2": (HERE.parent / "content" / "03-second-proposition.md"),
    "summary": (HERE.parent / "content" / "04-rebuttal-summary.md"),
}


def prepared_material(mode: str) -> str:
    """The spoken lines of our prepared script for this slot (stage directions and headings stripped). The model
    keeps the ideas and rewrites them to answer what the opposition actually said."""
    path = PREPARED.get(mode)
    if not path or not path.exists():
        return ""
    keep = []
    for line in path.read_text().splitlines():
        t = line.strip()
        if not t or t.startswith(("#", "~", "[[", "---")) or (t.startswith("**[") and t.endswith("]**")):
            continue
        keep.append(t.replace("**", ""))
    return "\n".join(keep)


def build_messages(mode: str, transcript: str, question: str | None = None, already_said: list[str] | None = None,
                   history: list[dict] | None = None, extra_instruction: str | None = None) -> list[dict]:
    instr = MODE_INSTRUCTIONS[mode]
    prep = prepared_material(mode)
    if prep:
        instr = instr + "\n\nPREPARED MATERIAL (our ideas for this slot; keep the ideas, rewrite them to answer tonight's speech, drop what no longer fits):\n" + prep
    if extra_instruction:
        instr = extra_instruction + "\n\n" + instr
    hist = ""
    if history:
        parts = []
        for h in history:
            parts.append(f"[{h['label']}]\n{h['text'].strip()[:3500]}")
        hist = ("EARLIER IN THE DEBATE (oldest first). Entries marked OPPOSITION SPEECH are what Speaker A and Speaker B said; rebut those. "
                "Entries marked WE ALREADY SAID are our own earlier openings and closings: never copy them, never repeat the scene, never address them as if an opponent said them. "
                "You are Andrew's voice; the word 'Andrew' must never appear in your output.\n"
                + "\n\n".join(parts) + "\n\n")
    if mode == "ask":
        user = f"Transcript so far (context, may be empty):\n{transcript.strip() or '(none)'}\n\nQUESTION FROM THE ROOM: {question or ''}\n\n{instr}"
    elif mode == "summary":
        user = f"{hist}LATEST OPPOSITION SPEECH (their second speaker / closing):\n{transcript.strip() or '(nothing captured)'}\n\n{instr}"
    else:
        user = f"{hist}OPPOSITION TRANSCRIPT (just now):\n{transcript.strip() or '(nothing captured)'}\n\n{instr}"
    if already_said:
        zingers = []
        for a in already_said[-3:]:
            paras = [x.strip() for x in a.strip().split("\n\n") if x.strip()]
            if paras:
                zingers.append(paras[-1][:160])
        if zingers:
            user += "\n\nCLOSING LINES ALREADY USED TONIGHT (write a different one): " + " | ".join(zingers)
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]


async def stream_openai(p: Provider, messages: list[dict], client: httpx.AsyncClient, max_tokens: int = MAX_TOKENS) -> AsyncIterator[str]:
    body = {"model": p.model, "messages": messages, "stream": True, "max_tokens": max_tokens, "temperature": 0.9}
    body.update(p.extra or {})
    headers = {"Authorization": f"Bearer {p.api_key}", "Content-Type": "application/json"}
    async with client.stream("POST", f"{p.base_url}/chat/completions", json=body, headers=headers) as r:
        if r.status_code >= 400:
            text = (await r.aread()).decode(errors="replace")[:300]
            raise RuntimeError(f"{p.name} HTTP {r.status_code}: {text}")
        async for line in r.aiter_lines():
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                obj = json.loads(data)
            except json.JSONDecodeError:
                continue
            for ch in obj.get("choices", []):
                delta = ch.get("delta", {}).get("content")
                if delta:
                    yield delta


async def stream_ollama(p: Provider, messages: list[dict], client: httpx.AsyncClient, max_tokens: int = MAX_TOKENS) -> AsyncIterator[str]:
    body = {
        "model": p.model,
        "messages": messages,
        "stream": True,
        "think": False,
        "keep_alive": -1,
        "options": {"num_ctx": 16384, "temperature": 0.9, "num_predict": max_tokens},
    }
    async with client.stream("POST", f"{p.base_url}/api/chat", json=body) as r:
        if r.status_code >= 400:
            text = (await r.aread()).decode(errors="replace")[:300]
            raise RuntimeError(f"{p.name} HTTP {r.status_code}: {text}")
        async for line in r.aiter_lines():
            if not line.strip():
                continue
            obj = json.loads(line)
            delta = obj.get("message", {}).get("content")
            if delta:
                yield delta
            if obj.get("done"):
                break


async def stream_anthropic(p: Provider, messages: list[dict], client: httpx.AsyncClient, max_tokens: int = MAX_TOKENS) -> AsyncIterator[str]:
    """Claude via the official SDK. System prompt goes in `system`; thinking is switched off on models that
    accept it (Sonnet 5 / Opus) and simply omitted on Haiku 4.5, so the first token is not delayed by reasoning."""
    from anthropic import AsyncAnthropic  # imported lazily so the app runs without the package if unused

    aclient = AsyncAnthropic(api_key=p.api_key)
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    convo = [m for m in messages if m["role"] != "system"]
    kwargs: dict = {"model": p.model, "max_tokens": max_tokens, "system": system, "messages": convo}
    if not p.model.startswith("claude-haiku"):
        kwargs["thinking"] = {"type": "disabled"}
    kwargs.update(p.extra or {})
    async with aclient.messages.stream(**kwargs) as stream:
        async for text in stream.text_stream:
            if text:
                yield text


def stream_for(p: Provider, messages: list[dict], client: httpx.AsyncClient, max_tokens: int = MAX_TOKENS) -> AsyncIterator[str]:
    if p.kind == "ollama":
        return stream_ollama(p, messages, client, max_tokens)
    if p.kind == "anthropic":
        return stream_anthropic(p, messages, client, max_tokens)
    return stream_openai(p, messages, client, max_tokens)


async def race(mode: str, transcript: str, question: str | None = None,
               providers: list[Provider] | None = None, only: str | None = None,
               already_said: list[str] | None = None, history: list[dict] | None = None,
               extra_instruction: str | None = None) -> AsyncIterator[dict]:
    """Yield events: {"type":"start"}, {"type":"winner","provider","ttft_ms"}, {"type":"delta","text"},
    {"type":"error","provider","error"}, {"type":"done","provider","total_ms","chars"}."""
    providers = [p for p in (providers or load_providers()) if p.available and (only is None or p.name == only)]
    messages = build_messages(mode, transcript, question, already_said, history, extra_instruction)
    t0 = time.perf_counter()
    yield {"type": "start", "racers": [p.name for p in providers]}
    if not providers:
        yield {"type": "error", "provider": "-", "error": "no providers available (no API keys and Ollama disabled?)"}
        return

    out_q: asyncio.Queue = asyncio.Queue()

    async def run(p: Provider):
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=5.0)) as client:
                first = True
                async for delta in stream_for(p, messages, client, MAX_TOKENS_BY_MODE.get(mode, MAX_TOKENS)):
                    if first:
                        await out_q.put(("first", p.name, None))
                        first = False
                    await out_q.put(("delta", p.name, delta))
                await out_q.put(("done", p.name, None))
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            await out_q.put(("error", p.name, str(e)))

    tasks = {p.name: asyncio.create_task(run(p)) for p in providers}
    prio = {p.name: p.priority for p in providers}
    top = max(prio.values()) if prio else 0
    grace = (3000 if mode in ("speech2", "summary") else grace_ms()) / 1000.0   # long passages: wait longer for the better racer
    winner: str | None = None
    started: dict[str, float] = {}          # provider -> time of first token
    buffers: dict[str, list[str]] = {n: [] for n in tasks}
    failed: set[str] = set()
    deadline: float | None = None            # set when the first racer starts
    chars = 0

    def pick() -> str:
        live = [n for n in started if n not in failed]
        return max(live, key=lambda n: (prio[n], -started[n]))

    try:
        while True:
            timeout = None
            if winner is None and deadline is not None:
                timeout = max(0.0, deadline - time.perf_counter())
            try:
                kind, name, payload = await asyncio.wait_for(out_q.get(), timeout) if timeout is not None else await out_q.get()
            except asyncio.TimeoutError:
                kind, name, payload = "deadline", None, None
            if winner is None:
                if kind == "first":
                    started[name] = time.perf_counter()
                    if deadline is None:
                        deadline = time.perf_counter() + grace
                    # decide now if the best possible racer has started, or nobody better is still running
                    better_pending = [n for n in tasks if prio[n] > prio[pick()] and n not in started and n not in failed]
                    if prio[name] == top or not better_pending:
                        winner = pick()
                elif kind == "delta":
                    buffers[name].append(payload)
                elif kind == "error":
                    failed.add(name)
                    yield {"type": "error", "provider": name, "error": payload}
                    if failed >= set(tasks):
                        yield {"type": "done", "provider": None, "total_ms": int((time.perf_counter() - t0) * 1000), "chars": 0}
                        return
                    if started and not [n for n in tasks if n not in started and n not in failed]:
                        winner = pick()
                elif kind == "deadline":
                    if started:
                        winner = pick()
                    else:
                        deadline = None
                elif kind == "done":
                    buffers[name].append("")
                if winner is not None:
                    yield {"type": "winner", "provider": winner, "ttft_ms": int((started[winner] - t0) * 1000)}
                    for other, t in tasks.items():
                        if other != winner:
                            t.cancel()
                    for text in buffers[winner]:
                        if text:
                            chars += len(text)
                            yield {"type": "delta", "text": text}
                    if tasks[winner].done():
                        yield {"type": "done", "provider": winner, "total_ms": int((time.perf_counter() - t0) * 1000), "chars": chars}
                        return
                continue
            # winner chosen: stream it
            if name != winner:
                continue
            if kind == "delta":
                chars += len(payload)
                yield {"type": "delta", "text": payload}
            elif kind == "done":
                yield {"type": "done", "provider": name, "total_ms": int((time.perf_counter() - t0) * 1000), "chars": chars}
                return
            elif kind == "error":
                yield {"type": "error", "provider": name, "error": payload}
                yield {"type": "done", "provider": name, "total_ms": int((time.perf_counter() - t0) * 1000), "chars": chars}
                return
    finally:
        for t in tasks.values():
            t.cancel()


async def warm_ollama(p: Provider) -> dict:
    """Load and pin the model, then run three realistic warm-up prompts (short ask, medium rebut, long rebut).
    The MLX runtime pays a one-off ~2-3 s cost the first time it sees a new prompt shape; doing this at
    startup means the first real request on stage is fast. Also picks the fallback model if the primary
    isn't pulled."""
    async with httpx.AsyncClient(timeout=180) as client:
        try:
            tags = (await client.get(f"{p.base_url}/api/tags")).json()
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": f"ollama not reachable: {e}"}
        names = {m["name"] for m in tags.get("models", [])}
        if p.model not in names and p.fallback_model in names:
            p.model = p.fallback_model
        if p.model not in names:
            return {"ok": False, "error": f"model {p.model} not pulled", "have": sorted(names)}

        mock_path = HERE.parent / "content" / "99-mock-opposition-speech.txt"
        mock = mock_path.read_text() if mock_path.exists() else "Buyers want a human relationship. " * 60
        medium = " ".join(mock.split()[:220])
        # Order matters: the runtime is fastest when a request shares its prefix with the previous one,
        # and the first live request on stage is the opening-bit Ask, so an Ask runs last.
        warmups = [
            ("rebut-long", build_messages("rebut", mock)),
            ("rebut-medium", build_messages("rebut", medium)),
            ("ask-short", build_messages("ask", "", "Buyers want a human relationship.")),
        ]
        timings = {}
        t_load = time.perf_counter()
        for label, messages in warmups:
            t0 = time.perf_counter()
            r = await client.post(f"{p.base_url}/api/chat", json={
                "model": p.model, "messages": messages, "stream": False, "think": False, "keep_alive": -1,
                "options": {"num_predict": 48, "num_ctx": 16384}})
            if r.status_code != 200:
                return {"ok": False, "model": p.model, "error": f"HTTP {r.status_code}: {r.text[:200]}"}
            timings[label] = int((time.perf_counter() - t0) * 1000)
        return {"ok": True, "model": p.model, "load_ms": int((time.perf_counter() - t_load) * 1000), "warmup_ms": timings}
