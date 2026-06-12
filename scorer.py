"""
최종 점수 산출 및 등급 판정.

4개 컴포넌트 점수를 합산하고 Grade를 부여.
문서 간 상대 비교를 위한 z-score 계산 기능 포함.
"""

import math
from components.confidence import score_confidence
from components.structure import score_structure
from components.text_quality import score_text_quality
from components.domain import score_domain

# (최소점수 이상이면 해당 등급)
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


def _infer_total_pages(elements: list[dict]) -> int:
    pages = [el.get("page", 0) for el in elements if el.get("page")]
    return max(pages) if pages else 1


def evaluate(
    parsed: dict,
    total_pages: int | None = None,
    custom_patterns: dict[str, str] | None = None,
) -> dict:
    """
    Args:
        parsed: 업스테이지 Document Parse API 응답 JSON (dict)
        total_pages: PDF 실제 총 페이지 수. None이면 elements에서 추론.
        custom_patterns: 도메인 패턴 교체/추가. key=이름, value=정규식.

    Returns:
        score, grade, components 상세, caution 포함 dict
    """
    elements = parsed.get("elements", [])

    if total_pages is None:
        total_pages = _infer_total_pages(elements)

    components = [
        score_confidence(elements),
        score_structure(elements, total_pages),
        score_text_quality(elements),
        score_domain(elements, custom_patterns),
    ]

    total = sum(c["score"] for c in components)
    total = max(0.0, min(100.0, float(total)))
    grade, grade_desc = _get_grade(total)

    return {
        "score": round(total, 2),
        "grade": grade,
        "grade_description": grade_desc,
        "components": {c["component"]: c for c in components},
        "caution": _CAUTION,
    }


def compute_zscore(score: float, history: list[float]) -> float | None:
    """
    누적 문서 점수 리스트 대비 현재 문서의 z-score 계산.
    z < -2.0 이면 이상 문서로 판단.
    최소 30개 이상 누적 후 사용 권장.

    Returns:
        z-score (float) 또는 None (샘플 부족)
    """
    if len(history) < 30:
        return None

    mean = sum(history) / len(history)
    variance = sum((x - mean) ** 2 for x in history) / len(history)
    stdev = math.sqrt(variance)

    if stdev == 0:
        return 0.0

    return round((score - mean) / stdev, 4)
