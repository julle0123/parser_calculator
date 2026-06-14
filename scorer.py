"""
감점 방식 점수 산출 및 등급 판정.

100점에서 시작해 체크별 감점을 합산.
문서 특성(words 존재, 한국어 여부 등)에 따라 적용 체크가 자동 결정됨.
"""

import math
from components.confidence import score_confidence
from components.structure import score_structure
from components.text_quality import score_text_quality
from components.completeness import score_completeness

_GRADE_TABLE = [
    (85, "A", "정상 처리"),
    (70, "B", "주의 — 재확인 권고"),
    (50, "C", "경고 — 파싱 재시도 권장"),
    (0,  "D", "실패 — 처리 보류"),
]

_CAUTION = (
    "이 점수는 파싱 실패 징후를 감지하는 필터입니다. "
    "Grade A = 명백한 실패 없음 (내용 정확성 보장 아님). "
    "숫자 오인식, 문장 일부 누락 등은 이 점수로 감지되지 않습니다."
)


def _get_grade(score: float) -> tuple[str, str]:
    for threshold, grade, desc in _GRADE_TABLE:
        if score >= threshold:
            return grade, desc
    return "D", "실패 — 처리 보류"


def evaluate(
    parsed: dict,
    total_pages: int | None = None,
) -> dict:
    """
    Args:
        parsed: 업스테이지 Document Parse API 응답 JSON (dict)
        total_pages: PDF 실제 총 페이지 수.
                     None이면 page_coverage 체크 skip.

    Returns:
        score, grade, checks 상세, caution 포함 dict
    """
    elements = parsed.get("elements", [])

    all_checks: list[dict] = []
    all_checks.extend(score_confidence(elements))
    all_checks.extend(score_structure(elements, total_pages))
    all_checks.extend(score_text_quality(elements))
    all_checks.extend(score_completeness(elements))

    total_deduction = sum(c["deduction"] for c in all_checks)
    score = max(0.0, min(100.0, 100.0 + float(total_deduction)))
    grade, grade_desc = _get_grade(score)

    return {
        "score": round(score, 2),
        "grade": grade,
        "grade_description": grade_desc,
        "total_deduction": total_deduction,
        "checks": all_checks,
        "caution": _CAUTION,
    }


def compute_zscore(score: float, history: list[float]) -> float | None:
    """
    누적 문서 점수 리스트 대비 현재 문서의 z-score 계산.
    z < -2.0 이면 이상 문서로 판단.
    최소 30개 이상 누적 후 사용 권장.
    """
    if len(history) < 30:
        return None

    mean = sum(history) / len(history)
    variance = sum((x - mean) ** 2 for x in history) / len(history)
    stdev = math.sqrt(variance)

    if stdev == 0:
        return 0.0

    return round((score - mean) / stdev, 4)
