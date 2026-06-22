"""Oracle ADB 비동기 엔진 — YAML 설정 기반 싱글톤.

엔진은 애플리케이션 전체에서 한 번만 생성된다.
init_engine() → 앱 시작 시 호출
close_engine() → 앱 종료 시 호출
get_db()       → FastAPI 의존성 (요청마다 세션 제공)
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Annotated

import yaml
from fastapi import Depends
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# DB_CONFIG_PATH 환경변수로 경로 오버라이드 가능; 기본은 프로젝트 루트 config/database.yaml
_CONFIG_PATH = Path(os.getenv("DB_CONFIG_PATH", "config/database.yaml"))

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────

def _load_config() -> dict:
    with open(_CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)["database"]


def _build_url(cfg: dict) -> URL:
    # URL.create() 가 비밀번호의 특수문자(@, # 등)를 자동 인코딩한다
    if cfg.get("dsn"):
        return URL.create(
            drivername="oracle+oracledb",
            username=cfg["user"],
            password=cfg["password"],
            host=cfg["dsn"],
        )
    return URL.create(
        drivername="oracle+oracledb",
        username=cfg["user"],
        password=cfg["password"],
        host=cfg["host"],
        port=int(cfg["port"]),
        query={"service_name": cfg["service_name"]},
    )


def _build_connect_args(cfg: dict) -> dict:
    args: dict = {}
    if cfg.get("wallet_location"):
        args["wallet_location"] = cfg["wallet_location"]
        args["config_dir"] = cfg["wallet_location"]  # tnsnames.ora / sqlnet.ora 경로
    if cfg.get("wallet_password"):
        args["wallet_password"] = cfg["wallet_password"]
    return args


# ── 공개 API ──────────────────────────────────────────────────────────────────

def init_engine() -> None:
    """앱 시작 시 한 번만 호출 — 이미 초기화된 경우 무시."""
    global _engine, _session_factory
    if _engine is not None:
        return

    cfg = _load_config()
    pool = cfg.get("pool", {})

    _engine = create_async_engine(
        _build_url(cfg),
        connect_args=_build_connect_args(cfg),
        pool_size=pool.get("size", 5),
        max_overflow=pool.get("max_overflow", 10),
        pool_timeout=pool.get("timeout", 30),
        pool_recycle=pool.get("recycle", 3600),
        pool_pre_ping=pool.get("pre_ping", True),
        echo=cfg.get("echo", False),
    )
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def close_engine() -> None:
    """앱 종료 시 호출 — 커넥션 풀 반환."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI Depends 의존성 — 요청마다 세션 제공, 자동 커밋/롤백."""
    if _session_factory is None:
        raise RuntimeError("DB 엔진이 초기화되지 않았습니다. init_engine()을 먼저 호출하세요.")
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# 라우터 파라미터 타입으로 사용: async def endpoint(db: DbSession) -> ...
DbSession = Annotated[AsyncSession, Depends(get_db)]
