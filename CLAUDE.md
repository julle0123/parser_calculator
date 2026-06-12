# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 목적

업스테이지(Upstage) Document Parse API(동기식)의 응답 JSON을 입력받아
파싱 품질을 수치화하는 자동 평가 도구. 내부망 환경에서 운영되며 외부 LLM/VLM 사용 불가.

**핵심 제약**: ground truth 없음, LLM 없음, 인간 검수 불가.
이 시스템은 "파싱 품질 보증"이 아닌 "파싱 실패 징후 감지 필터"임을 전제로 설계.

## 실행

```bash
python evaluate.py <파싱결과.json> --pages <총페이지수>
python evaluate.py <파싱결과.json> --pages 10 --output result.json
```

외부 라이브러리 없음. Python 3.10 이상 표준 라이브러리만 사용.

## 업스테이지 파서 응답 스키마 (API 2.0)

```
{
  "api": "2.0",
  "content": { "html": "...", "markdown": "...", "text": "" },
  "elements": [
    {
      "id": int,
      "page": int,
      "category": "header" | "paragraph" | "table" | "footer" | ...,
      "content": { "html": "...", "markdown": "...", "text": "..." },
      "coordinates": [{"x": float, "y": float}, ...],  // 정규화 0~1, 4꼭짓점
      "words": [{"text": "...", "confidence": float, "coordinates": [...]}]
    }
  ]
}
```

`words[].confidence`가 업스테이지가 제공하는 **유일한 직접 품질 신호**.
`content.text` 최상위 필드는 API 설계상 비어있는 경우가 많음.

## 점수 구성 (100점)

| 컴포넌트 | 점수 | 파일 |
|---------|------|------|
| ① OCR 신뢰도 | 35점 | `components/confidence.py` |
| ② 구조 무결성 | 25점 | `components/structure.py` |
| ③ 텍스트 품질 | 20점 | `components/text_quality.py` |
| ④ 도메인 패턴 | 20점 | `components/domain.py` |

등급: A(85+) / B(70+) / C(50+) / D(미만)

## 아키텍처

```
evaluate.py      CLI 진입점 — argparse, 결과 출력
scorer.py        컴포넌트 오케스트레이션, 등급 판정, z-score
components/
  confidence.py  words[].confidence 분포 분석
  structure.py   페이지 커버리지, 좌표 유효성, 표 HTML 구조
  text_quality.py 한글 비율, 깨진 문자, html↔markdown 일관성
  domain.py      정규식 패턴 존재 + 추출값 범위 검증
```

각 컴포넌트는 독립 함수로 분리되어 있어 threshold 조정 및 단독 테스트 가능.
`scorer.py`의 `evaluate()` 함수가 전체 흐름 조율.

## 확장 시 유의사항

- 도메인 패턴은 `custom_patterns` 인자로 문서 카테고리별 교체 가능 (`domain.py`)
- threshold 값은 각 컴포넌트 파일 상단에 위치 — 운영 중 데이터 기반으로 보정 필요
- z-score는 30개 이상 누적 후 유효 (`scorer.py:compute_zscore`)
- 감지 불가 영역(숫자 오인식, 문장 누락 등)은 이 시스템 범위 밖임을 항상 명시
