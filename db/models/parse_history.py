from sqlalchemy import Column, ForeignKey, Text
from sqlalchemy.dialects.oracle import CHAR, NUMBER, TIMESTAMP, VARCHAR2

from db.base import Base


class ParseHistory(Base):
    """파싱히스토리 테이블 — 복합 PK: pipeline_id + doc_id + parse_id."""

    __tablename__ = "parse_history"

    pipeline_id = Column(VARCHAR2(50), primary_key=True, nullable=False, comment="파이프라인ID")
    doc_id = Column(VARCHAR2(50), primary_key=True, nullable=False, comment="문서ID")
    parse_id = Column(VARCHAR2(50), primary_key=True, nullable=False, comment="파싱ID")
    doc_extension = Column(VARCHAR2(20), comment="문서확장자")
    # 정의서 타입: varchar2(50) — 날짜를 문자열로 저장
    parse_start_date = Column(VARCHAR2(50), comment="파싱시작일자")
    parse_end_date = Column(VARCHAR2(50), comment="파싱종료일자")
    parse_parameter = Column(Text, comment="파싱파라미터(JSON)")
    origin_doc_path = Column(VARCHAR2(50), nullable=False, comment="원본문서경로")
    parse_result_doc_path = Column(VARCHAR2(50), nullable=False, comment="파싱결과경로")
    parse_result_json = Column(Text, comment="파싱결과json")
    parse_result_html = Column(Text, comment="파싱결과html")
    parse_result_doc_format = Column(VARCHAR2(10), comment="결과파일포맷")
    parse_status_code = Column(NUMBER(5), ForeignKey("parse_status_code.parse_status_code"), comment="파싱결과코드")
    parse_status_yn = Column(CHAR(1), comment="파싱성공여부(Y/N)")
    parse_score = Column(NUMBER(5, 2), nullable=False, comment="파싱점수")
    parse_modified_yn = Column(CHAR(1), comment="수정여부(Y/N)")
    parse_modified_id = Column(VARCHAR2(20), comment="수정자ID")
    parse_modified_date = Column(TIMESTAMP, comment="수정일자")
    reparse_required = Column(CHAR(1), comment="재파싱여부(Y/N)")
    pii_detected = Column(CHAR(1), comment="PII검출여부(Y/N)")
    anonymize_type = Column(VARCHAR2(20), comment="비식별화방식")
