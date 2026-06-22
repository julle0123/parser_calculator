"""파싱히스토리 CRUD — 상황별 비즈니스 함수 정의.

각 함수는 필요한 컬럼을 직접 파라미터로 받아
내부에서 data / filter 를 구성한 뒤 Repository 를 호출한다.
"""

from __future__ import annotations

import traceback
from datetime import datetime
from decimal import Decimal
from typing import Any

from db.repository.parse_history_repo import ParseHistoryRepository
from db.schema.parse_history_schema import ParseHistorySchema

_repo = ParseHistoryRepository()


# ── 조회 ──────────────────────────────────────────────────────────────────────

async def select_parse_history(
    parse_id: str,
) -> ParseHistorySchema | None:
    try:
        filter = {"parse_id": "="}
        data = {"parse_id": parse_id}

        row = await _repo.select_one(filter=filter, data=data)
        return ParseHistorySchema.model_validate(row) if row else None
    except Exception:
        traceback.print_exc()
        return None


async def select_parse_history_by_pipeline(
    pipeline_id: str,
) -> list[ParseHistorySchema]:
    try:
        filter = {"pipeline_id": "="}
        data = {"pipeline_id": pipeline_id}

        rows = await _repo.select_list(filter=filter, data=data)
        return [ParseHistorySchema.model_validate(r) for r in rows]
    except Exception:
        traceback.print_exc()
        return []


async def select_parse_history_success(
    pipeline_id: str,
    parse_status_yn: str,
) -> list[ParseHistorySchema]:
    try:
        filter = {"pipeline_id": "=", "parse_status_yn": "="}
        data = {
            "pipeline_id": pipeline_id,
            "parse_status_yn": parse_status_yn,
        }
        rows = await _repo.select_list(filter=filter, data=data)
        return [ParseHistorySchema.model_validate(r) for r in rows]
    except Exception:
        traceback.print_exc()
        return []


# ── 등록 ──────────────────────────────────────────────────────────────────────

async def insert_parse_history(
    pipeline_id: str,
    doc_id: str,
    parse_id: str,
    origin_doc_path: str,
    parse_result_doc_path: str,
    parse_score: Decimal,
    doc_extension: str | None = None,
    parse_start_date: str | None = None,
    parse_end_date: str | None = None,
    parse_parameter: dict[str, Any] | None = None,
    parse_result_json: str | None = None,
    parse_result_html: str | None = None,
    parse_result_doc_format: str | None = None,
    parse_status_code: int | None = None,
    parse_status_yn: str | None = None,
    pii_detected: str | None = None,
    anonymize_type: str | None = None,
) -> bool:
    try:
        data = {
            "pipeline_id": pipeline_id,
            "doc_id": doc_id,
            "parse_id": parse_id,
            "origin_doc_path": origin_doc_path,
            "parse_result_doc_path": parse_result_doc_path,
            "parse_score": parse_score,
        }
        if doc_extension is not None: data["doc_extension"] = doc_extension
        if parse_start_date is not None: data["parse_start_date"] = parse_start_date
        if parse_end_date is not None: data["parse_end_date"] = parse_end_date
        if parse_parameter is not None: data["parse_parameter"] = parse_parameter
        if parse_result_json is not None: data["parse_result_json"] = parse_result_json
        if parse_result_html is not None: data["parse_result_html"] = parse_result_html
        if parse_result_doc_format is not None: data["parse_result_doc_format"] = parse_result_doc_format
        if parse_status_code is not None: data["parse_status_code"] = parse_status_code
        if parse_status_yn is not None: data["parse_status_yn"] = parse_status_yn
        if pii_detected is not None: data["pii_detected"] = pii_detected
        if anonymize_type is not None: data["anonymize_type"] = anonymize_type

        is_success = await _repo.insert_one(data=data)
        return is_success
    except Exception:
        traceback.print_exc()
        return False


async def insert_parse_history_many(
    data: list[dict],
) -> bool:
    try:
        is_success = await _repo.insert_many(data=data)
        return is_success
    except Exception:
        traceback.print_exc()
        return False


# ── 수정 ──────────────────────────────────────────────────────────────────────

async def update_parse_history_status(
    parse_id: str,
    parse_status_yn: str,
    parse_status_code: int,
) -> bool:
    try:
        filter = {"parse_id": "="}
        data = {
            "parse_id": parse_id,
            "parse_status_yn": parse_status_yn,
            "parse_status_code": parse_status_code,
        }
        is_success = await _repo.update_one(filter=filter, data=data)
        return is_success
    except Exception:
        traceback.print_exc()
        return False


async def update_parse_history_status_many(
    data: list[dict],
) -> bool:
    try:
        filter = {"parse_id": "="}
        is_success = await _repo.update_many(filter=filter, data=data)
        return is_success
    except Exception:
        traceback.print_exc()
        return False


async def update_parse_history_reparse(
    parse_id: str,
    reparse_required: str,
) -> bool:
    try:
        filter = {"parse_id": "="}
        data = {
            "parse_id": parse_id,
            "reparse_required": reparse_required,
        }
        is_success = await _repo.update_one(filter=filter, data=data)
        return is_success
    except Exception:
        traceback.print_exc()
        return False


async def update_parse_history_modified(
    parse_id: str,
    parse_modified_yn: str,
    parse_modified_id: str,
    parse_modified_date: datetime,
) -> bool:
    try:
        filter = {"parse_id": "="}
        data = {
            "parse_id": parse_id,
            "parse_modified_yn": parse_modified_yn,
            "parse_modified_id": parse_modified_id,
            "parse_modified_date": parse_modified_date,
        }
        is_success = await _repo.update_one(filter=filter, data=data)
        return is_success
    except Exception:
        traceback.print_exc()
        return False


# ── 삭제 ──────────────────────────────────────────────────────────────────────

async def delete_parse_history(
    parse_id: str,
) -> bool:
    try:
        filter = {"parse_id": "="}
        data = {"parse_id": parse_id}

        is_success = await _repo.delete_one(filter=filter, data=data)
        return is_success
    except Exception:
        traceback.print_exc()
        return False


# ── 필요한 함수를 아래에 추가하세요 ────────────────────────────────────────────
