"""
업스테이지 Document Parse 응답 일괄 평가

사용법:
    python batch_run.py                          # 현재 디렉터리의 모든 JSON
    python batch_run.py ./results/               # 특정 디렉터리
    python batch_run.py ./results/ --output summary.json
    python batch_run.py ./results/ --output-dir scored/
    python batch_run.py ./results/ --output summary.json --report report.txt
"""

import argparse
import json
import sys
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from scorer import evaluate


_INTERNAL_SKIP = {"summary.json"}

_CHECK_KO = {
    "ocr_avg_confidence":   "OCR 평균 신뢰도",
    "ocr_low_conf_ratio":   "저신뢰 단어 비율",
    "page_coverage":        "페이지 커버리지",
    "coord_validity":       "좌표 유효성",
    "table_structure":      "표 구조 이상",
    "garbled_chars":        "깨진 문자",
    "html_md_consistency":  "HTML↔Markdown 불일치",
    "korean_ratio":         "한글 비율 저하",
    "empty_element_ratio":  "빈 블록 비율",
    "table_html_missing":   "표 HTML 누락",
    "word_fragmentation":   "단어 단편화",
}


def _is_result_file(name: str) -> bool:
    return name.startswith("result_") or name == "result.json"


def _format_deduction_human(check_name: str, detail: dict) -> list[str]:
    lines = []

    if check_name == "table_structure":
        for t in detail.get("broken_table_details", []):
            lines.append(f"      · {t['page']}페이지: {t['reason']}")

    elif check_name == "html_md_consistency":
        samples = detail.get("low_similarity_samples", [])
        if samples:
            lines.append(f"      · {samples[0]['reason']}")
            for s in samples:
                lines.append(
                    f"      · {s['page']}페이지 [{s['category']}]  "
                    f"일치율 {round(s['similarity']*100)}%"
                )
                lines.append(f"          원문(HTML): {s['html'][:55]}")
                lines.append(f"          변환(MD)  : {s['markdown'][:55]}")

    elif check_name == "garbled_chars":
        for g in detail.get("garbled_locations", []):
            chars = " ".join(g["chars"])
            lines.append(
                f"      · {g['page']}페이지 [{g['category']}]에서 "
                f"깨진 문자 발견: {chars}"
            )
            lines.append(f"          해당 내용: {g['snippet'][:55]}")

    elif check_name in ("ocr_avg_confidence", "ocr_low_conf_ratio"):
        samples = detail.get("low_conf_samples", [])
        if samples:
            lines.append(
                "      OCR 인식 신뢰도가 낮은 단어 예시 "
                "(신뢰도가 낮을수록 오인식 가능성 높음):"
            )
            for w in samples:
                lines.append(
                    f"      · {w['page']}페이지  '{w['text']}'  "
                    f"신뢰도 {round(w['confidence']*100, 1)}%"
                )

    elif check_name == "page_coverage":
        total = detail.get("total_pages")
        empty = detail.get("empty_page_count")
        lines.append(
            f"      · 전체 {total}페이지 중 {empty}페이지에 "
            f"파싱된 내용이 없습니다. 해당 페이지가 통째로 누락되었을 수 있습니다."
        )

    elif check_name == "empty_element_ratio":
        total = detail.get("total_elements")
        empty = detail.get("empty_elements")
        lines.append(
            f"      · 파싱된 블록 {total}개 중 {empty}개가 "
            f"텍스트가 전혀 없는 빈 상태입니다."
        )

    elif check_name == "table_html_missing":
        total = detail.get("total_tables")
        missing = detail.get("html_missing")
        lines.append(
            f"      · 표 {total}개 중 {missing}개에 구조 정보(HTML)가 없습니다. "
            f"해당 표의 행·열 구조가 소실되었을 수 있습니다."
        )

    elif check_name == "word_fragmentation":
        avg = detail.get("avg_word_length")
        lines.append(
            f"      · 단어 평균 길이가 {avg}자로, 기준(2.0자)보다 짧습니다. "
            f"단어가 낱글자 단위로 쪼개져 인식된 것으로 보입니다."
        )

    elif check_name == "korean_ratio":
        ratio = round(detail.get("korean_ratio", 0) * 100, 1)
        lines.append(
            f"      · 문서 내 한글 비율이 {ratio}%로 낮습니다. "
            f"한국어 문서인데 한글이 다른 문자로 치환되거나 누락되었을 수 있습니다."
        )

    return lines


