#!/usr/bin/env bash
set -e

alembic upgrade head
uvicorn app.main:app --reload --log-level debug
