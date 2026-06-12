"""
업스테이지 Document Parse API 응답 품질 평가 CLI

사용법:
    python evaluate.py <json파일> [옵션]

예시:
    python evaluate.py parsed.json --pdf document.pdf
    python evaluate.py parsed.json --pages 10 --output result.json
    python evaluate.py parsed.json --history history.json
"""

import argparse
import io
import json
import sys
from pathlib import Path

# Windows 콘솔 한글 출력
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from scorer import evaluate, compute_zscore

try:
    import pdfplumber
    _HAS_PDFPLUMBER = True
except ImportError:
    _HAS_PDFPLUMBER = False


def _get_page_count_from_pdf(pdf_path: str) -> int | None:
    if not _HAS_PDFPLUMBER:
        return None
    try:
        with pdfplumber.open(pdf_path) as pdf:
            return len(pdf.pages)
    except Exception as e:
        print(f"[경고] PDF 페이지 수 추출 실패: {e}", file=sys.stderr)
        return None


def _print_summary(result: dict) -> None:
    score = result["score"]
    grade = result["grade"]
    desc = result["grade_description"]

    print(f"\n{'='*52}")
    print(f"  최종 점수 : {score} / 100")
    print(f"  등급      : Grade {grade}  ({desc})")

    if "zscore" in result and result["zscore"] is not None:
        z = result["zscore"]
        flag = "  ⚠ 이상 문서 의심" if z < -2.0 else ""
        print(f"  z-score   : {z}{flag}")

    print(f"{'='*52}")

    print("\n[컴포넌트별 점수]")
    for name, comp in result["components"].items():
        print(f"  {name:<22} {comp['score']:>5} / {comp['max_score']}")

    print(f"\n[주의] {result['caution']}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="업스테이지 Document Parse API 응답 품질 평가"
    )
    parser.add_argument("input", help="파싱 결과 JSON 파일 경로")

    page_group = parser.add_mutually_exclusive_group()
    page_group.add_argument(
        "--pdf", default=None,
        help="원본 PDF 파일 경로 — 정확한 총 페이지 수 자동 추출 (pdfplumber 필요)"
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

    # 입력 JSON 로드
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[오류] 파일을 찾을 수 없습니다: {input_path}", file=sys.stderr)
        sys.exit(1)

    try:
        parsed = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[오류] JSON 파싱 실패: {e}", file=sys.stderr)
        sys.exit(1)

    # 총 페이지 수 결정
    total_pages = None
    if args.pdf:
        total_pages = _get_page_count_from_pdf(args.pdf)
        if total_pages:
            print(f"[정보] PDF 페이지 수: {total_pages} (pdfplumber)")
    if total_pages is None and args.pages:
        total_pages = args.pages

    # 평가 실행
    result = evaluate(parsed, total_pages=total_pages)

    # z-score (히스토리 있을 때)
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

    # 결과 저장
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"상세 결과 저장: {output_path}")


if __name__ == "__main__":
    main()
