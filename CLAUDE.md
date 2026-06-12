# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 맥락

업스테이지(Upstage) Document Parse API(동기식)의 JSON 응답을 입력받아 파싱 품질을 수치화하는 도구.

**변경 불가 제약 — 항상 염두에 둘 것:**
- LLM/VLM 호출 금지 (내부망)
- 이 시스템은 "파싱 실패 징후 감지 필터"임 — "품질 보증 시스템"으로 프레이밍하지 말 것
- 외부 라이브러리는 whl 파일로 반입 가능. 추가 시 `requirements.txt`에 명시.

## 실행

```bash
python evaluate.py <파싱결과.json> --pdf document.pdf        # PDF로 페이지 수 자동 추출
python evaluate.py <파싱결과.json> --pages 10               # 페이지 수 직접 지정
python evaluate.py <파싱결과.json> --output result.json     # 결과 저장
python evaluate.py <파싱결과.json> --history history.json   # z-score (30개↑)
```

## 의존성

```
pdfplumber      PDF 페이지 수 정확 추출 → 페이지 커버리지 지표 직접 개선
beautifulsoup4  표 HTML 안정 파싱 (malformed HTML 대응) → 표 구조 지표 직접 개선
numpy           confidence 분포 통계 (mean, percentile) — p10은 참고용, 점수 미반영
```

제거된 라이브러리: rapidfuzz(약한 신호를 더 정확히 측정해도 전체 신뢰도 무변화),
langdetect(한글 비율과 중복 + 비결정성 리스크), pandas(미사용)

## 아키텍처

```
evaluate.py       CLI 진입점 — pdfplumber로 페이지 수 추출, argparse
scorer.py         evaluate() — 4개 컴포넌트 조율 + 등급 판정
                  compute_zscore() — 누적 문서 대비 이상값 탐지
components/
  confidence.py   words[].confidence 분포 → 35점
                  (avg 15점 + 저신뢰비율 13점 + p10 7점)
  structure.py    페이지 커버리지, 좌표 유효성, 표 HTML 구조 → 25점
                  (bs4로 표 파싱)
  text_quality.py 한글 비율, 깨진 문자, 언어감지, html↔md 일관성 → 20점
                  (langdetect + rapidfuzz)
  domain.py       정규식 패턴 존재 + 추출값 범위 검증 → 20점
```

각 컴포넌트 함수는 독립적으로 동작하며 `{"component", "score", "max_score", "details"}` 구조를 반환.

**업스테이지 응답에서 유일한 직접 품질 신호는 `words[].confidence`.**
`content.text` 최상위 필드는 API 설계상 비어있는 경우가 많으니 품질 신호로 쓰지 말 것.

## 코드 작업 원칙

**요청한 것만 변경한다.**
threshold 조정, 컴포넌트 추가, 패턴 수정 등 요청 범위를 벗어난 리팩터링이나 "개선"은 하지 않는다.

**threshold는 데이터 없이 바꾸지 않는다.**
각 컴포넌트의 구간값(0.85, 0.97, 0.03 등)은 임의로 설정된 초기값이며, 운영 데이터 기반으로만 보정해야 한다. 코드 리뷰 목적으로 threshold를 "더 합리적"으로 보이는 값으로 바꾸지 말 것.

**도메인 확장은 `custom_patterns`로만 한다.**
문서 카테고리별 패턴 추가는 `domain.py`의 `custom_patterns` 인자를 쓴다. `DEFAULT_PATTERNS`나 `_VALUE_RULES`를 직접 수정하면 모든 문서 유형에 영향을 준다.

**감지 불가 영역을 감지 가능한 것처럼 표현하지 않는다.**
숫자 오인식, 문장 일부 누락, 셀 내용 교차는 이 시스템이 원천적으로 감지할 수 없다. 출력 문구나 주석에서 이 한계를 희석하는 표현을 쓰지 말 것.

## 자주 건드리는 위치

| 작업 | 파일 | 위치 |
|------|------|------|
| 신뢰도 구간값 조정 | `components/confidence.py` | `score_confidence()` 내 if-elif |
| p10 기준 조정 | `components/confidence.py` | `p10_score` 블록 |
| 페이지 커버리지 기준 수정 | `components/structure.py` | `score_structure()` 내 page 블록 |
| 깨진 문자 목록 추가 | `components/text_quality.py` | `_GARBLED_CHARS` |
| 금융 패턴 추가/수정 | `components/domain.py` | `DEFAULT_PATTERNS`, `_VALUE_RULES` |
| 등급 기준 변경 | `scorer.py` | `_GRADE_TABLE` |
