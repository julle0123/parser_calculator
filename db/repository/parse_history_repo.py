"""파싱히스토리 Repository."""

from __future__ import annotations

import traceback
from typing import Any

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.decorator import connectional
from db.models.parse_history import ParseHistory
from db.repository.base_repo import BaseRepository


class ParseHistoryRepository(BaseRepository):

    @property
    def table(self) -> type[ParseHistory]:
        return ParseHistory

    # ── 조회 ─────────────────────────────────────────────────────────────────

    @connectional
    async def select_one(
        self,
        session: AsyncSession,
        filter: dict[str, str],
        data: dict[str, Any],
    ) -> ParseHistory | None:
        try:
            stmt = select(ParseHistory).where(*self._where(filter, data))
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception:
            traceback.print_exc()
            return None

    @connectional
    async def select_list(
        self,
        session: AsyncSession,
        filter: dict[str, str] | None = None,
        data: dict[str, Any] | None = None,
    ) -> list[ParseHistory]:
        try:
            stmt = select(ParseHistory)
            if filter and data:
                stmt = stmt.where(*self._where(filter, data))
            result = await session.execute(stmt)
            return list(result.scalars().all())
        except Exception:
            traceback.print_exc()
            return []

    # ── 등록 ─────────────────────────────────────────────────────────────────

    @connectional
    async def insert_one(
        self,
        session: AsyncSession,
        data: dict[str, Any],
    ) -> bool:
        try:
            await session.execute(insert(ParseHistory).values(**data))
            await session.commit()
            return True
        except Exception:
            await session.rollback()
            traceback.print_exc()
            return False

    @connectional
    async def insert_many(
        self,
        session: AsyncSession,
        data: list[dict[str, Any]],
    ) -> bool:
        try:
            await session.execute(insert(ParseHistory), data)
            await session.commit()
            return True
        except Exception:
            await session.rollback()
            traceback.print_exc()
            return False

    # ── 수정 ─────────────────────────────────────────────────────────────────

    @connectional
    async def update_one(
        self,
        session: AsyncSession,
        filter: dict[str, str],
        data: dict[str, Any],
    ) -> bool:
        try:
            await session.execute(
                update(ParseHistory)
                .where(*self._where(filter, data))
                .values(**self._set_values(filter, data))
            )
            await session.commit()
            return True
        except Exception:
            await session.rollback()
            traceback.print_exc()
            return False

    @connectional
    async def update_many(
        self,
        session: AsyncSession,
        filter: dict[str, str],
        data: list[dict[str, Any]],
    ) -> bool:
        try:
            for row in data:
                await session.execute(
                    update(ParseHistory)
                    .where(*self._where(filter, row))
                    .values(**self._set_values(filter, row))
                )
            await session.commit()
            return True
        except Exception:
            await session.rollback()
            traceback.print_exc()
            return False

    # ── 삭제 ─────────────────────────────────────────────────────────────────

    @connectional
    async def delete_one(
        self,
        session: AsyncSession,
        filter: dict[str, str],
        data: dict[str, Any],
    ) -> bool:
        try:
            await session.execute(
                delete(ParseHistory).where(*self._where(filter, data))
            )
            await session.commit()
            return True
        except Exception:
            await session.rollback()
            traceback.print_exc()
            return False
