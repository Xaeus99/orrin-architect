"""Dry run: print the plan for a prompt without touching Discord.

  python -m architect.cli "a cozy study group for AP exams"
  python -m architect.cli --preset gaming
  python -m architect.cli "gaming clan" --json --variant 2 --no-llm
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

from . import presets
from .planner import make_plan, planner_from_env
from .schema import validate_plan
from .preview import plan_text, plan_embed, embed_size


def main(argv=None):
    ap = argparse.ArgumentParser(prog="architect-dry-run", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prompt", nargs="*", help="what the server is for")
    ap.add_argument("--preset", choices=sorted(presets.PRESETS))
    ap.add_argument("--variant", type=int, default=0, help="like pressing Regenerate N times")
    ap.add_argument("--json", action="store_true", help="print the validated plan as JSON")
    ap.add_argument("--no-llm", action="store_true", help="use only the built-in planner")
    ap.add_argument("--name", default="", help="server name for the welcome text")
    a = ap.parse_args(argv)
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if a.preset:
        plan, warns, _ = validate_plan(presets.get(a.preset))
        used = f"preset:{a.preset}"
    else:
        prompt = " ".join(a.prompt).strip()
        if not prompt:
            ap.error("give a prompt or --preset")
        llm = None if a.no_llm else planner_from_env()
        plan, warns, used = asyncio.run(make_plan(prompt, llm=llm, variant=a.variant, server_name=a.name))
    if a.json:
        print(json.dumps({"planner": used, "warnings": warns, "plan": plan}, ensure_ascii=False, indent=2))
    else:
        print(plan_text(plan, warns, used))
        print(f"\n(preview embed size {embed_size(plan_embed(plan))}/6000 characters)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
