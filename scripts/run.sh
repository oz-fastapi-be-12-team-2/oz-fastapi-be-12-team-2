#!/bin/sh
set -e

# 초기화는 처음 한 번만
#uv run aerich init -t core.config.TORTOISE_ORM
#uv run aerich init-db

# (필요시) 마이그레이션 수행 (aerich 등)
# aerich 초기화 (한 번만)
uv run aerich init -t core.config.TORTOISE_ORM || true
uv run aerich init-db || true
uv run aerich migrate || true
uv run aerich upgrade || true

# FastAPI 앱 실행 (개발용 --reload 포함)
# app.main:app 에서 app.main은 위치를, :app은 main.py의 FastAPI 인스턴스 이름
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload