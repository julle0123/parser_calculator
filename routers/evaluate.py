import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from schemas.evaluate import EvaluateResponse
from scorer import DocumentScorer

router = APIRouter(prefix="/evaluate", tags=["evaluate"])


@router.post(
    "",
    response_model=EvaluateResponse,
    summary="파서 결과 단건 평가",
    description="업스테이지 Document Parse API 결과 JSON 파일을 업로드하면 파싱 실패 징후 점수를 반환합니다.",
)
async def evaluate_document(
    file: UploadFile = File(..., description="업스테이지 파서 결과 JSON 파일"),
    total_pages: int | None = Form(None, description="PDF 총 페이지 수 (미제공 시 page_coverage skip)"),
) -> EvaluateResponse:
    raw = await file.read()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"JSON 파싱 실패: {e}")

    result = DocumentScorer(total_pages=total_pages).evaluate(parsed)
    return EvaluateResponse(**result)
