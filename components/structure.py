"""
② 구조 무결성 컴포넌트 (최대 25점)

파싱 결과의 기술적 완전성 검증.
내용 정확성은 알 수 없으나, 명백한 구조적 실패는 감지 가능.

- 페이지 커버리지: element 없는 페이지 탐지 (10점)
- 좌표 유효성: 정규화 범위(0~1) 벗어난 bounding box 탐지 (8점)
- 표 구조: HTML table 행별 셀 수 불일치 탐지 (7점)

bs4(BeautifulSoup)로 malformed HTML에도 안정적으로 표 파싱.
"""

import statistics
from bs4 import BeautifulSoup


def _get_row_cell_counts(html: str) -> list[int]:
    """
    HTML table에서 행별 셀 수 추출 (colspan 반영).
    bs4로 파싱해 malformed HTML에도 안정적으로 동작.
    """
    try:
        soup = BeautifulSoup(html, "html.parser")
        counts = []
        for row in soup.find_all("tr"):
            cell_count = 0
            for cell in row.find_all(["td", "th"]):
                colspan = cell.get("colspan", 1)
                try:
                    cell_count += int(colspan)
                except (ValueError, TypeError):
                    cell_count += 1
            if cell_count > 0:
                counts.append(cell_count)
        return counts
    except Exception:
        return []


def _is_table_structure_valid(html: str) -> bool:
    """
    True = 정상, False = 구조 이상.
    행별 셀 수의 표준편차가 평균의 50% 초과 시 이상으로 판단.
    """
    counts = _get_row_cell_counts(html)
    if len(counts) < 2:
        return True

    mean = statistics.mean(counts)
    if mean == 0:
        return True

    stdev = statistics.stdev(counts)
    return (stdev / mean) <= 0.5


def _is_valid_coord(coord: dict) -> bool:
    x = coord.get("x", -1)
    y = coord.get("y", -1)
    return (
        isinstance(x, (int, float))
        and isinstance(y, (int, float))
        and 0.0 <= x <= 1.0
        and 0.0 <= y <= 1.0
    )


def score_structure(elements: list[dict], total_pages: int) -> dict:
    result = {
        "component": "structure",
        "max_score": 25,
        "score": 0,
        "details": {},
    }

    if not elements:
        result["details"]["error"] = "elements 없음"
        return result

    # 페이지 커버리지 (10점)
    covered_pages = set(el.get("page") for el in elements if el.get("page"))
    empty_page_count = max(0, total_pages - len(covered_pages))
    empty_ratio = empty_page_count / total_pages if total_pages > 0 else 0.0

    if empty_ratio == 0.0:
        page_score = 10
    elif empty_ratio <= 0.05:
        page_score = 6
    else:
        page_score = 0

    # 좌표 유효성 (8점)
    invalid_coord_count = sum(
        1 for el in elements
        if el.get("coordinates") and any(
            not _is_valid_coord(c) for c in el["coordinates"]
        )
    )
    coord_invalid_ratio = invalid_coord_count / len(elements)

    if coord_invalid_ratio == 0.0:
        coord_score = 8
    elif coord_invalid_ratio <= 0.01:
        coord_score = 4
    else:
        coord_score = 0

    # 표 구조 (7점)
    table_elements = [el for el in elements if el.get("category") == "table"]
    broken_table_count = sum(
        1 for el in table_elements
        if not _is_table_structure_valid(el.get("content", {}).get("html", ""))
    )

    if not table_elements:
        table_score = 7
    else:
        broken_ratio = broken_table_count / len(table_elements)
        if broken_ratio == 0.0:
            table_score = 7
        elif broken_ratio <= 0.20:
            table_score = 4
        else:
            table_score = 0

    result["score"] = page_score + coord_score + table_score
    result["details"] = {
        "total_pages": total_pages,
        "covered_pages": len(covered_pages),
        "empty_page_count": empty_page_count,
        "empty_page_ratio": round(empty_ratio, 4),
        "page_coverage_score": page_score,
        "total_elements": len(elements),
        "invalid_coord_elements": invalid_coord_count,
        "coord_invalid_ratio": round(coord_invalid_ratio, 4),
        "coord_validity_score": coord_score,
        "total_tables": len(table_elements),
        "broken_tables": broken_table_count,
        "table_structure_score": table_score,
    }
    return result
