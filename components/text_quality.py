"""
텍스트 품질 감점 체크 (최대 -20점)

- garbled_chars:      깨진 문자 비율 (최대 -7점, 텍스트 20자 이상 시)
- html_md_consistency: HTML↔MD 불일치 (최대 -6점, 양쪽 필드 있을 때)
- korean_ratio:       한글 비율 저하 (최대 -7점, 한국어 문서 감지 시)

한국어 문서 감지 기준: 전체 비공백 문자 중 한글 음절 비율 > 15%
"""

import re
from difflib import SequenceMatcher
from html.parser import HTMLParser

_KO_SYLLABLE_START = 0xAC00
_KO_SYLLABLE_END = 0xD7A3

# 한글 자모 범위 (ㄱ-ㅣ) — 단독 등장 시 OCR 깨짐 신호
_KO_JAMO_START = 0x3131
_KO_JAMO_END = 0x318E

# OCR 실패 시 나타나는 대체/이상 문자 (※ 제외 — 한국 문서에서 정상 사용)
_GARBLED_CHARS = frozenset("□■口▪▫○●◇◆替〓々〒▷▶◁◀")

_KOREAN_DOC_THRESHOLD = 0.15  # 이 비율 초과 시 한국어 문서로 간주


def _describe_consistency_diff(html: str, md: str) -> str:
    has_tag_in_md = bool(re.search(r"<[a-zA-Z]", md))
    if has_tag_in_md:
        return (
            "HTML 버전과 Markdown 버전의 내용이 다르게 처리되었습니다. "
            "Markdown에 코드 태그가 텍스트로 그대로 남아 있어 "
            "파싱 과정에서 해당 요소를 Markdown 형식으로 변환하지 못한 것입니다."
        )
    if len(html) > 0 and len(md) / max(len(html), 1) < 0.5:
        return (
            "Markdown 버전의 내용이 HTML 버전보다 현저히 짧습니다. "
            "Markdown 변환 과정에서 일부 내용이 누락되었을 가능성이 있습니다."
        )
    if len(md) > 0 and len(html) / max(len(md), 1) < 0.5:
        return (
            "HTML 버전의 내용이 Markdown 버전보다 현저히 짧습니다. "
            "HTML 변환 과정에서 일부 내용이 누락되었을 가능성이 있습니다."
        )
    return (
        "HTML 버전과 Markdown 버전의 텍스트 내용이 일치하지 않습니다. "
        "같은 내용을 두 형식으로 표현한 것이므로 동일해야 합니다."
    )


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


def score_text_quality(elements: list[dict]) -> list[dict]:
    all_chars: list[str] = []
    garbled_locations: list[dict] = []
    pair_details: list[tuple] = []

    for el in elements:
        content = el.get("content", {})
        html_plain = _strip_html(content.get("html", "")).strip()
        md_plain = _strip_markdown(content.get("markdown", "")).strip()
        page = el.get("page")
        category = el.get("category", "")

        non_space = [c for c in html_plain if not c.isspace()]
        all_chars.extend(non_space)

        garbled_in_el = [c for c in non_space if _is_garbled(c)]
        if garbled_in_el:
            garbled_locations.append({
                "page": page,
                "category": category,
                "chars": list(dict.fromkeys(garbled_in_el))[:5],
                "snippet": html_plain[:80],
            })

        if html_plain and md_plain:
            sim = SequenceMatcher(None, html_plain, md_plain).ratio()
            pair_details.append((sim, page, category, html_plain, md_plain))

    checks = []
    non_space_count = len(all_chars)

    if non_space_count >= 20:
        garbled_count = sum(1 for c in all_chars if _is_garbled(c))
        garbled_ratio = garbled_count / non_space_count

        if garbled_ratio <= 0.005:
            garbled_deduction = 0
        elif garbled_ratio <= 0.010:
            garbled_deduction = -4
        else:
            garbled_deduction = -7

        detail: dict = {
            "garbled_ratio": round(garbled_ratio, 4),
            "garbled_count": garbled_count,
            "total_chars": non_space_count,
        }
        if garbled_count > 0:
            detail["garbled_locations"] = garbled_locations[:5]

        checks.append({
            "check": "garbled_chars",
            "applicable": True,
            "deduction": garbled_deduction,
            "detail": detail,
        })
    else:
        checks.append({
            "check": "garbled_chars",
            "applicable": False,
            "skip_reason": f"텍스트 부족 ({non_space_count}자, 20자 미만)",
            "deduction": 0,
            "detail": {},
        })

    if pair_details:
        sampled = pair_details[:50]
        sims = [s for s, *_ in sampled]
        avg_sim = sum(sims) / len(sims)

        if avg_sim >= 0.90:
            consistency_deduction = 0
        elif avg_sim >= 0.70:
            consistency_deduction = -3
        else:
            consistency_deduction = -6

        consistency_detail: dict = {
            "avg_similarity": round(avg_sim, 4),
            "sample_pairs": len(sampled),
        }
        if consistency_deduction < 0:
            worst = sorted(sampled, key=lambda x: x[0])[:5]
            consistency_detail["low_similarity_samples"] = [
                {
                    "page": page,
                    "category": cat,
                    "similarity": round(sim, 3),
                    "html": h[:80],
                    "markdown": m[:80],
                    "reason": _describe_consistency_diff(h, m),
                }
                for sim, page, cat, h, m in worst
            ]

        checks.append({
            "check": "html_md_consistency",
            "applicable": True,
            "deduction": consistency_deduction,
            "detail": consistency_detail,
        })
    else:
        checks.append({
            "check": "html_md_consistency",
            "applicable": False,
            "skip_reason": "HTML 또는 markdown 필드 없음",
            "deduction": 0,
            "detail": {},
        })

    if non_space_count >= 20:
        korean_count = sum(1 for c in all_chars if _is_korean_syllable(c))
        korean_ratio = korean_count / non_space_count

        if korean_ratio > _KOREAN_DOC_THRESHOLD:
            if korean_ratio >= 0.50:
                korean_deduction = 0
            elif korean_ratio >= 0.30:
                korean_deduction = -3
            else:
                korean_deduction = -7

            checks.append({
                "check": "korean_ratio",
                "applicable": True,
                "deduction": korean_deduction,
                "detail": {
                    "korean_ratio": round(korean_ratio, 4),
                    "korean_count": korean_count,
                    "total_chars": non_space_count,
                },
            })
        else:
            checks.append({
                "check": "korean_ratio",
                "applicable": False,
                "skip_reason": (
                    f"한국어 문서 미감지 "
                    f"(한글 비율 {round(korean_ratio * 100, 1)}%, 기준 {int(_KOREAN_DOC_THRESHOLD * 100)}%)"
                ),
                "deduction": 0,
                "detail": {"korean_ratio": round(korean_ratio, 4)},
            })
    else:
        checks.append({
            "check": "korean_ratio",
            "applicable": False,
            "skip_reason": f"텍스트 부족 ({non_space_count}자, 20자 미만)",
            "deduction": 0,
            "detail": {},
        })

    return checks
