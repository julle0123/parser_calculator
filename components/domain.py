"""
④ 도메인 패턴 컴포넌트 (최대 20점)

금융 문서에서 반드시 등장해야 할 패턴의 존재 여부와
추출된 값의 유효 범위를 검증.

ground truth 없이 내용에 가장 근접한 검증 수단.
단, 패턴 자체가 있어도 내용이 맞다는 보장은 아님.

- 필수 패턴 존재 여부: 5개 패턴 각 2점 (10점)
- 추출값 범위 유효성: 수수료%, 위험등급 범위 검증 (10점)

custom_patterns 인자로 문서 카테고리별 패턴 교체/추가 가능.
"""

import re

# 한국 금융 문서 공통 필수 패턴
DEFAULT_PATTERNS: dict[str, str] = {
    "date":   r"\d{4}년\s*\d{1,2}월",
    "ratio":  r"\d+\.?\d*\s*%",
    "amount": r"\d+[억만천]\s*원",
    "risk":   r"위험|리스크|손실",
    "fee":    r"수수료|보수|비용",
}

# 추출값 범위 유효성 규칙
_VALUE_RULES: dict[str, dict] = {
    "fee_pct": {
        "name": "수수료/비율(%)",
        "pattern": r"(\d+\.?\d*)\s*%",
        "valid_range": (0.0, 30.0),
        "max_score": 5,
    },
    "risk_grade": {
        "name": "위험등급",
        "pattern": r"([1-6])등급",
        "valid_range": (1, 6),
        "max_score": 5,
    },
}


def score_domain(elements: list[dict], custom_patterns: dict[str, str] | None = None) -> dict:
    result = {
        "component": "domain",
        "max_score": 20,
        "score": 0,
        "details": {},
    }

    patterns = {**DEFAULT_PATTERNS, **(custom_patterns or {})}

    # 전체 텍스트 수집 (markdown 기준)
    full_text = " ".join(
        el.get("content", {}).get("markdown", "")
        for el in elements
    )

    # 필수 패턴 존재 여부 (패턴당 2점, 최대 10점)
    pattern_results: dict[str, bool] = {}
    for name, pat in patterns.items():
        pattern_results[name] = bool(re.search(pat, full_text))

    found_count = sum(pattern_results.values())
    pattern_score = min(found_count * 2, 10)

    # 추출값 범위 유효성 (최대 10점)
    validation_results: dict[str, dict] = {}
    value_score_total = 0

    for key, rule in _VALUE_RULES.items():
        matches = re.findall(rule["pattern"], full_text)
        max_s = rule["max_score"]

        if not matches:
            # 해당 패턴 없음 — 문서 유형에 따라 없을 수 있으므로 절반 부여
            earned = max_s // 2
            value_score_total += earned
            validation_results[key] = {
                "name": rule["name"],
                "found": False,
                "note": "패턴 미발견 — 문서 유형 특성일 수 있음",
                "score": earned,
            }
            continue

        try:
            values = [float(m) for m in matches]
            lo, hi = rule["valid_range"]
            in_range_count = sum(1 for v in values if lo <= v <= hi)
            valid_ratio = in_range_count / len(values)

            if valid_ratio >= 0.90:
                earned = max_s
            elif valid_ratio >= 0.50:
                earned = max_s // 2
            else:
                earned = 0

            value_score_total += earned
            validation_results[key] = {
                "name": rule["name"],
                "found": True,
                "extracted_values": values[:10],
                "valid_range": list(rule["valid_range"]),
                "valid_ratio": round(valid_ratio, 4),
                "score": earned,
            }
        except Exception as e:
            validation_results[key] = {
                "name": rule["name"],
                "found": True,
                "error": str(e),
                "score": 0,
            }

    result["score"] = pattern_score + value_score_total
    result["details"] = {
        "pattern_results": pattern_results,
        "found_pattern_count": found_count,
        "pattern_score": pattern_score,
        "value_validations": validation_results,
        "value_validation_score": value_score_total,
    }
    return result
