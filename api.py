"""
파싱 품질 평가 API

실행:
    uvicorn api:app --reload

엔드포인트:
    POST /evaluate        — 단건 JSON 파일 평가
    POST /evaluate/batch  — 복수 JSON 파일 일괄 평가
    GET  /health          — 헬스체크
"""

from fastapi import FastAPI

from routers import batch, evaluate, health

app = FastAPI(
    title="Document Parse Quality API",
    description="업스테이지 Document Parse API 결과의 파싱 실패 징후 감지",
    version="1.0.0",
)

app.include_router(evaluate.router)
app.include_router(batch.router)
app.include_router(health.router)
