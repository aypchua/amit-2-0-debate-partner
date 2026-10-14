"""AMIT 2.0 server: live transcript + LLM race + stage UI.

Run:  uv run uvicorn server:app --port 8765
Open: http://127.0.0.1:8765
"""
from __future__ import annotations

import asyncio
import json
import re
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

import llm
from stt import YapSTT

HERE = Path(__file__).parent
app = FastAPI(title="AMIT 2.0")

# ---------- shared state ----------
class State:
    transcript: list[str] = []
    providers = llm.load_providers()
    clients: set[asyncio.Queue] = set()
    gen_task: asyncio.Task | None = None
    gen_seq = 0
    notes_task: asyncio.Task | None = None
    notes_every_s = 25.0
    notes_last_len = 0
    notes_last_at = 0.0
    warm: dict = {}
    log: list[str] = []
    auto_notes = True
    said: list[str] = []   # final passages generated tonight (not notes), for anti-repetition
    history: list[dict] = []   # debate memory: archived opposition transcripts and our passages, with slot labels
    slot: int = -1

S = State()


async def broadcast(ev: dict) -> None:
    ev.setdefault("t", time.time())
    dead = []
    for q in S.clients:
        try:
            q.put_nowait(ev)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        S.clients.discard(q)


async def status_line(msg: str) -> None:
    S.log.append(msg)
    S.log = S.log[-50:]
    await broadcast({"type": "status", "msg": msg})


NUM_RE = re.compile(r"(\d{1,3}(?:\.\d+)?)\s?(?:%|percent|per cent)|\b(one in (?:two|three|four|five|ten)|two[- ]thirds|three[- ]quarters|half of)\b", re.I)
WORD_NUMS = {"one in four": "25", "one in three": "33", "one in five": "20", "one in ten": "10", "one in two": "50",
             "two-thirds": "67", "two thirds": "67", "three-quarters": "75", "three quarters": "75", "half of": "50"}


def their_numbers() -> list[dict]:
    """Every percentage the opposition has said so far, with whether it matches our verified facts bank."""
    text = transcript_text()
    out, seen = [], set()
    for m in NUM_RE.finditer(text):
        raw = m.group(1) or WORD_NUMS.get(m.group(2).lower().replace("  ", " "), "")
        if not raw:
            continue
        key = raw.rstrip("0").rstrip(".") if "." in raw else raw
        if key in seen:
            continue
        seen.add(key)
        start = max(0, m.start() - 60)
        ctx = text[start:m.end() + 40].replace("\n", " ").strip()
        phrase = (m.group(2) or "").lower()
        verified = key in llm.ALLOWED_FACT_PERCENTS or (bool(phrase) and (phrase in llm.FACTS_TEXT.lower() or phrase.replace("one in four", "1 in 4") in llm.FACTS_TEXT.lower()))
        src = ""
        if verified:
            for line in llm.FACTS_TEXT.splitlines():
                if re.search(rf"\b{re.escape(key)}\s?%", line):
                    src = re.sub(r"\s*\(.*?\)\s*", " ", line.split(":")[0].lstrip("- ")).strip()[:40]
                    break
        out.append({"n": key, "verified": verified, "source": src, "ctx": ctx})
    return out


async def on_phrase(text: str) -> None:
    S.transcript.append(text)
    await broadcast({"type": "phrase", "text": text, "n": len(S.transcript)})
    if NUM_RE.search(text):
        await broadcast({"type": "numbers", "items": their_numbers()})

stt = YapSTT(on_phrase, status_line)


def transcript_text() -> str:
    return " ".join(S.transcript)


# ---------- generation ----------
LONG_MODES = {"speech2", "summary"}


