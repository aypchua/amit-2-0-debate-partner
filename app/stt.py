"""Live speech-to-text via Apple SpeechAnalyzer (macOS 26) using the `yap` CLI.

`yap dictate --txt` prints each finalised result the moment it lands, flushed, WITHOUT a newline (the only
newline comes at exit). So we read raw chunks, not lines, and treat each chunk as a phrase.
`yap listen --txt`  does the same for system audio (needs Screen Recording permission); handy for
rehearsing against a played-back mock speech. We read stdout line by line and hand each phrase
to a callback. Stop with SIGINT so yap flushes cleanly.
"""
from __future__ import annotations

import asyncio
import shutil
import signal
import time
from typing import Awaitable, Callable

Callback = Callable[[str], Awaitable[None]]


class YapSTT:
    def __init__(self, on_phrase: Callback, on_status: Callback | None = None):
        self.on_phrase = on_phrase
        self.on_status = on_status
        self.proc: asyncio.subprocess.Process | None = None
        self.source = "mic"
        self.started_at: float | None = None
        self.last_phrase_at: float | None = None
        self._reader: asyncio.Task | None = None

    @staticmethod
    def available() -> bool:
        return shutil.which("yap") is not None

    @property
    def running(self) -> bool:
        return self.proc is not None and self.proc.returncode is None

    async def start(self, source: str = "mic", locale: str | None = None) -> None:
        if self.running:
            return
        sub = "dictate" if source == "mic" else "listen"
        args = ["yap", sub, "--txt"]
        if locale:
            args += ["--locale", locale]
        self.source = source
        self.proc = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        self.started_at = time.time()
        self.last_phrase_at = None
        self._reader = asyncio.create_task(self._read())
        if self.on_status:
            await self.on_status(f"stt started ({source})")

    async def _read(self) -> None:
        assert self.proc and self.proc.stdout and self.proc.stderr
        async def read_err():
            err = (await self.proc.stderr.read()).decode(errors="replace").strip()
            if err and self.on_status:
                await self.on_status(f"yap: {err[:300]}")
        err_task = asyncio.create_task(read_err())
        try:
            pending = b""
            while True:
                chunk = await self.proc.stdout.read(4096)
                if not chunk:
                    break
                pending += chunk
                # yap emits whole finalised results per write; decode what we have (guard split UTF-8).
                try:
                    text = pending.decode()
                except UnicodeDecodeError:
                    continue
                pending = b""
                text = text.strip()
                if text:
                    self.last_phrase_at = time.time()
                    await self.on_phrase(text)
        finally:
            await err_task
            if self.on_status:
                await self.on_status("stt stopped")

    async def stop(self, wait: float = 1.2) -> None:
        """SIGINT yap and wait up to `wait` seconds for its final flush. Late phrases still get appended
        by the reader task after we return, so a rebuttal can start without blocking on the tail."""
        if not self.running:
            return
        assert self.proc
        try:
            self.proc.send_signal(signal.SIGINT)
            await asyncio.wait_for(self.proc.wait(), timeout=wait)
        except asyncio.TimeoutError:
            asyncio.get_running_loop().call_later(3.0, self._kill_if_alive)
        except ProcessLookupError:
            pass

    def _kill_if_alive(self) -> None:
        if self.proc and self.proc.returncode is None:
            self.proc.kill()

    def silence_seconds(self) -> float | None:
        """Seconds since the last phrase (None if nothing heard yet)."""
        if not self.running or self.last_phrase_at is None:
            return None
        return time.time() - self.last_phrase_at
