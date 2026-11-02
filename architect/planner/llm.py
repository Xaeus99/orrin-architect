"""LLM planner backends (all optional, all free options):

* Ollama on the same PC (default): ARCHITECT_LLM=ollama, OLLAMA_URL, OLLAMA_MODEL
* Any OpenAI-compatible endpoint (e.g. a free tier): ARCHITECT_LLM=openai,
  LLM_BASE_URL, LLM_API_KEY, LLM_MODEL
* ARCHITECT_LLM=none -> no AI, the deterministic planner only.

The model gets the JSON schema, a compact example and strict instructions; its answer is
parsed, validated, and on failure retried once with the validator's errors."""
from __future__ import annotations

import asyncio
import json
import os
import re

import aiohttp

from ..schema import PLAN_JSON_SCHEMA, validate_plan
from ..permissions import PRESETS
from .. import presets as P


class LLMError(RuntimeError):
    pass


SYSTEM = """You design Discord server layouts. Reply with ONE JSON object only, no prose, no markdown.
Shape (keys): server_name, summary, style{category,separator,tree,emoji}, settings{verification_level
(none|low|medium|high|highest), explicit_content_filter (disabled|members_without_roles|all_members),
default_notifications (all|mentions), community(bool)}, roles[{name,color("#RRGGBB"),hoist,mentionable,
permissions (one of: %s, or a list of Discord permission names), self_assignable}],
categories[{name,emoji,private,visible_to[role names],read_only,writable_by[role names],
channels[{name (lowercase-with-hyphens for text),emoji,type(text|voice|forum|announcement|stage),topic,
slowmode(seconds),private,visible_to,read_only,writable_by,tags(forum only)}]}],
rules[short strings], rules_channel, welcome_channel, welcome_message, rules_gate(bool), member_role,
automod[{kind(spam|mention_spam|profanity|keyword),name,keywords,mention_limit}].
Guidelines: 4-8 categories, 3-8 channels each, 5-10 roles ordered from most to least powerful.
Exactly one top role gets "administrator"; staff get "admin"/"moderator"/"helper"; normal people get
"member"; ping/colour roles members pick themselves are "cosmetic" with self_assignable true.
Put rules/announcements/welcome in a first read_only category writable_by staff. Private staff
category visible_to staff roles. One emoji per category and channel. Keep names short and clear,
original and family friendly. Use real Discord features: forum channels for help/suggestions,
announcement channel for news, stage only for big talks. Never include NSFW channels."""


def _example() -> str:
    ex = P.get("study")
    ex.pop("source", None)
    return json.dumps(ex, ensure_ascii=False, separators=(",", ":"))


def extract_json(text: str) -> dict:
    """Pull the first JSON object out of a model reply (handles ```json fences and chatter)."""
    if not isinstance(text, str):
        raise LLMError("empty reply")
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    try:
        v = json.loads(t)
        if isinstance(v, dict):
            return v
    except json.JSONDecodeError:
        pass
    start = t.find("{")
    while start != -1:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(t)):
            c = t[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            elif c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        v = json.loads(t[start:i + 1])
                        if isinstance(v, dict):
                            return v
                    except json.JSONDecodeError:
                        break
                    break
        start = t.find("{", start + 1)
    raise LLMError("reply had no JSON object")


class LLMPlanner:
    def __init__(self, kind: str, model: str, base_url: str, api_key: str = "", timeout: float = 120.0,
                 temperature: float = 0.4):
        self.kind, self.model, self.base_url = kind, model, base_url.rstrip("/")
        self.api_key, self.timeout, self.temperature = api_key, timeout, temperature

    def messages(self, prompt: str, feedback: str = "") -> list[dict]:
        sys = SYSTEM % ", ".join(PRESETS) + "\nExample of a valid answer for a study group:\n" + _example()
        user = f"Design a Discord server for: {prompt.strip()[:1500]}"
        msgs = [{"role": "system", "content": sys}, {"role": "user", "content": user}]
        if feedback:
            msgs.append({"role": "user", "content": "Your last JSON had problems: " + feedback +
                         ". Reply again with the corrected JSON object only."})
        return msgs

    async def _post(self, session: aiohttp.ClientSession, msgs: list[dict], temperature: float) -> str:
        if self.kind == "ollama":
            body = {"model": self.model, "messages": msgs, "stream": False, "format": PLAN_JSON_SCHEMA,
                    "options": {"temperature": temperature, "num_ctx": 8192}}
            url = self.base_url + "/api/chat"
            headers = {}
        else:
            body = {"model": self.model, "messages": msgs, "temperature": temperature,
                    "response_format": {"type": "json_object"}}
            url = self.base_url + "/chat/completions"
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        try:
            async with session.post(url, json=body, headers=headers,
                                    timeout=aiohttp.ClientTimeout(total=self.timeout)) as r:
                txt = await r.text()
                if r.status >= 400:
                    raise LLMError(f"{self.kind} answered HTTP {r.status}: {txt[:200]}")
        except asyncio.TimeoutError as e:
            raise LLMError(f"{self.kind} timed out after {self.timeout:.0f}s") from e
        except aiohttp.ClientError as e:
            raise LLMError(f"can't reach {self.kind} at {self.base_url} ({type(e).__name__})") from e
        try:
            data = json.loads(txt)
        except json.JSONDecodeError as e:
            raise LLMError("endpoint did not answer JSON") from e
        if self.kind == "ollama":
            return (data.get("message") or {}).get("content", "")
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise LLMError("unexpected reply shape") from e

    async def plan(self, prompt: str, variant: int = 0) -> dict:
        temp = min(1.0, self.temperature + 0.2 * variant)
        async with aiohttp.ClientSession() as s:
            raw = extract_json(await self._post(s, self.messages(prompt), temp))
            _plan, warns, errs = validate_plan(raw)
            if errs:
                raw = extract_json(await self._post(s, self.messages(prompt, "; ".join(errs + warns[:10])), temp))
            return raw


def planner_from_env(env=None) -> LLMPlanner | None:
    env = env if env is not None else os.environ
    kind = env.get("ARCHITECT_LLM", "ollama").strip().lower()
    timeout = float(env.get("LLM_TIMEOUT", "120") or 120)
    if kind in {"", "none", "off", "false", "0"}:
        return None
    if kind == "ollama":
        return LLMPlanner("ollama", env.get("OLLAMA_MODEL", "qwen2.5:7b-instruct"),
                          env.get("OLLAMA_URL", "http://localhost:11434"), timeout=timeout)
    if kind in {"openai", "openai-compatible", "compatible"}:
        base = env.get("LLM_BASE_URL", "").strip()
        model = env.get("LLM_MODEL", "").strip()
        if not base or not model:
            return None
        return LLMPlanner("openai", model, base, env.get("LLM_API_KEY", ""), timeout=timeout)
    return None
