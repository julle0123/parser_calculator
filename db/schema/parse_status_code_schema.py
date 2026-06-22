from pydantic import BaseModel, ConfigDict


class ParseStatusCodeSchema(BaseModel):
    """파싱상태코드 스키마."""

    model_config = ConfigDict(from_attributes=True)

    parse_status_code: int
    parse_starus_message: str  # 원본 정의서 오타(starus) 유지
