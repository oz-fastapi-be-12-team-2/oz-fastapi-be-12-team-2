#!/bin/sh
set -e

# 초기화는 처음 한 번만
#uv run aerich init -t core.config.TORTOISE_ORM
uv run aerich init-db

# (필요시) 마이그레이션 수행 (aerich 등)
uv run aerich migrate
uv run aerich upgrade

# FastAPI 앱 실행 (개발용 --reload 포함)
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload