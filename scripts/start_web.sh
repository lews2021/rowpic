#!/usr/bin/env bash
# rowpic — web mode (Linux/macOS)
set -e
cd "$(dirname "$0")/.."
[ -d frontend/node_modules ] || (cd frontend && npm install)
python3 scripts/start_web.py
