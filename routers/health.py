from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", summary="헬스체크")
def health() -> dict:
    return {"status": "ok"}
