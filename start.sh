#!/usr/bin/env bash
# ORRIN Architect on Linux / macOS / a free VM / Raspberry Pi.
set -e
cd "$(dirname "$0")"
[ -x .venv/bin/python ] || { python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt; }
[ -f .env ] || { cp .env.example .env; echo "Edit .env (DISCORD_TOKEN=...) and run again."; exit 1; }
exec .venv/bin/python -m architect.bot
