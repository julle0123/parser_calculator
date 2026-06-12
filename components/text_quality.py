"""
③ 텍스트 품질 컴포넌트 (최대 20점)

ground truth 없이 텍스트 자체의 품질 이상 징후를 감지.
내용이 정확한지는 알 수 없으나, 명백한 품질 저하는 탐지 가능.

- 한글 문자 비율: 한국 금융 문서에서 한글 비율이 낮으면 OCR 실패 간접 신호 (7점)
- 깨진 문자 감지: OCR 실패 대체 문자 및 한글 자모 단독 등장 탐지 (7점)
- html↔markdown 일관성: 동일 element의 두 포맷 간 텍스트 불일치 탐지 (6점)
"""

import re
from difflib import SequenceMatcher
from html.parser import HTMLParser

# 한글 완성형 음절 범위 (가-힣)
_KO_SYLLABLE_START = 0xAC00
_KO_SYLLABLE_END = 0xD7A3

# 한글 자모 범위 (ㄱ-ㅣ) — 단독 등장 시 OCR 깨짐 신호
_KO_JAMO_START = 0x3131
_KO_JAMO_END = 0x318E

# OCR 실패 시 자주 나타나는 대체/이상 문자
_GARBLED_CHARS = frozenset("□■口▪▫○●◇◆替〓々〒〓※▷▶◁◀")


class _TagStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str):
        self._parts.append(data)

    def get_text(self) -> str:
        return " ".join(self._parts)


def _strip_html(html: str) -> str:
    s = _TagStripper()
    try:
        s.feed(html)
        return s.get_text()
    except Exception:
        return html


def _strip_markdown(md: str) -> str:
    md = re.sub(r"#{1,6}\s*", "", md)
    md = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", md)
    md = re.sub(r"_{1,2}([^_]+)_{1,2}", r"\1", md)
    md = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", md)
    md = re.sub(r"[|]", " ", md)
    md = re.sub(r"^[\s\-:]+$", "", md, flags=re.MULTILINE)
    return " ".join(md.split())


def _is_korean_syllable(ch: str) -> bool:
    code = ord(ch)
    return _KO_SYLLABLE_START <= code <= _KO_SYLLABLE_END


def _is_korean_jamo(ch: str) -> bool:
    code = ord(ch)
    return _KO_JAMO_START <= code <= _KO_JAMO_END


def _is_garbled(ch: str) -> bool:
    return ch in _GARBLED_CHARS or _is_korean_jamo(ch)


def score_text_quality(elements: list[dict]) -> dict:
    result = {
        "component": "text_quality",
        "max_score": 20,
        "score": 0,
        "details": {},
    }

    all_chars: list[str] = []
    html_texts: list[str] = []
    md_texts: list[str] = []

    for el in elements:
        content = el.get("content", {})
        html = content.get("html", "")
        md = content.get("markdown", "")

        html_plain = _strip_html(html).strip()
        md_plain = _strip_markdown(md).strip()

        all_chars.extend(c for c in html_plain if not c.isspace())

        if html_plain and md_plain:
            html_texts.append(html_plain)
            md_texts.append(md_plain)

    # 한글 문자 비율 (7점)
    non_space_count = len(all_chars)
    if non_space_count >= 20:
        korean_count = sum(1 for c in all_chars if _is_korean_syllable(c))
        korean_ratio = korean_count / non_space_count

        if korean_ratio >= 0.50:
            korean_score = 7
        elif korean_ratio >= 0.30:
            korean_score = 4
        else:
            korean_score = 1
    else:
        korean_ratio = None
        korean_score = 7  # 텍스트 부족으로 평가 불가 → 감점 없음

    # 깨진 문자 감지 (7점)
    if non_space_count >= 20:
        garbled_count = sum(1 for c in all_chars if _is_garbled(c))
        garbled_ratio = garbled_count / non_space_count

        if garbled_ratio <= 0.005:
            garbled_score = 7
        elif garbled_ratio <= 0.010:
            garbled_score = 4
        else:
            garbled_score = 0
    else:
        garbled_ratio = None
        garbled_score = 7

    # html↔markdown 일관성 (6점)
    # 표 element는 두 포맷의 구조 차이가 크므로 포함해도 무방 (파이프 제거 후 비교)
    sample_pairs = list(zip(html_texts, md_texts))[:50]
    if sample_pairs:
        sims = [
            SequenceMatcher(None, h, m).ratio()
            for h, m in sample_pairs
            if h and m
        ]
        avg_sim = sum(sims) / len(sims) if sims else 1.0

        if avg_sim >= 0.90:
            consistency_score = 6
        elif avg_sim >= 0.70:
            consistency_score = 3
        else:
            consistency_score = 0
    else:
        avg_sim = None
        consistency_score = 6  # 비교 가능한 element 없으면 감점 없음

    result["score"] = korean_score + garbled_score + consistency_score
    result["details"] = {
        "total_non_space_chars": non_space_count,
        "korean_ratio": round(korean_ratio, 4) if korean_ratio is not None else "N/A",
        "korean_ratio_score": korean_score,
        "garbled_ratio": round(garbled_ratio, 4) if garbled_ratio is not None else "N/A",
        "garbled_score": garbled_score,
        "html_markdown_similarity": round(avg_sim, 4) if avg_sim is not None else "N/A",
        "html_markdown_consistency_score": consistency_score,
    }
    return result
