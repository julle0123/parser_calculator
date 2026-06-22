"""@connectional 데코레이터 — Repository 메서드에 DB 세션 자동 주입.

메서드 시그니처: def method(self, session, ...)
호출 방법:       await repo.method(...)   ← session 전달 불필요
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def connectional(func: F) -> F:
    """비동기 Repository 메서드에 AsyncSession을 자동으로 주입.

    - 메서드 두 번째 파라미터(self 다음)를 session으로 선언
    - 호출 측에서 session 전달 불필요 — 데코레이터가 세션 생성 후 주입
    - 세션 범위(열기·닫기)는 데코레이터가 관리
    - commit / rollback은 각 메서드 내부에서 직접 수행

    사용 예)
        class ParseHistoryRepository:
            @connectional
            async def insert_one(self, session: AsyncSession, data: dict) -> bool:
                try:
                    await session.execute(insert(ParseHistory).values(**data))
                    await session.commit()
                    return True
                except Exception:
                    await session.rollback()
                    traceback.print_exc()
                    return False

        # 호출 — session 생략
        repo = ParseHistoryRepository()
        is_success = await repo.insert_one(data={...})
        rows       = await repo.select_list(filters=[...])
    """

    @functools.wraps(func)
    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        from db.engine import _session_factory

        if _session_factory is None:
            raise RuntimeError(
                "DB 엔진이 초기화되지 않았습니다. init_engine()을 먼저 호출하세요."
            )
        async with _session_factory() as session:
            return await func(self, session, *args, **kwargs)

    return wrapper  # type: ignore[return-value]
