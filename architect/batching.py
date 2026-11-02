"""Rate-limit-safe batching.

discord.py already waits out 429s; on top of that we run operations in small batches with a
pause between batches (Discord's channel-create limit is the tight one), retry transient
failures with backoff, keep going past ordinary failures, and report progress."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Optional


@dataclass
class Op:
    label: str
    fn: Callable[[], Awaitable]
    critical: bool = False       # a failure stops the run


@dataclass
class Result:
    label: str
    ok: bool
    value: object = None
    error: str = ""
    attempts: int = 1


@dataclass
class Progress:
    done: int
    total: int
    failed: int
    label: str
    results: list = field(default_factory=list)

    @property
    def percent(self) -> int:
        return 100 if self.total == 0 else int(self.done * 100 / self.total)


class AbortRun(RuntimeError):
    def __init__(self, msg, results):
        super().__init__(msg)
        self.results = results


def is_transient(exc: BaseException) -> bool:
    status = getattr(exc, "status", None)
    if isinstance(status, int) and (status == 429 or status >= 500):
        return True
    return isinstance(exc, (asyncio.TimeoutError, ConnectionError, TransientError))


class TransientError(RuntimeError):
    pass


def chunks(seq, n):
    if n < 1:
        raise ValueError("batch size must be >= 1")
    return [seq[i:i + n] for i in range(0, len(seq), n)]


async def run_batched(ops: list[Op], *, batch_size: int = 5, pause: float = 1.0, retries: int = 3,
                      backoff: float = 2.0, on_progress: Optional[Callable[[Progress], Awaitable]] = None,
                      sleep=asyncio.sleep, progress_every: int = 1) -> list[Result]:
    results: list[Result] = []
    total = len(ops)
    failed = 0
    for bi, batch in enumerate(chunks(ops, batch_size)):
        if bi:
            await sleep(pause)
        for op in batch:
            attempt = 0
            while True:
                attempt += 1
                try:
                    v = await op.fn()
                    results.append(Result(op.label, True, v, attempts=attempt))
                    break
                except Exception as e:  # noqa: BLE001 - we report every failure
                    if is_transient(e) and attempt <= retries:
                        await sleep(pause * backoff ** (attempt - 1))
                        continue
                    failed += 1
                    results.append(Result(op.label, False, None, f"{type(e).__name__}: {e}"[:300], attempt))
                    if op.critical:
                        raise AbortRun(f"stopped at '{op.label}': {e}", results) from e
                    break
        if on_progress and ((bi + 1) % progress_every == 0 or len(results) == total):
            await on_progress(Progress(len(results), total, failed, batch[-1].label, results))
    return results
