"""
감점 방식 점수 산출 및 등급 판정.

100점에서 시작해 체크별 감점을 합산.
문서 특성(words 존재, 한국어 여부 등)에 따라 적용 체크가 자동 결정됨.
"""

import math
from components import (
    BaseChecker,
    ConfidenceChecker,
    StructureChecker,
    TextQualityChecker,
    CompletenessChecker,
)

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
    # _GRADE_TABLE은 내림차순(85→70→50→0)으로 정렬되어 있어,
    # 점수 이상인 첫 번째 항목이 곧 해당 등급. 마지막 항목이 0이므로 항상 매칭됨.
    for threshold, grade, desc in _GRADE_TABLE:
        if score >= threshold:
            return grade, desc
    raise AssertionError(f"score {score} matched no grade — _GRADE_TABLE misconfigured")


class DocumentScorer:
    def __init__(
        self,
        total_pages: int | None = None,
        checkers: list[BaseChecker] | None = None,
    ):
        self._checkers: list[BaseChecker] = checkers or [
            ConfidenceChecker(),
            StructureChecker(total_pages=total_pages),
            TextQualityChecker(),
            CompletenessChecker(),
        ]

    def evaluate(self, parsed: dict) -> dict:
        """
        Args:
            parsed: 업스테이지 Document Parse API 응답 JSON (dict)

        Returns:
            score, grade, checks 상세, caution 포함 dict
        """
        elements = parsed.get("elements", [])

        all_checks: list[dict] = []
        for checker in self._checkers:
            all_checks.extend(checker.score(elements))

        # deduction은 모두 0 이하 값. 합산 후 100에서 빼면 최종 점수 (0 미만은 0으로 클램핑)
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

    @staticmethod
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
