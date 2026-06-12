"""
① OCR 신뢰도 컴포넌트 (최대 35점)

업스테이지 파서가 제공하는 유일한 직접 품질 신호.
words[].confidence 분포를 분석해 OCR 품질을 수치화.

- 평균 confidence: 전반적 OCR 품질 (18점)
- 저신뢰 단어 비율: 오인식 단어 빈도 (17점)
- p10 confidence: 하위 10% 백분위수 — 점수 반영 없이 details에만 제공.
  평균이 높아도 국소적 실패 구간이 있는지 확인하는 참고 지표.

한계: confidence는 "이 글자가 맞다는 확신"이지 "실제로 맞다"는 보장이 아님.
"""

import numpy as np


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

    confidences = np.array([w.get("confidence", 0.0) for w in all_words], dtype=float)
    avg_conf = float(np.mean(confidences))
    low_conf_ratio = float(np.mean(confidences < 0.85))
    p10_conf = float(np.percentile(confidences, 10))

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
        "avg_confidence_score": avg_score,
        "low_conf_ratio": round(low_conf_ratio, 4),
        "low_conf_count": int(np.sum(confidences < 0.85)),
        "low_conf_ratio_score": low_score,
        "p10_confidence": round(p10_conf, 4),  # 참고용 — 점수 미반영
    }
    return result
