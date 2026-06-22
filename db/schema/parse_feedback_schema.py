from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ParseFeedbackSchema(BaseModel):
    """파싱 뷰어 피드백 스키마."""

    model_config = ConfigDict(from_attributes=True)

    # ── PK ───────────────────────────────────────────────────────────────────
    doc_id: str
    feedback_user_id: str

    # ── 피드백 내용 ───────────────────────────────────────────────────────────
    feedback_user_nm: str | None = None
    feedback_message: str | None = None
    feedback_date: datetime | None = None

    # ── 수정 정보 ─────────────────────────────────────────────────────────────
    feedback_modified_yn: str | None = None
    feedback_modified_date: datetime | None = None
