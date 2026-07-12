#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

# Используем интерпретатор из локального .venv, чтобы запуск не зависел от того,
# активировано ли окружение в текущем шелле.
VENV=.venv
if [ ! -x "$VENV/bin/python" ]; then
  echo "Нет $VENV. Создай окружение и поставь зависимости:" >&2
  echo "  python3.11 -m venv $VENV && $VENV/bin/pip install -r requirements.txt" >&2
  exit 1
fi

"$VENV/bin/alembic" upgrade head
"$VENV/bin/uvicorn" app.main:app --reload --log-level debug
