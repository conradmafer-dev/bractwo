#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
GAME_HOST=127.0.0.1
if [[ "${1:-}" == "lan" ]]; then GAME_HOST=0.0.0.0; fi
if [[ ! -x .venv/bin/python ]]; then python3 -m venv .venv; fi
.venv/bin/python -m pip install -r server/requirements.txt
printf '\nBractwo — Pogranicze — http://127.0.0.1:8080\nPozostaw okno otwarte. Zatrzymanie serwera: Ctrl+C.\n'
exec .venv/bin/python server/server.py --host "$GAME_HOST" --port 8080 --db data/world.sqlite3
