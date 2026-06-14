import json
import sys
import os
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from scorer import evaluate

skip = {"result.json", "result_씨스퀘어.json", "result_KB.json", "batch_run.py"}

files = sorted([
    p for p in Path(".").glob("*.json")
    if p.name not in skip and not p.name.startswith("result_")
])

results = []
for path in files:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
        r = evaluate(parsed)
        results.append({
            "file": path.name,
            "score": r["score"],
            "grade": r["grade"],
            "deduction": r["total_deduction"],
            "checks": r["checks"],
        })
    except Exception as e:
        results.append({
            "file": path.name,
            "score": None,
            "grade": "ERR",
            "deduction": 0,
            "error": str(e),
            "checks": [],
        })

results.sort(key=lambda x: (x["score"] or 999))

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
    print(f"\n  총 {len(results)}개 문서  |  최고 {max(scores):.1f}  최저 {min(scores):.1f}  평균 {sum(scores)/len(scores):.1f}")

print()