def _build_report(results: list[dict], scores: list[float]) -> str:
    lines = []
    lines.append("=" * 64)
    lines.append("  업스테이지 Document Parse — 파싱 품질 평가 보고서")
    lines.append("=" * 64)
    lines.append("")

    normal = [r for r in results if r["score"] == 100.0]
    deducted = [r for r in results if r["score"] is not None and r["score"] < 100.0]
    errors = [r for r in results if r["grade"] == "ERR"]

    lines.append("[ 전체 요약 ]")
    lines.append(f"  평가 문서 수  : {len(results)}개")
    if scores:
        lines.append(f"  최고점        : {max(scores):.1f}점")
        lines.append(f"  최저점        : {min(scores):.1f}점")
        lines.append(f"  평균          : {sum(scores)/len(scores):.1f}점")
    lines.append(f"  감점 없음     : {len(normal)}개")
    lines.append(f"  감점 발생     : {len(deducted)}개")
    if errors:
        lines.append(f"  평가 실패     : {len(errors)}개")
    lines.append("")

    # 등급별 분포
    grade_counts: dict[str, int] = {}
    for r in results:
        if r["grade"] != "ERR":
            grade_counts[r["grade"]] = grade_counts.get(r["grade"], 0) + 1
    if grade_counts:
        lines.append("[ 등급 분포 ]")
        for g in ["A", "B", "C", "D"]:
            if g in grade_counts:
                label = {"A": "정상", "B": "주의", "C": "경고", "D": "실패"}[g]
                lines.append(f"  Grade {g} ({label}) : {grade_counts[g]}개")
        lines.append("")

    if not deducted and not errors:
        lines.append("  모든 문서 감점 없음 — 명백한 파싱 실패 징후 없음")
        lines.append("")
        lines.append("=" * 64)
        lines.append("  주의: 이 결과는 구조적 파싱 실패 징후를 감지한 것입니다.")
        lines.append("        숫자 오인식, 문장 일부 누락 등은 이 시스템으로")
        lines.append("        감지되지 않습니다.")
        lines.append("=" * 64)
        return "\n".join(lines)

    lines.append("[ 감점 발생 문서 상세 ]")
    lines.append("")

    for i, r in enumerate(deducted, 1):
        grade_desc = {"A": "정상", "B": "주의 — 재확인 권고",
                      "C": "경고 — 재시도 권장", "D": "실패 — 처리 보류"}.get(r["grade"], "")
        lines.append(f"  {i}. {r['file']}")
        lines.append(f"     점수: {r['score']}점  Grade {r['grade']} ({grade_desc})")
        lines.append(f"     총 감점: {r['deduction']}점")
        lines.append("")

        for c in r["checks"]:
            if c["deduction"] >= 0:
                continue
            ko_name = _CHECK_KO.get(c["check"], c["check"])
            lines.append(f"    ▸ {ko_name} ({c['deduction']}점)")
            detail_lines = _format_deduction_human(c["check"], c.get("detail", {}))
            lines.extend(detail_lines)
            lines.append("")

        lines.append("  " + "-" * 60)
        lines.append("")

    if errors:
        lines.append("[ 평가 실패 문서 ]")
        for r in errors:
            lines.append(f"  - {r['file']}: {r.get('error', '')}")
        lines.append("")

    lines.append("=" * 64)
    lines.append("  주의: 이 결과는 구조적 파싱 실패 징후를 감지한 것입니다.")
    lines.append("        숫자 오인식, 문장 일부 누락 등은 이 시스템으로")
    lines.append("        감지되지 않습니다.")
    lines.append("=" * 64)

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="업스테이지 Document Parse API 응답 일괄 평가"
    )
    parser.add_argument(
        "directory", nargs="?", default=".",
        help="평가할 JSON 파일이 있는 디렉터리 (기본: 현재 디렉터리)"
    )
    parser.add_argument(
        "--output", default=None,
        help="배치 요약 결과를 저장할 JSON 파일 경로 (선택)"
    )
    parser.add_argument(
        "--output-dir", default=None,
        help="파일별 상세 결과를 저장할 디렉터리 (선택)"
    )
    parser.add_argument(
        "--report", default=None,
        help="사람이 읽기 쉬운 한국어 보고서 저장 경로 (선택, 예: report.txt)"
    )
    args = parser.parse_args()

    target_dir = Path(args.directory)
    if not target_dir.is_dir():
        print(f"[오류] 디렉터리를 찾을 수 없습니다: {target_dir}", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output_dir) if args.output_dir else None
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    files = sorted([
        p for p in target_dir.glob("*.json")
        if p.name not in _INTERNAL_SKIP and not _is_result_file(p.name)
    ])

    if not files:
        print(f"[정보] {target_dir} 에서 평가할 JSON 파일을 찾지 못했습니다.")
        return

    results = []
    for path in files:
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
            r = evaluate(parsed)

            entry = {
                "file": path.name,
                "score": r["score"],
                "grade": r["grade"],
                "deduction": r["total_deduction"],
                "checks": r["checks"],
            }
            results.append(entry)

            if output_dir:
                out_path = output_dir / f"result_{path.stem}.json"
                out_path.write_text(
                    json.dumps(r, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

        except Exception as e:
            results.append({
                "file": path.name,
                "score": None,
                "grade": "ERR",
                "deduction": 0,
                "error": str(e),
                "checks": [],
            })

    results.sort(key=lambda x: (x["score"] is None, x["score"] or 0))

    print(f"\n{'='*72}")
    print(f"  {'파일명':<46} {'점수':>6}  {'등급'}  {'감점 항목'}")
    print(f"{'='*72}")

    for r in results:
        if r["grade"] == "ERR":
            print(f"  {r['file'][:46]:<46} {'ERR':>6}  ERR   {r.get('error','')[:30]}")
            continue

        deducted = [c for c in r["checks"] if c["deduction"] < 0]
        deduct_str = ", ".join(
            f"{c['check']}({c['deduction']})" for c in deducted
        ) if deducted else "-"

        print(f"  {r['file'][:46]:<46} {r['score']:>6.1f}  {r['grade']}     {deduct_str}")

    print(f"{'='*72}")

    scores = [r["score"] for r in results if r["score"] is not None]
    if scores:
        print(
            f"\n  총 {len(results)}개 문서  |  "
            f"최고 {max(scores):.1f}  최저 {min(scores):.1f}  "
            f"평균 {sum(scores)/len(scores):.1f}"
        )

    if output_dir:
        print(f"  파일별 결과 저장: {output_dir}/")

    if args.output:
        def _build_file_entry(r: dict) -> dict:
            entry = {k: v for k, v in r.items() if k != "checks"}
            entry["deductions"] = [
                {"check": c["check"], "deduction": c["deduction"], "detail": c.get("detail", {})}
                for c in r.get("checks", [])
                if c["deduction"] < 0
            ]
            return entry

        summary = {
            "total": len(results),
            "scores": {
                "max": max(scores) if scores else None,
                "min": min(scores) if scores else None,
                "avg": round(sum(scores) / len(scores), 2) if scores else None,
            },
            "files": [_build_file_entry(r) for r in results],
        }
        output_path = Path(args.output)
        output_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"  배치 요약 저장: {output_path}")

    if args.report:
        report_text = _build_report(results, scores)
        report_path = Path(args.report)
        report_path.write_text(report_text, encoding="utf-8")
        print(f"  보고서 저장: {report_path}")

    print()


if __name__ == "__main__":
    main()
