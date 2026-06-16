"""
업스테이지 Document Parse API 응답 파싱 실패 징후 감지 CLI

사용법:
    python evaluate.py <json파일> [옵션]

예시:
    python evaluate.py parsed.json --pdf document.pdf
    python evaluate.py parsed.json --pages 10 --output result.json
    python evaluate.py parsed.json --history history.json
"""

import argparse
import json
import sys
import pdfplumber
from pathlib import Path
from typing import Any, cast

stdout = cast(Any, sys.stdout)

if stdout and hasattr(stdout, "reconfigure"):
    stdout.reconfigure(encoding="utf-8", errors="replace")

from scorer import evaluate, compute_zscore


def _get_page_count_from_pdf(pdf_path: str) -> int | None:
    # pdfplumber로 PDF를 열어 페이지 수만 추출. 실패 시 None 반환 → page_coverage 체크가 skip됨.
    try:
        with pdfplumber.open(pdf_path) as pdf:
            return len(pdf.pages)
    except Exception as e:
        print(f"[경고] PDF 페이지 수 추출 실패: {e}", file=sys.stderr)
        return None


def _format_check_detail(check: dict) -> str:
    # 체크마다 detail 구조가 달라서 이름별로 분기해 CLI 한 줄 요약 문자열로 변환.
    d = check.get("detail", {})
    name = check["check"]
    if name == "ocr_avg_confidence":
        return f"avg={d.get('avg_confidence', '?')}"
    if name == "ocr_low_conf_ratio":
        return f"ratio={d.get('low_conf_ratio', '?')}"
    if name == "page_coverage":
        return f"빈 {d.get('empty_page_count', '?')}/{d.get('total_pages', '?')}페이지"
    if name == "coord_validity":
        return f"이상 {d.get('invalid_coord_elements', '?')}/{d.get('total_elements', '?')}개"
    if name == "table_structure":
        return f"{d.get('broken_tables', '?')}/{d.get('total_tables', '?')} 구조 이상"
    if name == "garbled_chars":
        return f"ratio={d.get('garbled_ratio', '?')}"
    if name == "html_md_consistency":
        return f"유사도={d.get('avg_similarity', '?')}"
    if name == "korean_ratio":
        return f"ratio={d.get('korean_ratio', '?')}"
    if name == "empty_element_ratio":
        return f"빈 {d.get('empty_elements', '?')}/{d.get('total_elements', '?')}개"
    if name == "table_html_missing":
        return f"HTML 누락 {d.get('html_missing', '?')}/{d.get('total_tables', '?')}개"
    if name == "word_fragmentation":
        return f"평균 {d.get('avg_word_length', '?')}자/단어"
    return ""


def _print_summary(result: dict) -> None:
    # 체크 결과를 "감점 발생 / 통과 / 미적용(skip)" 세 그룹으로 분류해 터미널에 출력.
    score = result["score"]
    grade = result["grade"]
    desc = result["grade_description"]
    total_deduction = result.get("total_deduction", 0)

    print(f"\n{'='*56}")
    print(f"  최종 점수 : {score} / 100  (감점 합계: {total_deduction})")
    print(f"  등급      : Grade {grade}  ({desc})")

    if "zscore" in result and result["zscore"] is not None:
        z = result["zscore"]
        flag = "  ⚠ 이상 문서 의심" if z < -2.0 else ""
        print(f"  z-score   : {z}{flag}")

    print(f"{'='*56}")

    checks = result.get("checks", [])
    deducted = [c for c in checks if c["applicable"] and c["deduction"] < 0]
    passed   = [c for c in checks if c["applicable"] and c["deduction"] == 0]
    skipped  = [c for c in checks if not c["applicable"]]

    if deducted:
        print("\n[감점 내역]")
        for c in deducted:
            detail_str = _format_check_detail(c)
            print(f"  {c['check']:<30} {detail_str:<22} {c['deduction']:>4}")
        print(f"  {'─'*56}")
        print(f"  {'합계':<52} {total_deduction:>4}")
    else:
        print("\n[감점 없음 — 모든 적용 체크 통과]")

    if passed:
        print("\n[통과]")
        for c in passed:
            detail_str = _format_check_detail(c)
            print(f"  {c['check']:<30} {detail_str}")

    if skipped:
        print("\n[미적용 — 해당 없음]")
        for c in skipped:
            print(f"  {c['check']:<30} {c.get('skip_reason', '')}")

    print(f"\n[주의] {result['caution']}\n")


def main() -> None:
    # 실행 순서: JSON 로드 → 페이지 수 결정 → 평가 → (선택) z-score → 출력 → (선택) 파일 저장
    parser = argparse.ArgumentParser(
        description="업스테이지 Document Parse API 응답 파싱 실패 징후 감지"
    )
    parser.add_argument("input", help="파싱 결과 JSON 파일 경로")

    page_group = parser.add_mutually_exclusive_group()
    page_group.add_argument(
        "--pdf", default=None,
        help="원본 PDF 파일 경로 — 총 페이지 수 자동 추출 (pdfplumber 필요)"
    )
    page_group.add_argument(
        "--pages", type=int, default=None,
        help="PDF 총 페이지 수 직접 지정 (--pdf 미사용 시)"
    )

    parser.add_argument(
        "--output", default=None,
        help="상세 결과를 저장할 JSON 파일 경로 (선택)"
    )
    parser.add_argument(
        "--history", default=None,
        help="누적 점수 JSON 파일 경로 — z-score 계산용, 30개↑ 권장 (선택)"
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[오류] 파일을 찾을 수 없습니다: {input_path}", file=sys.stderr)
        sys.exit(1)

    try:
        parsed = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[오류] JSON 파싱 실패: {e}", file=sys.stderr)
        sys.exit(1)

    total_pages = None
    if args.pdf:
        total_pages = _get_page_count_from_pdf(args.pdf)
        if total_pages:
            print(f"[정보] PDF 페이지 수: {total_pages} (pdfplumber)")
    if total_pages is None and args.pages:
        total_pages = args.pages

    result = evaluate(parsed, total_pages=total_pages)

    if args.history:
        history_path = Path(args.history)
        if history_path.exists():
            try:
                history: list[float] = json.loads(
                    history_path.read_text(encoding="utf-8")
                )
                z = compute_zscore(result["score"], history)
                result["zscore"] = z
                result["zscore_note"] = (
                    "이상 문서 의심 (z < -2.0)" if z is not None and z < -2.0
                    else "정상 범위" if z is not None
                    else f"샘플 부족 ({len(history)}개, 30개 이상 권장)"
                )
            except Exception as e:
                result["zscore_error"] = str(e)

    _print_summary(result)

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"상세 결과 저장: {output_path}")


if __name__ == "__main__":
    main()
