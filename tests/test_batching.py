import pytest

from architect.batching import Op, run_batched, chunks, AbortRun, TransientError


class Sleeper:
    def __init__(self):
        self.calls = []

    async def __call__(self, s):
        self.calls.append(s)


def ok(v):
    async def f():
        return v
    return f


def test_chunks():
    assert chunks(list(range(7)), 3) == [[0, 1, 2], [3, 4, 5], [6]]
    with pytest.raises(ValueError):
        chunks([1], 0)


async def test_pauses_between_batches_only():
    sl = Sleeper()
    res = await run_batched([Op(str(i), ok(i)) for i in range(12)], batch_size=5, pause=1.5, sleep=sl)
    assert [r.value for r in res] == list(range(12))
    assert sl.calls == [1.5, 1.5]


async def test_retries_transient_then_succeeds():
    sl, n = Sleeper(), {"i": 0}

    async def flaky():
        n["i"] += 1
        if n["i"] < 3:
            e = Exception("429")
            e.status = 429
            raise e
        return "done"
    res = await run_batched([Op("x", flaky)], pause=1, backoff=2, retries=3, sleep=sl)
    assert res[0].ok and res[0].attempts == 3 and sl.calls == [1, 2]


async def test_gives_up_after_retries():
    async def always():
        raise TransientError("boom")
    res = await run_batched([Op("x", always), Op("y", ok(1))], retries=2, sleep=Sleeper())
    assert not res[0].ok and res[0].attempts == 3 and res[1].ok


async def test_ordinary_failure_continues_critical_aborts():
    async def bad():
        raise ValueError("nope")
    res = await run_batched([Op("a", bad), Op("b", ok(2))], sleep=Sleeper())
    assert [r.ok for r in res] == [False, True] and "nope" in res[0].error
    with pytest.raises(AbortRun) as ei:
        await run_batched([Op("a", bad, critical=True), Op("b", ok(2))], sleep=Sleeper())
    assert len(ei.value.results) == 1


async def test_progress_reports():
    seen = []

    async def prog(p):
        seen.append((p.done, p.total, p.percent))
    await run_batched([Op(str(i), ok(i)) for i in range(7)], batch_size=3, sleep=Sleeper(), on_progress=prog)
    assert seen == [(3, 7, 42), (6, 7, 85), (7, 7, 100)]
