"""
① OCR 신뢰도 컴포넌트 (최대 35점)

업스테이지 파서가 제공하는 유일한 직접 품질 신호.
words[].confidence 분포를 분석해 OCR 품질을 수치화.

한계: confidence는 "이 글자가 맞다는 확신"이지 "실제로 맞다"는 보장이 아님.
"""


def score_confidence(elements: list[dict]) -> dict:
    all_words = []
    for el in elements:
        all_words.extend(el.get("words", []))

    result = {
        "component": "confidence",
        "max_score": 35,
        "score": 0,
        "details": {},
    }

    if not all_words:
        result["details"]["error"] = "words 데이터 없음"
        return result

    confidences = [w.get("confidence", 0.0) for w in all_words]
    avg_conf = sum(confidences) / len(confidences)
    low_conf_count = sum(1 for c in confidences if c < 0.85)
    low_conf_ratio = low_conf_count / len(confidences)

    # 평균 confidence (18점)
    if avg_conf >= 0.97:
        avg_score = 18
    elif avg_conf >= 0.94:
        avg_score = 13
    elif avg_conf >= 0.90:
        avg_score = 7
    else:
        avg_score = 0

    # 저신뢰 단어 비율 — confidence < 0.85 (17점)
    if low_conf_ratio <= 0.03:
        low_score = 17
    elif low_conf_ratio <= 0.08:
        low_score = 11
    elif low_conf_ratio <= 0.15:
        low_score = 5
    else:
        low_score = 0

    result["score"] = avg_score + low_score
    result["details"] = {
        "total_words": len(confidences),
        "avg_confidence": round(avg_conf, 4),
        "low_conf_count": low_conf_count,
        "low_conf_ratio": round(low_conf_ratio, 4),
        "avg_confidence_score": avg_score,
        "low_conf_ratio_score": low_score,
    }
    return result
