"""파싱상태코드 CRUD — 상황별 비즈니스 함수 정의.

각 함수는 필요한 컬럼을 직접 파라미터로 받아
내부에서 data / filter 를 구성한 뒤 Repository 를 호출한다.
"""

from __future__ import annotations

import traceback

from db.repository.parse_status_code_repo import ParseStatusCodeRepository
from db.schema.parse_status_code_schema import ParseStatusCodeSchema

_repo = ParseStatusCodeRepository()


# ── 조회 ──────────────────────────────────────────────────────────────────────

async def select_status_code(
    parse_status_code: int,
) -> ParseStatusCodeSchema | None:
    try:
        filter = {"parse_status_code": "="}
        data = {"parse_status_code": parse_status_code}

        row = await _repo.select_one(filter=filter, data=data)
        return ParseStatusCodeSchema.model_validate(row) if row else None
    except Exception:
        traceback.print_exc()
        return None


async def select_status_code_list() -> list[ParseStatusCodeSchema]:
    try:
        rows = await _repo.select_list()
        return [ParseStatusCodeSchema.model_validate(r) for r in rows]
    except Exception:
        traceback.print_exc()
        return []


# ── 등록 ──────────────────────────────────────────────────────────────────────

async def insert_status_code(
    parse_status_code: int,
    parse_starus_message: str,
) -> bool:
    try:
        data = {
            "parse_status_code": parse_status_code,
            "parse_starus_message": parse_starus_message,
        }
        is_success = await _repo.insert_one(data=data)
        return is_success
    except Exception:
        traceback.print_exc()
        return False


async def insert_status_code_many(
    data: list[dict],
) -> bool:
    try:
        is_success = await _repo.insert_many(data=data)
        return is_success
    except Exception:
        traceback.print_exc()
        return False


# ── 수정 ──────────────────────────────────────────────────────────────────────

async def update_status_message(
    parse_status_code: int,
    parse_starus_message: str,
) -> bool:
    try:
        filter = {"parse_status_code": "="}
        data = {
            "parse_status_code": parse_status_code,
            "parse_starus_message": parse_starus_message,
        }
        is_success = await _repo.update_one(filter=filter, data=data)
        return is_success
    except Exception:
        traceback.print_exc()
        return False


async def update_status_message_many(
    data: list[dict],
) -> bool:
    try:
        filter = {"parse_status_code": "="}
        is_success = await _repo.update_many(filter=filter, data=data)
        return is_success
    except Exception:
        traceback.print_exc()
        return False


# ── 삭제 ──────────────────────────────────────────────────────────────────────

async def delete_status_code(
    parse_status_code: int,
) -> bool:
    try:
        filter = {"parse_status_code": "="}
        data = {"parse_status_code": parse_status_code}

        is_success = await _repo.delete_one(filter=filter, data=data)
        return is_success
    except Exception:
        traceback.print_exc()
        return False


# ── 필요한 함수를 아래에 추가하세요 ────────────────────────────────────────────
