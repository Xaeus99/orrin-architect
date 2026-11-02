import json

import pytest
from aiohttp import web

from architect import presets
from architect.planner import make_plan
from architect.planner.llm import LLMPlanner, extract_json, LLMError, planner_from_env

GOOD = presets.get("gaming")
GOOD["server_name"] = "From The Model"


def test_extract_json_variants():
    assert extract_json('{"a": 1}') == {"a": 1}
    assert extract_json('```json\n{"a": {"b": "}"}}\n```') == {"a": {"b": "}"}}
    assert extract_json('Sure! Here it is: {"x": "y \\" z"} hope that helps') == {"x": 'y " z'}
    with pytest.raises(LLMError):
        extract_json("no json here")


def test_planner_from_env():
    assert planner_from_env({"ARCHITECT_LLM": "none"}) is None
    p = planner_from_env({})
    assert p.kind == "ollama" and p.base_url == "http://localhost:11434"
    assert planner_from_env({"ARCHITECT_LLM": "openai"}) is None  # needs a URL + model
    p = planner_from_env({"ARCHITECT_LLM": "openai", "LLM_BASE_URL": "https://x/v1/", "LLM_MODEL": "m"})
    assert p.kind == "openai" and p.base_url == "https://x/v1"


async def serve(aiohttp_server_factory, replies):
    calls = []

    async def ollama(req):
        body = await req.json()
        calls.append(body)
        return web.json_response({"message": {"content": replies[min(len(calls), len(replies)) - 1]}})

    async def openai(req):
        body = await req.json()
        calls.append(body)
        return web.json_response({"choices": [{"message": {"content": replies[min(len(calls), len(replies)) - 1]}}]})
    app = web.Application()
    app.router.add_post("/api/chat", ollama)
    app.router.add_post("/v1/chat/completions", openai)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    return runner, f"http://127.0.0.1:{port}", calls


@pytest.mark.parametrize("kind,path", [("ollama", ""), ("openai", "/v1")])
async def test_good_reply_is_used(kind, path):
    runner, url, calls = await serve(None, ["Here you go:\n" + json.dumps(GOOD)])
    try:
        llm = LLMPlanner(kind, "test-model", url + path, timeout=10)
        plan, warns, used = await make_plan("gaming", llm=llm)
        assert used == "llm:test-model" and plan["server_name"] == "From The Model"
        assert len(calls) == 1
        if kind == "ollama":
            assert calls[0]["format"]["type"] == "object" and calls[0]["stream"] is False
        else:
            assert calls[0]["response_format"] == {"type": "json_object"}
    finally:
        await runner.cleanup()


async def test_bad_then_good_retries_once():
    runner, url, calls = await serve(None, ['{"categories": []}', json.dumps(GOOD)])
    try:
        plan, warns, used = await make_plan("x", llm=LLMPlanner("ollama", "m", url, timeout=10))
        assert used == "llm:m" and len(calls) == 2
        assert "problems" in calls[1]["messages"][-1]["content"]
    finally:
        await runner.cleanup()


async def test_garbage_falls_back():
    runner, url, calls = await serve(None, ["I can't do JSON today"])
    try:
        plan, warns, used = await make_plan("study group", llm=LLMPlanner("ollama", "m", url, timeout=10))
        assert used == "fallback" and plan["source"] == "fallback:study"
        assert any("AI planner" in w for w in warns)
    finally:
        await runner.cleanup()


async def test_unreachable_falls_back():
    plan, warns, used = await make_plan("roleplay", llm=LLMPlanner("ollama", "m", "http://127.0.0.1:9", timeout=3))
    assert used == "fallback" and any("unavailable" in w for w in warns)
