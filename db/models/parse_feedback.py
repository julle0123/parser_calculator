from sqlalchemy import Column, Text
from sqlalchemy.dialects.oracle import CHAR, TIMESTAMP, VARCHAR2

from db.base import Base


class ParseFeedback(Base):
    """파싱 뷰어 피드백 테이블 — 복합 PK: doc_id + feedback_user_id."""

    __tablename__ = "parse_feedback"

    doc_id = Column(VARCHAR2(20), primary_key=True, nullable=False, comment="문서ID")
    feedback_user_id = Column(VARCHAR2(20), primary_key=True, nullable=False, comment="피드백사용자ID")
    feedback_user_nm = Column(VARCHAR2(10), comment="피드백사용자명")
    feedback_message = Column(Text, comment="피드백내용")
    feedback_date = Column(TIMESTAMP, comment="개시일자")
    feedback_modified_yn = Column(CHAR(1), comment="수정여부(Y/N)")
    feedback_modified_date = Column(TIMESTAMP, comment="수정일자")
