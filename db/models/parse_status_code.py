from sqlalchemy import Column
from sqlalchemy.dialects.oracle import NUMBER, VARCHAR2

from db.base import Base


class ParseStatusCode(Base):
    """파싱상태코드 테이블."""

    __tablename__ = "parse_status_code"

    parse_status_code = Column(NUMBER(5), primary_key=True, nullable=False, comment="파싱상태코드")
    # 원본 정의서의 컬럼명 오타(starus) 그대로 유지
    parse_starus_message = Column(VARCHAR2(50), nullable=False, comment="파싱상태메세지")
