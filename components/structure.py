"""
구조 무결성 감점 체크 (최대 -25점)

- page_coverage:   total_pages 제공 시만 적용 (최대 -10점)
- coord_validity:  항상 적용 (최대 -8점)
- table_structure: table element 존재 시만 적용 (최대 -7점)

bs4(BeautifulSoup)로 malformed HTML에도 안정적으로 표 파싱.
"""

import statistics
from bs4 import BeautifulSoup
from .base import BaseChecker


class StructureChecker(BaseChecker):
    def __init__(self, total_pages: int | None = None):
        self.total_pages = total_pages

    def score(self, elements: list[dict]) -> list[dict]:
        # 세 가지 구조 체크(페이지 커버리지 → 좌표 유효성 → 표 구조)를 순서대로 실행해 리스트로 반환.
        checks = []

        # --- 페이지 커버리지: total_pages를 알아야만 "빠진 페이지"를 계산할 수 있으므로 조건부 적용 ---
        if self.total_pages is not None and self.total_pages > 0:
            covered_pages = set(el.get("page") for el in elements if el.get("page"))
            empty_count = max(0, self.total_pages - len(covered_pages))
            empty_ratio = empty_count / self.total_pages

            if empty_ratio == 0.0:
                page_deduction = 0
            elif empty_ratio <= 0.05:
                page_deduction = -5
            else:
                page_deduction = -10

            checks.append({
                "check": "page_coverage",
                "applicable": True,
                "deduction": page_deduction,
                "detail": {
                    "total_pages": self.total_pages,
                    "covered_pages": len(covered_pages),
                    "empty_page_count": empty_count,
                    "empty_page_ratio": round(empty_ratio, 4),
                },
            })
        else:
            checks.append({
                "check": "page_coverage",
                "applicable": False,
                "skip_reason": "total_pages 미제공 (--pdf 또는 --pages 옵션 필요)",
                "deduction": 0,
                "detail": {},
            })

        # --- 좌표 유효성: coordinates 필드가 있는 element만 검사 (없는 element는 무시) ---
        if elements:
            invalid_count = sum(
                1 for el in elements
                if el.get("coordinates") and any(
                    not self._is_valid_coord(c) for c in el["coordinates"]
                )
            )
            invalid_ratio = invalid_count / len(elements)

            if invalid_ratio == 0.0:
                coord_deduction = 0
            elif invalid_ratio <= 0.01:
                coord_deduction = -4
            else:
                coord_deduction = -8

            checks.append({
                "check": "coord_validity",
                "applicable": True,
                "deduction": coord_deduction,
                "detail": {
                    "total_elements": len(elements),
                    "invalid_coord_elements": invalid_count,
                    "invalid_ratio": round(invalid_ratio, 4),
                },
            })
        else:
            checks.append({
                "check": "coord_validity",
                "applicable": False,
                "skip_reason": "elements 없음",
                "deduction": 0,
                "detail": {},
            })

        # --- 표 구조: category == "table"인 element가 있을 때만 적용 ---
        table_elements = [el for el in elements if el.get("category") == "table"]
        if table_elements:
            broken_info = []
            for el in table_elements:
                html = el.get("content", {}).get("html", "")
                counts = self._get_row_cell_counts(html)
                if len(counts) >= 2:
                    mean = statistics.mean(counts)
                    stdev = statistics.stdev(counts)
                    # CV(변동계수) = 표준편차 / 평균. 행 간 셀 수 편차가 클수록 구조 이상.
                    cv = stdev / mean if mean else 0
                    if cv > 0.5:
                        reason = self._describe_table_anomaly(counts)
                        broken_info.append({
                            "page": el.get("page"),
                            "cv": round(cv, 3),
                            "row_cell_counts": counts[:8],
                            "reason": reason,
                        })

            broken_count = len(broken_info)
            broken_ratio = broken_count / len(table_elements)

            if broken_ratio == 0.0:
                table_deduction = 0
            elif broken_ratio <= 0.20:
                table_deduction = -3
            else:
                table_deduction = -7

            checks.append({
                "check": "table_structure",
                "applicable": True,
                "deduction": table_deduction,
                "detail": {
                    "total_tables": len(table_elements),
                    "broken_tables": broken_count,
                    "broken_ratio": round(broken_ratio, 4),
                    "broken_table_details": broken_info,
                },
            })
        else:
            checks.append({
                "check": "table_structure",
                "applicable": False,
                "skip_reason": "table 유형 element 없음",
                "deduction": 0,
                "detail": {},
            })

        return checks

    @staticmethod
    def _get_row_cell_counts(html: str) -> list[int]:
        # 각 <tr>의 실질적인 열 수를 반환. colspan 속성을 반영해 병합 셀도 올바르게 계산.
        # 빈 행(셀 없는 tr)은 제외. HTML 파싱 오류 시 빈 리스트 반환.
        try:
            soup = BeautifulSoup(html, "html.parser")
            counts = []
            for row in soup.find_all("tr"):
                cell_count = 0
                for cell in row.find_all(["td", "th"]):
                    colspan = str(cell.get("colspan") or "1")
                    try:
                        cell_count += int(colspan)
                    except (ValueError, TypeError):
                        cell_count += 1
                if cell_count > 0:
                    counts.append(cell_count)
            return counts
        except Exception:
            return []

    @staticmethod
    def _describe_table_anomaly(counts: list[int]) -> str:
        # 셀 수가 가장 많은 행을 기준으로 "어느 행이, 나머지 행 평균 대비 얼마나 튀는지" 설명.
        # CV(변동계수) 이상 탐지에서 어떤 행이 원인인지 사람이 읽을 수 있는 형태로 변환.
        if not counts:
            return "표 구조를 파악할 수 없습니다."
        max_val = max(counts)
        max_idx = counts.index(max_val)
        rest = [c for i, c in enumerate(counts) if i != max_idx]
        avg_rest = round(sum(rest) / len(rest), 1) if rest else 0
        row_label = f"{max_idx + 1}번째 행"
        return (
            f"표의 {row_label}에 내용이 비정상적으로 몰려 있습니다. "
            f"({row_label}: {max_val}칸, 나머지 행 평균: {avg_rest}칸) "
            f"셀 병합이 많은 복잡한 표에서 파싱이 구조를 제대로 인식하지 못했을 가능성이 있습니다."
        )

    @staticmethod
    def _is_valid_coord(coord: dict) -> bool:
        # Upstage API는 좌표를 페이지 크기 대비 0~1 정규화 비율로 반환.
        # 이 범위를 벗어나거나 숫자가 아니면 파싱 오류로 간주.
        x = coord.get("x", -1)
        y = coord.get("y", -1)
        return (
            isinstance(x, (int, float))
            and isinstance(y, (int, float))
            and 0.0 <= x <= 1.0
            and 0.0 <= y <= 1.0
        )
