"""
파싱 완결성 감점 체크 (최대 -20점)

content 정확성이 아닌 기술적 완결성을 측정.
문서 유형 무관하게 Upstage API 응답 구조에서 직접 파생.

- empty_element_ratio: content 필드가 완전히 빈 element 비율 (최대 -10점)
- table_html_missing:  table element의 HTML 누락 비율 (최대 -5점, table 있을 때)
- word_fragmentation:  words 평균 글자 수 이상 단편화 감지 (최대 -5점, words 있을 때)

한계: 내용이 맞는지는 알 수 없음. 파싱 출력이 기술적으로 채워졌는지만 측정.
"""

from .base import BaseChecker


class CompletenessChecker(BaseChecker):
    def score(self, elements: list[dict]) -> list[dict]:
        # 파싱 출력이 기술적으로 채워졌는지 확인. 내용의 정확성은 이 체크로 알 수 없음.
        # 세 가지 체크: 빈 element 비율 → 표 HTML 누락 → word 단편화
        if not elements:
            return [
                {
                    "check": name,
                    "applicable": False,
                    "skip_reason": "elements 없음",
                    "deduction": 0,
                    "detail": {},
                }
                for name in ("empty_element_ratio", "table_html_missing", "word_fragmentation")
            ]

        checks = []

        empty_count = sum(1 for el in elements if self._is_content_empty(el))
        empty_ratio = empty_count / len(elements)

        if empty_ratio == 0.0:
            empty_deduction = 0
        elif empty_ratio <= 0.10:
            empty_deduction = -4
        else:
            empty_deduction = -10

        checks.append({
            "check": "empty_element_ratio",
            "applicable": True,
            "deduction": empty_deduction,
            "detail": {
                "total_elements": len(elements),
                "empty_elements": empty_count,
                "empty_ratio": round(empty_ratio, 4),
            },
        })

        table_els = [el for el in elements if el.get("category") == "table"]
        if table_els:
            html_missing = sum(
                1 for el in table_els
                if not (el.get("content", {}).get("html") or "").strip()
            )
            missing_ratio = html_missing / len(table_els)

            if missing_ratio == 0.0:
                table_deduction = 0
            elif missing_ratio <= 0.20:
                table_deduction = -2
            else:
                table_deduction = -5

            checks.append({
                "check": "table_html_missing",
                "applicable": True,
                "deduction": table_deduction,
                "detail": {
                    "total_tables": len(table_els),
                    "html_missing": html_missing,
                    "missing_ratio": round(missing_ratio, 4),
                },
            })
        else:
            checks.append({
                "check": "table_html_missing",
                "applicable": False,
                "skip_reason": "table 유형 element 없음",
                "deduction": 0,
                "detail": {},
            })

        all_words = [w for el in elements for w in el.get("words", [])]
        if all_words:
            # API 버전에 따라 단어 텍스트 필드가 "text" 또는 "word"로 다를 수 있음
            word_texts = [
                w.get("text", "") or w.get("word", "")
                for w in all_words
            ]
            word_texts = [t for t in word_texts if t]

            if word_texts:
                avg_len = sum(len(t) for t in word_texts) / len(word_texts)

                # 평균 글자 수 2.0 미만이면 단어가 글자 단위로 분해된 것으로 판단
                if avg_len >= 2.0:
                    frag_deduction = 0
                elif avg_len >= 1.5:
                    frag_deduction = -2
                else:
                    frag_deduction = -5

                checks.append({
                    "check": "word_fragmentation",
                    "applicable": True,
                    "deduction": frag_deduction,
                    "detail": {
                        "total_words": len(word_texts),
                        "avg_word_length": round(avg_len, 3),
                    },
                })
            else:
                checks.append({
                    "check": "word_fragmentation",
                    "applicable": False,
                    "skip_reason": "words 텍스트 필드 없음",
                    "deduction": 0,
                    "detail": {},
                })
        else:
            checks.append({
                "check": "word_fragmentation",
                "applicable": False,
                "skip_reason": "words 데이터 없음",
                "deduction": 0,
                "detail": {},
            })

        return checks

    @staticmethod
    def _is_content_empty(el: dict) -> bool:
        # html / text / markdown 세 필드 중 하나라도 공백 아닌 내용이 있으면 비어있지 않다고 판단.
        content = el.get("content", {})
        return not any([
            (content.get("html") or "").strip(),
            (content.get("text") or "").strip(),
            (content.get("markdown") or "").strip(),
        ])