def guard_in_place(text: str, source: str, prior: list[str]) -> tuple[str, list[str]]:
    """For long passages Andrew is already reading: never regenerate. Scrub tic words, drop any sentence carrying a
    percentage that is in neither the facts bank nor the opposition's own words, and drop a closing paragraph that
    repeats an earlier passage. Returns (text, notes)."""
    notes: list[str] = []
    out = llm.scrub(text, prior)
    if out != text:
        notes.append("tic words scrubbed")
    allowed = llm.ALLOWED_FACT_PERCENTS | llm._percentages(source)
    kept, dropped = [], 0
    for para in [x for x in re.split(r"\n\s*\n", out) if x.strip()]:
        sents = re.split(r"(?<=[.!?])\s+", para.strip())
        good = [x for x in sents if not (llm._percentages(x) - allowed)]
        dropped += len(sents) - len(good)
        if good:
            kept.append(" ".join(good))
    if dropped:
        notes.append(f"{dropped} sentence{'s' if dropped > 1 else ''} removed: unverified number")
    if len(kept) > 1 and prior and any(len(llm._shingles(kept[-1]) & llm._shingles(pr)) >= 1 for pr in prior):
        kept = kept[:-1]
        notes.append("repeated closing dropped")
    return "\n\n".join(kept), notes


async def generate(mode: str, question: str | None = None, only: str | None = None, transcript: str | None = None) -> None:
    S.gen_seq += 1
    seq = S.gen_seq
    text = transcript if transcript is not None else transcript_text()
    await broadcast({"type": "gen_start", "mode": mode, "seq": seq})
    out = ""
    hist = S.history   # every mode, including notes: the primed prefix must match what STOP will send
    extra = None
    try:
        for attempt in range(3):
            out = ""
            async for ev in llm.race(mode, text, question, providers=S.providers, only=only,
                                     already_said=S.said if mode != "notes" else None, history=hist,
                                     extra_instruction=extra):
                if ev["type"] == "delta":
                    out += ev["text"]
                ev.update({"mode": mode, "seq": seq, "attempt": attempt})
                ev["type"] = "gen_" + ev["type"]
                await broadcast(ev)
            source = text + " " + " ".join(h["text"] for h in S.history if h["label"].startswith("OPPOSITION"))
            if mode in LONG_MODES:                       # long passage: fix in place, never regenerate
                fixed, notes = guard_in_place(out, source, S.said)
                if fixed != out:
                    out = fixed
                    await broadcast({"type": "gen_replace", "mode": mode, "seq": seq, "text": out, "note": "; ".join(notes)})
                    await status_line("guard: " + "; ".join(notes))
                break
            problems = llm.quality_problems(out, S.said, source) if mode != "notes" else []
            if not problems or attempt == 2:
                if problems:   # out of attempts: scrub tics mechanically and tell Andrew what to watch
                    scrubbed = llm.scrub(out, S.said)
                    if scrubbed != out:
                        out = scrubbed
                        await broadcast({"type": "gen_replace", "mode": mode, "seq": seq, "text": out})
                    await status_line("CHECK: " + "; ".join(problems))
                break
            extra = ("REWRITE. Your previous draft " + "; ".join(problems) +
                     ". Produce a completely different opening and closing, keep the arguments, obey the forbidden-word list.")
            await broadcast({"type": "gen_rewrite", "mode": mode, "seq": seq, "problems": problems})
            await status_line("rewrite: " + "; ".join(problems))
        if mode != "notes" and out.strip():
            S.said.append(out)
            after = SLOTS[S.slot]["title"] if 0 <= S.slot < len(SLOTS) else "now"
            S.history.append({"label": f"WE ALREADY SPOKE (our {mode} after {after})",
                              "text": "(our passage; its closing line is listed separately, do not repeat it)"})
    except asyncio.CancelledError:
        await broadcast({"type": "gen_cancelled", "mode": mode, "seq": seq})
        raise


def start_generation(mode: str, question: str | None = None, only: str | None = None, transcript: str | None = None) -> int:
    if S.gen_task and not S.gen_task.done():
        S.gen_task.cancel()
    S.gen_task = asyncio.create_task(generate(mode, question, only, transcript))
    return S.gen_seq + 1


async def notes_loop() -> None:
    """While STT runs, refresh provisional notes when the transcript has grown and enough time has passed."""
    while True:
        await asyncio.sleep(1.0)
        if not (S.auto_notes and stt.running):
            continue
        grown = len(S.transcript) - S.notes_last_len >= 3
        due = time.time() - S.notes_last_at >= S.notes_every_s
        busy = S.gen_task and not S.gen_task.done()
        if grown and due and not busy:
            S.notes_last_len = len(S.transcript)
            S.notes_last_at = time.time()
            start_generation("notes", only="local")   # notes stay local: keeps the KV cache warm and spares cloud rate limits


