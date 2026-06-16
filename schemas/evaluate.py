from pydantic import BaseModel, Field


class CheckResult(BaseModel):
    check: str = Field(description="체크 항목 이름 (e.g. ocr_avg_confidence)")
    applicable: bool = Field(description="이 문서에 적용 여부")
    deduction: int = Field(description="감점 값 (0 이하)")
    detail: dict = Field(description="체크별 상세 수치")
    skip_reason: str | None = Field(None, description="applicable=False 일 때 skip 사유")


class EvaluateResponse(BaseModel):
    score: float = Field(description="최종 점수 (0~100)")
    grade: str = Field(description="등급 (A/B/C/D)")
    grade_description: str = Field(description="등급 설명")
    total_deduction: int = Field(description="총 감점 합계 (0 이하)")
    checks: list[CheckResult] = Field(description="체크 항목별 결과 목록")
    caution: str = Field(description="점수 해석 시 주의사항")


class BatchFileResult(BaseModel):
    filename: str = Field(description="업로드된 파일명")
    score: float | None = Field(description="최종 점수 (평가 실패 시 null)")
    grade: str = Field(description="등급 (A/B/C/D/ERR)")
    total_deduction: int = Field(description="총 감점 합계")
    checks: list[CheckResult] = Field(description="체크 항목별 결과 목록")
    error: str | None = Field(None, description="평가 실패 시 오류 메시지")


class BatchResponse(BaseModel):
    total: int = Field(description="평가 요청 파일 수")
    results: list[BatchFileResult] = Field(description="파일별 평가 결과")
