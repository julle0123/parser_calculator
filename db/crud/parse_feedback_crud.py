"""파싱 뷰어 피드백 CRUD — 상황별 비즈니스 함수 정의.

각 함수는 필요한 컬럼을 직접 파라미터로 받아
내부에서 data / filter 를 구성한 뒤 Repository 를 호출한다.
"""

from __future__ import annotations

import traceback
from datetime import datetime

from db.repository.parse_feedback_repo import ParseFeedbackRepository
from db.schema.parse_feedback_schema import ParseFeedbackSchema

_repo = ParseFeedbackRepository()


# ── 조회 ──────────────────────────────────────────────────────────────────────

async def select_feedback(
    doc_id: str,
    feedback_user_id: str,
) -> ParseFeedbackSchema | None:
    try:
        filter = {"doc_id": "=", "feedback_user_id": "="}
        data = {
            "doc_id": doc_id,
            "feedback_user_id": feedback_user_id,
        }
        row = await _repo.select_one(filter=filter, data=data)
        return ParseFeedbackSchema.model_validate(row) if row else None
    except Exception:
        traceback.print_exc()
        return None


async def select_feedback_by_doc(
    doc_id: str,
) -> list[ParseFeedbackSchema]:
    try:
        filter = {"doc_id": "="}
        data = {"doc_id": doc_id}

        rows = await _repo.select_list(filter=filter, data=data)
        return [ParseFeedbackSchema.model_validate(r) for r in rows]
    except Exception:
        traceback.print_exc()
        return []


# ── 등록 ──────────────────────────────────────────────────────────────────────

async def insert_feedback(
    doc_id: str,
    feedback_user_id: str,
    feedback_user_nm: str | None = None,
    feedback_message: str | None = None,
    feedback_date: datetime | None = None,
) -> bool:
    try:
        data = {
            "doc_id": doc_id,
            "feedback_user_id": feedback_user_id,
        }
        if feedback_user_nm is not None: data["feedback_user_nm"] = feedback_user_nm
        if feedback_message is not None: data["feedback_message"] = feedback_message
        if feedback_date is not None: data["feedback_date"] = feedback_date

        is_success = await _repo.insert_one(data=data)
        return is_success
    except Exception:
        traceback.print_exc()
        return False


async def insert_feedback_many(
    data: list[dict],
) -> bool:
    try:
        is_success = await _repo.insert_many(data=data)
        return is_success
    except Exception:
        traceback.print_exc()
        return False


# ── 수정 ──────────────────────────────────────────────────────────────────────

async def update_feedback(
    doc_id: str,
    feedback_user_id: str,
    feedback_message: str | None = None,
    feedback_modified_yn: str | None = None,
    feedback_modified_date: datetime | None = None,
) -> bool:
    try:
        filter = {"doc_id": "=", "feedback_user_id": "="}
        data = {
            "doc_id": doc_id,
            "feedback_user_id": feedback_user_id,
        }
        if feedback_message is not None: data["feedback_message"] = feedback_message
        if feedback_modified_yn is not None: data["feedback_modified_yn"] = feedback_modified_yn
        if feedback_modified_date is not None: data["feedback_modified_date"] = feedback_modified_date

        is_success = await _repo.update_one(filter=filter, data=data)
        return is_success
    except Exception:
        traceback.print_exc()
        return False


async def update_feedback_many(
    data: list[dict],
) -> bool:
    try:
        filter = {"doc_id": "=", "feedback_user_id": "="}
        is_success = await _repo.update_many(filter=filter, data=data)
        return is_success
    except Exception:
        traceback.print_exc()
        return False


# ── 삭제 ──────────────────────────────────────────────────────────────────────

async def delete_feedback(
    doc_id: str,
    feedback_user_id: str,
) -> bool:
    try:
        filter = {"doc_id": "=", "feedback_user_id": "="}
        data = {
            "doc_id": doc_id,
            "feedback_user_id": feedback_user_id,
        }
        is_success = await _repo.delete_one(filter=filter, data=data)
        return is_success
    except Exception:
        traceback.print_exc()
        return False


# ── 필요한 함수를 아래에 추가하세요 ────────────────────────────────────────────