@app.on_event("startup")
async def _startup() -> None:
    S.notes_task = asyncio.create_task(notes_loop())
    loc = next((p for p in S.providers if p.kind == "ollama"), None)
    if loc:
        asyncio.create_task(_warm(loc))


async def _warm(p: llm.Provider) -> None:
    await status_line(f"warming {p.model}...")
    S.warm = await llm.warm_ollama(p)
    await status_line(f"warm: {S.warm}")
    await broadcast({"type": "warm", **S.warm})


# ---------- API ----------
class GenReq(BaseModel):
    mode: str = "rebut"
    question: str | None = None
    only: str | None = None
    stop_stt: bool = False
    transcript: str | None = None  # UI-edited override


class TextReq(BaseModel):
    text: str


class SttReq(BaseModel):
    source: str = "mic"   # "mic" | "system"
    locale: str | None = None


@app.get("/")
async def index():
    return FileResponse(HERE / "static" / "index.html")


@app.get("/status")
async def status():
    return {
        "yap": YapSTT.available(),
        "stt_running": stt.running,
        "stt_source": stt.source,
        "silence_s": stt.silence_seconds(),
        "providers": [{"name": p.name, "model": p.model, "available": p.available, "kind": p.kind} for p in S.providers],
        "warm": S.warm,
        "transcript_phrases": len(S.transcript),
        "auto_notes": S.auto_notes,
        "log": S.log[-40:],
    }


@app.get("/events")
async def events():
    q: asyncio.Queue = asyncio.Queue(maxsize=1000)
    S.clients.add(q)
    await q.put({"type": "hello", "transcript": S.transcript, "warm": S.warm, "stt_running": stt.running})

    async def gen():
        try:
            while True:
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
                    continue
                yield f"data: {json.dumps(ev)}\n\n"
        finally:
            S.clients.discard(q)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/stt/start")
async def stt_start(req: SttReq):
    await stt.start(req.source, req.locale)
    S.notes_last_at = time.time()
    S.notes_last_len = len(S.transcript)
    return {"running": stt.running}


@app.post("/stt/stop")
async def stt_stop():
    await stt.stop()
    return {"running": stt.running}


@app.post("/generate")
async def generate_ep(req: GenReq):
    if req.stop_stt:
        await stt.stop()
    seq = start_generation(req.mode, req.question, req.only, req.transcript)
    return {"seq": seq}


@app.post("/cancel")
async def cancel():
    if S.gen_task and not S.gen_task.done():
        S.gen_task.cancel()
    return {"ok": True}


@app.get("/numbers")
async def numbers():
    return {"items": their_numbers()}


@app.get("/transcript")
async def get_transcript():
    return {"phrases": S.transcript, "text": transcript_text()}


@app.post("/transcript")
async def set_transcript(req: TextReq):
    S.transcript = [ln for ln in req.text.replace("\r", "").split("\n") if ln.strip()] if req.text.strip() else []
    await broadcast({"type": "transcript_replaced", "transcript": S.transcript})
    await broadcast({"type": "numbers", "items": their_numbers()})
    return {"n": len(S.transcript)}


def archive_current(label: str | None = None) -> None:
    """Move the live transcript into debate memory (used by slot changes and by Clear outside Show mode)."""
    if not S.transcript:
        return
    n = 1 + sum(1 for h in S.history if h["label"].startswith("OPPOSITION SPEECH"))
    label = label or f"OPPOSITION SPEECH {n}"
    S.history = [h for h in S.history if h["label"] != label]
    S.history.append({"label": label, "text": transcript_text()})


@app.post("/transcript/discard")
async def discard_transcript():
    """Empty the live transcript WITHOUT archiving (mic checks, MC chatter, accidental capture of our own speech)."""
    await stt.stop()
    S.transcript = []
    S.notes_last_len = 0
    await broadcast({"type": "transcript_replaced", "transcript": []})
    await broadcast({"type": "numbers", "items": []})
    return {"ok": True}


