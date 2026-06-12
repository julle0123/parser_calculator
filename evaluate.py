"""
업스테이지 Document Parse API 응답 품질 평가 CLI

사용법:
    python evaluate.py <json파일> [--pages N] [--output result.json]

예시:
    python evaluate.py parsed.json --pages 10
    python evaluate.py parsed.json --output result.json
"""

import argparse
import json
import sys
import io
from pathlib import Path

# Windows 콘솔 한글 출력
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from scorer import evaluate, compute_zscore


def _print_summary(result: dict) -> None:
    score = result["score"]
    grade = result["grade"]
    desc = result["grade_description"]

    print(f"\n{'='*50}")
    print(f"  최종 점수 : {score} / 100")
    print(f"  등급      : Grade {grade}  ({desc})")
    print(f"{'='*50}")

    print("\n[컴포넌트별 점수]")
    for name, comp in result["components"].items():
        print(f"  {name:<20} {comp['score']:>5} / {comp['max_score']}")

    print(f"\n[주의] {result['caution']}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="업스테이지 Document Parse API 응답 품질 평가"
    )
    parser.add_argument("input", help="파싱 결과 JSON 파일 경로")
    parser.add_argument(
        "--pages", type=int, default=None,
        help="PDF 실제 총 페이지 수 (미입력 시 elements에서 자동 추론)"
    )
    parser.add_argument(
        "--output", default=None,
        help="상세 결과를 저장할 JSON 파일 경로 (선택)"
    )
    parser.add_argument(
        "--history", default=None,
        help="누적 점수 JSON 파일 경로 — z-score 계산용 (선택)"
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

    result = evaluate(parsed, total_pages=args.pages)

    # z-score (히스토리 있을 때만)
    if args.history:
        history_path = Path(args.history)
        if history_path.exists():
            try:
                history: list[float] = json.loads(history_path.read_text(encoding="utf-8"))
                z = compute_zscore(result["score"], history)
                result["zscore"] = z
                result["zscore_note"] = (
                    "이상 문서 의심 (z < -2.0)" if z is not None and z < -2.0
                    else "정상 범위"
                )
            except Exception as e:
                result["zscore_error"] = str(e)

    _print_summary(result)

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"상세 결과 저장 완료: {output_path}")


if __name__ == "__main__":
    main()
