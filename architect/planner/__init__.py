"""Planners turn a prompt into a raw plan. `make_plan` always returns a valid plan:
LLM first (if configured), validated; on any failure, the deterministic fallback."""
from __future__ import annotations

import logging

from ..schema import validate_plan
from .fallback import fallback_plan
from .llm import LLMPlanner, LLMError, planner_from_env

log = logging.getLogger("architect.planner")


async def make_plan(prompt: str, *, llm: LLMPlanner | None = None, variant: int = 0,
                    server_name: str = "") -> tuple[dict, list[str], str]:
    """Return (plan, warnings, used) where used is 'llm:<model>' or 'fallback'."""
    notes: list[str] = []
    if llm is not None:
        try:
            raw = await llm.plan(prompt, variant=variant)
            if server_name and not raw.get("server_name"):
                raw["server_name"] = server_name
            plan, warns, errs = validate_plan(raw)
            if not errs:
                plan["source"] = f"llm:{llm.model}"
                return _fill(plan, server_name), warns, f"llm:{llm.model}"
            notes.append("AI plan was unusable (" + "; ".join(errs) + "), used the built-in planner")
        except LLMError as e:
            notes.append(f"AI planner unavailable ({e}), used the built-in planner")
        except Exception as e:  # never let the planner kill a /setup
            log.exception("llm planner crashed")
            notes.append(f"AI planner error ({type(e).__name__}), used the built-in planner")
    raw = fallback_plan(prompt, variant=variant)
    if server_name and not raw.get("server_name"):
        raw["server_name"] = server_name
    plan, warns, errs = validate_plan(raw)
    assert not errs, errs
    return _fill(plan, server_name), notes + warns, "fallback"


def _fill(plan: dict, server_name: str) -> dict:
    name = plan.get("server_name") or server_name or "the server"
    plan["welcome_message"] = (plan.get("welcome_message") or "Welcome to {server}!").replace("{server}", name)
    return plan


__all__ = ["make_plan", "fallback_plan", "LLMPlanner", "LLMError", "planner_from_env"]