@app.post("/transcript/clear")
async def clear_transcript():
    archive_current()          # never lose a speech: memory keeps it for the summary
    S.transcript = []
    S.notes_last_len = 0
    S.said = []
    await broadcast({"type": "transcript_replaced", "transcript": []})
    return {"ok": True}


@app.post("/auto_notes")
async def auto_notes(req: dict):
    S.auto_notes = bool(req.get("on", True))
    return {"auto_notes": S.auto_notes}


@app.post("/warm")
async def warm():
    loc = next((p for p in S.providers if p.kind == "ollama"), None)
    if loc:
        await _warm(loc)
    return S.warm


SLOTS = [
    {"id": 1, "title": "1st Proposition", "who": "Andrew", "kind": "script", "limit": 300, "file": "02-first-proposition.md"},
    {"id": 2, "title": "1st Opposition", "who": "Speaker A / Speaker B", "kind": "opp", "limit": 300},
    {"id": 3, "title": "2nd Proposition", "who": "Andrew", "kind": "script", "limit": 300, "file": "03-second-proposition.md"},
    {"id": 4, "title": "2nd Opposition", "who": "the other one", "kind": "opp", "limit": 300},
    {"id": 5, "title": "Prop Summary", "who": "Andrew", "kind": "script", "limit": 180, "file": "04-rebuttal-summary.md"},
    {"id": 6, "title": "Opp Summary", "who": "them", "kind": "opp", "limit": 180},
]


class SlotReq(BaseModel):
    index: int
    source: str = "mic"


@app.post("/slot")
async def set_slot(req: SlotReq):
    """Move to a run-of-show slot. Leaving an opposition slot archives its transcript into debate memory."""
    prev = SLOTS[S.slot] if 0 <= S.slot < len(SLOTS) else None
    if prev and prev["kind"] == "opp" and S.transcript:
        label = f"OPPOSITION SPEECH: {prev['title']} ({prev['who']})"
        S.history = [h for h in S.history if h["label"] != label]   # re-entering a slot replaces its archive, no duplicates
        S.history.append({"label": label, "text": transcript_text()})
    S.slot = max(-1, min(req.index, len(SLOTS) - 1))
    cur = SLOTS[S.slot] if S.slot >= 0 else None
    if cur and cur["kind"] == "opp":
        S.transcript = []
        S.notes_last_len = 0
        S.notes_last_at = time.time()
        await broadcast({"type": "transcript_replaced", "transcript": []})
        await stt.start(req.source)
    else:
        await stt.stop()
    await broadcast({"type": "slot", "index": S.slot})
    return {"slot": S.slot, "history": [h["label"] for h in S.history], "stt_running": stt.running}


@app.get("/history")
async def history():
    return {"history": S.history, "slot": S.slot}


@app.post("/history/clear")
async def clear_history():
    """New debate: wipe memory, our passages, the live transcript, notes state and the current slot."""
    S.history = []
    S.said = []
    S.transcript = []
    S.notes_last_len = 0
    S.slot = -1
    await stt.stop()
    await broadcast({"type": "transcript_replaced", "transcript": []})
    await broadcast({"type": "numbers", "items": []})
    await status_line("memory wiped: new debate")
    return {"ok": True}


@app.get("/show")
async def show():
    """Run of show: slots plus the current markdown of each script (re-read every call so edits show on reload)."""
    out = []
    for sl in SLOTS:
        d = dict(sl)
        if sl["kind"] == "script":
            path = HERE.parent / "content" / sl["file"]
            d["md"] = path.read_text() if path.exists() else f"(missing {sl['file']})"
        out.append(d)
    return {"slots": out, "last_said": S.said[-1] if S.said else ""}


@app.get("/panic")
async def panic():
    path = HERE.parent / "content" / "05-cheat-sheet.md"
    lines = []
    if path.exists():
        for ln in path.read_text().splitlines():
            if ln.startswith("- **") and "->" in ln:
                lines.append(ln[2:].replace("**", ""))
    return {"lines": lines[:12]}
