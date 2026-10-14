#!/bin/zsh
# AMIT 2.0 launcher. Run from Terminal.app (so the mic permission prompt attaches to Terminal).
set -e
cd "$(dirname "$0")"
export OLLAMA_KEEP_ALIVE=-1
PORT=${PORT:-8765}

echo "== checks =="
command -v yap >/dev/null && echo "yap: ok" || echo "yap: MISSING (brew install yap)"
if ! curl -s http://127.0.0.1:11434/api/tags >/dev/null; then
  echo "ollama: starting..."; (ollama serve >/dev/null 2>&1 &); sleep 2
fi
curl -s http://127.0.0.1:11434/api/tags | python3 -c "import sys,json; print('ollama models:', [m['name'] for m in json.load(sys.stdin)['models']])"
[ -f .env ] && echo ".env: found" || echo ".env: missing (cloud racers off, local only)"

echo "== server on http://127.0.0.1:$PORT =="
(sleep 1.5; open "http://127.0.0.1:$PORT") &
exec uv run uvicorn server:app --host 127.0.0.1 --port "$PORT" --log-level warning
