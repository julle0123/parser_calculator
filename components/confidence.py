"""
OCR 신뢰도 감점 체크 (최대 -35점)

words[].confidence 분포를 분석. words 데이터 없으면 두 체크 모두 skip.

- ocr_avg_confidence: 전반적 OCR 품질 (최대 -18점)
- ocr_low_conf_ratio: 오인식 단어 빈도 (최대 -17점)

한계: confidence는 "이 글자가 맞다는 확신"이지 "실제로 맞다"는 보장이 아님.
"""

import numpy as np


def score_confidence(elements: list[dict]) -> list[dict]:
    # 모든 element의 words 배열을 평탄화. page 정보는 낮은 신뢰도 샘플 위치 표시용.
    word_page_pairs = [
        (el.get("page"), w)
        for el in elements
        for w in el.get("words", [])
    ]

    # words가 아예 없으면 (이미지가 아닌 디지털 PDF 등) 두 체크 모두 적용 불가
    if not word_page_pairs:
        return [
            {
                "check": "ocr_avg_confidence",
                "applicable": False,
                "skip_reason": "words 데이터 없음",
                "deduction": 0,
                "detail": {},
            },
            {
                "check": "ocr_low_conf_ratio",
                "applicable": False,
                "skip_reason": "words 데이터 없음",
                "deduction": 0,
                "detail": {},
            },
        ]

    confidences = np.array([w.get("confidence", 0.0) for _, w in word_page_pairs], dtype=float)
    avg_conf = float(np.mean(confidences))           # 전체 평균 신뢰도 (0~1)
    low_conf_ratio = float(np.mean(confidences < 0.85))  # 신뢰도 0.85 미만 단어 비율
    p10_conf = float(np.percentile(confidences, 10))     # 하위 10% 신뢰도 (참고용)

    # 평균 신뢰도 구간별 감점: 97% 이상이면 정상, 그 아래로 내려갈수록 감점 증가
    if avg_conf >= 0.97:
        avg_deduction = 0
    elif avg_conf >= 0.94:
        avg_deduction = -5
    elif avg_conf >= 0.90:
        avg_deduction = -10
    else:
        avg_deduction = -18

    # 저신뢰도 단어 비율 구간별 감점: 3% 이하면 정상, 많을수록 감점 증가
    if low_conf_ratio <= 0.03:
        low_deduction = 0
    elif low_conf_ratio <= 0.08:
        low_deduction = -6
    elif low_conf_ratio <= 0.15:
        low_deduction = -12
    else:
        low_deduction = -17

    # 신뢰도가 낮은 단어를 최대 5개 추출 (리포트 시 어느 단어가 문제인지 표시용)
    low_conf_samples = sorted(
        [
            {
                "page": page,
                "text": (w.get("text") or w.get("word") or "")[:20],
                "confidence": round(float(w.get("confidence", 0)), 4),
            }
            for page, w in word_page_pairs
            if float(w.get("confidence", 0)) < 0.85
        ],
        key=lambda x: x["confidence"],
    )[:5]

    avg_detail: dict = {
        "total_words": len(confidences),
        "avg_confidence": round(avg_conf, 4),
        "p10_confidence": round(p10_conf, 4),  # 참고용 — 점수 미반영
    }
    low_detail: dict = {
        "low_conf_ratio": round(low_conf_ratio, 4),
        "low_conf_count": int(np.sum(confidences < 0.85)),
        "threshold": 0.85,
    }
    if low_conf_samples:
        avg_detail["low_conf_samples"] = low_conf_samples
        low_detail["low_conf_samples"] = low_conf_samples

    return [
        {
            "check": "ocr_avg_confidence",
            "applicable": True,
            "deduction": avg_deduction,
            "detail": avg_detail,
        },
        {
            "check": "ocr_low_conf_ratio",
            "applicable": True,
            "deduction": low_deduction,
            "detail": low_detail,
        },
    ]
