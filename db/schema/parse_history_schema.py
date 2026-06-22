from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class ParseHistorySchema(BaseModel):
    """파싱히스토리 스키마."""

    model_config = ConfigDict(from_attributes=True)

    # ── PK ───────────────────────────────────────────────────────────────────
    pipeline_id: str
    doc_id: str
    parse_id: str

    # ── 문서 정보 ─────────────────────────────────────────────────────────────
    doc_extension: str | None = None
    parse_start_date: str | None = None   # 정의서 상 varchar2(50)
    parse_end_date: str | None = None
    parse_parameter: dict[str, Any] | None = None
    origin_doc_path: str
    parse_result_doc_path: str

    # ── 파싱 결과 ─────────────────────────────────────────────────────────────
    parse_result_json: str | None = None
    parse_result_html: str | None = None
    parse_result_doc_format: str | None = None
    parse_status_code: int | None = None
    parse_status_yn: str | None = None
    parse_score: Decimal

    # ── 수정 정보 ─────────────────────────────────────────────────────────────
    parse_modified_yn: str | None = None
    parse_modified_id: str | None = None
    parse_modified_date: datetime | None = None

    # ── 기타 ─────────────────────────────────────────────────────────────────
    reparse_required: str | None = None
    pii_detected: str | None = None
    anonymize_type: str | None = None
