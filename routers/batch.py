import json

from fastapi import APIRouter, File, UploadFile

from schemas.evaluate import BatchFileResult, BatchResponse, CheckResult
from scorer import evaluate as run_evaluate

router = APIRouter(prefix="/evaluate", tags=["evaluate"])


@router.post(
    "/batch",
    response_model=BatchResponse,
    summary="파서 결과 일괄 평가",
    description="JSON 파일을 여러 개 업로드하면 파일별 점수를 일괄 반환합니다.",
)
async def evaluate_batch(
    files: list[UploadFile] = File(..., description="업스테이지 파서 결과 JSON 파일 목록"),
) -> BatchResponse:
    results: list[BatchFileResult] = []

    for f in files:
        raw = await f.read()
        try:
            parsed = json.loads(raw)
            r = run_evaluate(parsed)
            results.append(
                BatchFileResult(
                    filename=f.filename or "",
                    score=r["score"],
                    grade=r["grade"],
                    total_deduction=r["total_deduction"],
                    checks=[CheckResult(**c) for c in r["checks"]],
                ) #type: ignore
            )
        except Exception as e:
            results.append(
                BatchFileResult(
                    filename=f.filename or "",
                    score=None,
                    grade="ERR",
                    total_deduction=0,
                    checks=[],
                    error=str(e),
                )
            )

    return BatchResponse(total=len(results), results=results)
