# 업스테이지 Document Parse 파싱 실패 징후 감지 필터

업스테이지(Upstage) Document Parse API의 JSON 응답을 입력받아
파싱 실패 징후를 100점 감점 방식으로 수치화하는 도구.

---

## 중요 전제 — 반드시 먼저 읽을 것

이 시스템은 **파싱 실패 징후 감지 필터**입니다. 파싱 품질 보증 시스템이 아닙니다.

| 감지 가능 | 감지 불가능 |
|----------|------------|
| 페이지 통째 누락 | 숫자 오인식 (1→l, 0→O) |
| 표 구조 완전 붕괴 | 문장 일부 누락 |
| OCR 신뢰도 극저하 | 표 셀 내용 교차 |
| 한글 깨짐/대체문자 | 미묘한 의미 왜곡 |
| 좌표 범위 이탈 | 읽기 순서 오류 |

> **Grade A = 명백한 실패 없음** (내용 정확성 보장 아님)
> **Grade D = 명백한 실패 감지** (즉시 조치 필요)

---

## 코드 실행 구조

### 전체 흐름

```
사용자 명령
  python evaluate.py parsed.json --pages 5 --output result.json
        │
        ▼
  [evaluate.py]  ── JSON 파일 로드
                 ── scorer.evaluate() 호출
        │
        ▼
  [scorer.py]    ── 4개 컴포넌트를 순서대로 실행
        │
        ├── [confidence.py]   OCR 신뢰도 체크 2개
        ├── [structure.py]    구조 무결성 체크 3개
        ├── [text_quality.py] 텍스트 품질 체크 3개
        └── [completeness.py] 파싱 완결성 체크 3개
        │
        ▼
  감점 합산: 100 + 각 체크 deduction 합계
  등급 판정: 85↑→A / 70↑→B / 50↑→C / 그 외→D
        │
        ▼
  [evaluate.py]  ── 화면 출력
                 ── result.json 저장 (--output 지정 시)
```

---

### 각 컴포넌트가 API 응답에서 읽는 필드

업스테이지 Document Parse API는 파싱 결과를 `elements` 배열로 반환합니다.
각 컴포넌트는 그 안의 서로 다른 필드를 읽어 감점 여부를 판단합니다.

```
Upstage API 응답 JSON
└── elements[]                     ← 파싱된 블록 목록 (단락, 표, 그림 등)
      ├── page                     ← 몇 번째 페이지인지
      ├── category                 ← 블록 유형 (paragraph / table / figure 등)
      ├── coordinates[]            ← 페이지 내 위치 (정규화 0~1)
      │     ├── x
      │     └── y
      ├── content
      │     ├── html               ← HTML 형식 텍스트
      │     ├── markdown           ← Markdown 형식 텍스트
      │     └── text               ← 일반 텍스트
      └── words[]                  ← 단어 단위 OCR 결과
            ├── text               ← 단어 텍스트
            └── confidence         ← OCR 신뢰도 (0~1)
```

| 컴포넌트 | 읽는 필드 | 측정하는 것 |
|---------|-----------|------------|
| `confidence.py` | `words[].confidence` | OCR이 얼마나 확신하는지 |
| `structure.py` | `page`, `coordinates`, `content.html` (표만) | 페이지 누락·좌표 이상·표 구조 붕괴 |
| `text_quality.py` | `content.html`, `content.markdown` | 깨진 문자·한글 비율·HTML↔MD 불일치 |
| `completeness.py` | `content` 전체, `words[].text` | 빈 블록·표 HTML 누락·단어 단편화 |

---

### 체크 하나의 판단 과정 (예: `ocr_avg_confidence`)

```
1. elements 전체를 순회하며 words[] 수집
2. 모든 단어의 confidence 값 평균 계산
3. 평균값을 구간에 대입해 감점 결정

   avg ≥ 0.97  →  감점 없음 (deduction = 0)
   avg ≥ 0.94  →  -5점
   avg ≥ 0.90  →  -10점
   avg < 0.90  →  -18점

4. words 데이터가 아예 없으면 → applicable: false (skip)
```

모든 체크가 이 패턴을 따릅니다.
측정값을 구간에 넣어 감점(deduction)을 결정하고, 해당 없으면 skip.

---

### 최종 점수 계산

```
100점
 - ocr_avg_confidence  deduction   (0 / -5 / -10 / -18 중 하나)
 - ocr_low_conf_ratio  deduction   (0 / -6 / -12 / -17 중 하나)
 - page_coverage       deduction   (0 / -5 / -10 중 하나, total_pages 있을 때)
 - coord_validity      deduction   (0 / -4 / -8 중 하나)
 - table_structure     deduction   (0 / -3 / -7 중 하나, 표 있을 때)
 - garbled_chars       deduction   (0 / -4 / -7 중 하나, 텍스트 있을 때)
 - html_md_consistency deduction   (0 / -3 / -6 중 하나)
 - korean_ratio        deduction   (0 / -3 / -7 중 하나, 한국어 문서일 때)
 - empty_element_ratio deduction   (0 / -4 / -10 중 하나)
 - table_html_missing  deduction   (0 / -2 / -5 중 하나, 표 있을 때)
 - word_fragmentation  deduction   (0 / -2 / -5 중 하나, words 있을 때)
= 최종 점수 (최소 0, 최대 100)
```

각 체크는 **티어 중 하나만** 적용됩니다.
예) `ocr_avg_confidence`가 0.88이면 -10점 하나만 감점. -5점과 중복 적용 없음.

---

## 설치

```bash
pip install pdfplumber beautifulsoup4 numpy fastapi uvicorn python-multipart
# 내부망: whl 파일로 반입 후 pip install *.whl
```

---

## 실행

### API 서버 (`main.py`)

```bash
python main.py
```

서버가 `http://localhost:9101` 에서 시작됩니다.
Swagger UI: `http://localhost:9101/docs`

**엔드포인트**

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/evaluate` | 파서 결과 JSON 파일 단건 평가 |
| `POST` | `/evaluate/batch` | 파서 결과 JSON 파일 일괄 평가 |
| `GET` | `/health` | 헬스체크 |

**`POST /evaluate` 요청 (multipart/form-data)**

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `file` | 파일 | Y | 업스테이지 파서 결과 JSON 파일 |
| `total_pages` | 정수 | N | PDF 총 페이지 수 (미제공 시 page_coverage skip) |

**`POST /evaluate/batch` 요청 (multipart/form-data)**

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `files` | 파일 목록 | Y | 업스테이지 파서 결과 JSON 파일 여러 개 |

---

### 단일 파일 평가 (`evaluate.py`)

```bash
# 기본 실행 (PDF/페이지 수 없어도 동작)
python evaluate.py parsed.json

# PDF로 페이지 수 자동 추출 (page_coverage 체크 활성화)
python evaluate.py parsed.json --pdf document.pdf

# 페이지 수 직접 지정
python evaluate.py parsed.json --pages 10

# 상세 결과 JSON 저장
python evaluate.py parsed.json --pdf document.pdf --output result.json

# z-score 계산 (30개 이상 누적 후 유효)
python evaluate.py parsed.json --history history.json
```

### 일괄 평가 (`batch_run.py`)

디렉터리 안의 JSON 파일을 한 번에 모두 평가합니다.

```bash
# 현재 디렉터리의 모든 JSON 평가
python batch_run.py

# 특정 디렉터리 지정
python batch_run.py ./results/

# 배치 요약을 JSON으로 저장
python batch_run.py ./results/ --output summary.json

# 파일별 상세 result_*.json 저장
python batch_run.py ./results/ --output-dir scored/

# 한국어 보고서 텍스트 저장 (비개발자용)
python batch_run.py ./results/ --output summary.json --report report.txt
```

`--output summary.json` 형식 (감점 항목에 `reason` 포함):

```jsonc
{
  "total": 36,
  "scores": { "max": 100.0, "min": 93.0, "avg": 98.4 },
  "files": [
    {
      "file": "doc1.json",
      "score": 100.0,
      "grade": "A",
      "deduction": 0,
      "deductions": []
    },
    {
      "file": "doc2.json",
      "score": 93.0,
      "grade": "A",
      "deduction": -7,
      "deductions": [
        {
          "check": "table_structure",
          "deduction": -7,
          "detail": {
            "total_tables": 9,
            "broken_tables": 2,
            "broken_ratio": 0.2222,
            "broken_table_details": [
              {
                "page": 8,
                "reason": "표의 1번째 행에 내용이 비정상적으로 몰려 있습니다. (1번째 행: 48칸, 나머지 행 평균: 5.3칸) 셀 병합이 많은 복잡한 표에서 파싱이 구조를 제대로 인식하지 못했을 가능성이 있습니다."
              }
            ]
          }
        }
      ]
    }
  ]
}
```

---

## 점수 구성 — 100점 감점 방식

100점에서 시작해 감지된 문제만 감점합니다.
**문서 특성에 따라 해당 없는 체크는 자동으로 skip됩니다.**

### 감점 체크 목록

| 체크 항목 | 최대 감점 | 적용 조건 |
|-----------|-----------|-----------|
| `ocr_avg_confidence` | -18 | words 데이터 존재 시 |
| `ocr_low_conf_ratio` | -17 | words 데이터 존재 시 |
| `page_coverage` | -10 | --pdf 또는 --pages 제공 시 |
| `coord_validity` | -8 | 항상 적용 |
| `table_structure` | -7 | table element 존재 시 |
| `garbled_chars` | -7 | 텍스트 20자 이상 시 |
| `korean_ratio` | -7 | 한글 비율 15% 초과 시 (한국어 문서 자동 감지) |
| `html_md_consistency` | -6 | HTML·markdown 양쪽 필드 존재 시 |
| `empty_element_ratio` | -10 | 항상 적용 |
| `table_html_missing` | -5 | table element 존재 시 |
| `word_fragmentation` | -5 | words 데이터 존재 시 |

### 체크별 감점 기준

**OCR 평균 신뢰도** (`words[].confidence` 평균)
```
≥ 0.97 →  0점
≥ 0.94 → -5점
≥ 0.90 → -10점
< 0.90 → -18점
```

**저신뢰 단어 비율** (confidence < 0.85 비율)
```
≤ 3%  →  0점
≤ 8%  → -6점
≤ 15% → -12점
> 15% → -17점
```

**페이지 커버리지** (element 없는 페이지 비율)
```
0%    →  0점
≤ 5%  → -5점
> 5%  → -10점
```

**좌표 유효성** (정규화 범위 0~1 이탈 비율)
```
0%    →  0점
≤ 1%  → -4점
> 1%  → -8점
```

**표 구조** (행별 셀 수 불일치 표 비율)
```
0%    →  0점
≤ 20% → -3점
> 20% → -7점
```

**깨진 문자** (대체문자·한글자모 단독 등장 비율)
```
≤ 0.5% →  0점
≤ 1.0% → -4점
> 1.0% → -7점
```

**HTML↔Markdown 일관성** (동일 element 텍스트 유사도)
```
≥ 0.90 →  0점
≥ 0.70 → -3점
< 0.70 → -6점
```

**한글 비율** (한국어 문서 감지 시만)
```
≥ 50% →  0점
≥ 30% → -3점
< 30% → -7점
```

**빈 element 비율** (html·text·markdown 모두 비어있는 element 비율)
```
0%    →  0점
≤ 10% → -4점
> 10% → -10점
```

**table HTML 누락** (table element인데 html 필드 없는 비율)
```
0%    →  0점
≤ 20% → -2점
> 20% → -5점
```

**word 단편화** (words 평균 글자 수)
```
≥ 2.0자 →  0점
≥ 1.5자 → -2점
< 1.5자 → -5점
```

---

## 출력 예시

```
========================================================
  최종 점수 : 74 / 100  (감점 합계: -26)
  등급      : Grade B  (주의 — 재확인 권고)
========================================================

[감점 내역]
  ocr_avg_confidence             avg=0.926              -10
  ocr_low_conf_ratio             ratio=0.092            -12
  table_structure                2/8 구조 이상           -3
  ────────────────────────────────────────────────────────
  합계                                                   -26

[통과]
  coord_validity                 이상 0/42개
  garbled_chars                  ratio=0.0002
  html_md_consistency            유사도=0.9401
  korean_ratio                   ratio=0.7823

[미적용 — 해당 없음]
  page_coverage                  total_pages 미제공 (--pdf 또는 --pages 옵션 필요)
```

---

## 등급 기준

| Grade | 점수 | 의미 |
|-------|------|------|
| A | 85~100 | 정상 처리 |
| B | 70~84 | 주의 — 재확인 권고 |
| C | 50~69 | 경고 — 파싱 재시도 권장 |
| D | 0~49 | 실패 — 처리 보류 |

---

## z-score 이상 감지 (30개 이상 누적 후 권장)

```python
from scorer import compute_zscore

history = [88.0, 91.5, 85.0, ...]  # 누적 점수 리스트
z = compute_zscore(current_score, history)
# z < -2.0 → 이상 문서 플래그
```

---

## result.json 형식

`--output result.json` 옵션을 쓰면 저장되는 파일의 전체 구조입니다.

```jsonc
{
  "score": 82.0,                        // 최종 점수 (0~100)
  "grade": "B",                         // 등급 (A / B / C / D)
  "grade_description": "주의 - 재확인 권고",
  "total_deduction": -18,               // 감점 합계 (음수)

  "checks": [                           // 체크 11개, 순서 고정
    {
      "check": "ocr_avg_confidence",    // 체크 이름
      "applicable": true,               // true = 실제 측정됨
      "deduction": -10,                 // 이 체크의 감점 (0이면 통과)
      "detail": {
        "total_words": 150,
        "avg_confidence": 0.921,
        "p10_confidence": 0.874,        // 하위 10% 백분위 (참고용)
        "low_conf_samples": [           // 신뢰도 낮은 단어 예시 (감점 시 포함)
          { "page": 3, "text": "운용", "confidence": 0.712 }
        ]
      }
    },
    {
      "check": "ocr_low_conf_ratio",
      "applicable": true,
      "deduction": -8,
      "detail": {
        "low_conf_ratio": 0.093,
        "low_conf_count": 14,
        "threshold": 0.85,
        "low_conf_samples": [           // 신뢰도 낮은 단어 예시 (감점 시 포함)
          { "page": 3, "text": "운용", "confidence": 0.712 }
        ]
      }
    },
    {
      "check": "page_coverage",
      "applicable": false,              // false = skip (측정 안 됨)
      "skip_reason": "total_pages 미제공 (--pdf 또는 --pages 옵션 필요)",
      "deduction": 0,
      "detail": {}
    },
    {
      "check": "coord_validity",
      "applicable": true,
      "deduction": 0,
      "detail": {
        "total_elements": 42,
        "invalid_coord_elements": 0,
        "invalid_ratio": 0.0
      }
    },
    {
      "check": "table_structure",
      "applicable": true,
      "deduction": -7,
      "detail": {
        "total_tables": 9,
        "broken_tables": 2,
        "broken_ratio": 0.2222,
        "broken_table_details": [       // 이상 표별 위치·원인 (감점 시 포함)
          {
            "page": 8,
            "reason": "표의 1번째 행에 내용이 비정상적으로 몰려 있습니다. (1번째 행: 48칸, 나머지 행 평균: 5.3칸) 셀 병합이 많은 복잡한 표에서 파싱이 구조를 제대로 인식하지 못했을 가능성이 있습니다."
          }
        ]
      }
    },
    {
      "check": "garbled_chars",
      "applicable": true,
      "deduction": 0,
      "detail": {
        "garbled_ratio": 0.0003,
        "garbled_count": 2,
        "total_chars": 6240
        // garbled_locations: 감점 시 페이지·위치·발견 문자 포함
      }
    },
    {
      "check": "html_md_consistency",
      "applicable": true,
      "deduction": -3,
      "detail": {
        "avg_similarity": 0.878,
        "sample_pairs": 50,
        "low_similarity_samples": [     // 불일치 항목 예시 (감점 시 포함)
          {
            "page": 4,
            "category": "heading1",
            "similarity": 0.275,
            "html": "○   위험도",
            "markdown": "○ <label><input type=\"checkbox\"> 위험도</label>",
            "reason": "HTML 버전과 Markdown 버전의 내용이 다르게 처리되었습니다. Markdown에 코드 태그가 텍스트로 그대로 남아 있어 파싱 과정에서 해당 요소를 Markdown 형식으로 변환하지 못한 것입니다."
          }
        ]
      }
    },
    {
      "check": "korean_ratio",
      "applicable": true,               // 한글 비율 > 15% → 한국어 문서로 감지
      "deduction": 0,
      "detail": {
        "korean_ratio": 0.871,
        "korean_count": 5435,
        "total_chars": 6240
      }
    },
    {
      "check": "empty_element_ratio",
      "applicable": true,
      "deduction": 0,
      "detail": {
        "total_elements": 42,
        "empty_elements": 0,            // html + text + markdown 모두 빈 element 수
        "empty_ratio": 0.0
      }
    },
    {
      "check": "table_html_missing",
      "applicable": true,
      "deduction": 0,
      "detail": {
        "total_tables": 5,
        "html_missing": 0,              // html 필드가 없는 table element 수
        "missing_ratio": 0.0
      }
    },
    {
      "check": "word_fragmentation",
      "applicable": true,
      "deduction": 0,
      "detail": {
        "total_words": 150,
        "avg_word_length": 3.94         // 단어 평균 글자 수 (< 1.5이면 단편화)
      }
    }
  ],

  "caution": "이 점수는 파싱 실패 징후를 감지하는 필터입니다. ..."

  // z-score 옵션 사용 시 추가 필드
  // "zscore": -1.23,
  // "zscore_note": "정상 범위"
}
```

### applicable 필드 이해하기

| applicable | deduction | 의미 |
|-----------|-----------|------|
| `true` | `0` | 측정했고 문제 없음 (통과) |
| `true` | `-N` | 측정했고 문제 발견 (감점) |
| `false` | `0` | 해당 없어서 측정 안 함 (skip) |

`applicable: false`인 체크는 점수에 영향을 주지 않습니다.
예) words 데이터가 없는 문서는 `ocr_avg_confidence`가 skip되며 감점도 없습니다.

---

## Python API

```python
import json
from scorer import evaluate

with open("parsed.json", encoding="utf-8") as f:
    parsed = json.load(f)

result = evaluate(
    parsed,
    total_pages=10,   # 없으면 page_coverage 체크 skip
)

print(result["score"])       # 74.0
print(result["grade"])       # "B"
for check in result["checks"]:
    if check["deduction"] < 0:
        print(check["check"], check["deduction"])
```

---

## 프로젝트 구조

```
parser_cal/
├── main.py               # API 서버 진입점 (python main.py)
├── api.py                # FastAPI 앱 생성 + 라우터 등록
├── routers/
│   ├── evaluate.py       # POST /evaluate
│   ├── batch.py          # POST /evaluate/batch
│   └── health.py         # GET /health
├── schemas/
│   └── evaluate.py       # Pydantic 요청/응답 모델
├── evaluate.py           # CLI 진입점
├── batch_run.py          # CLI 일괄 평가 진입점
├── scorer.py             # 감점 합산 + 등급 판정 + z-score
├── components/
│   ├── confidence.py     # OCR 신뢰도 체크 (최대 -35점)
│   ├── structure.py      # 구조 무결성 체크 (최대 -25점)
│   ├── text_quality.py   # 텍스트 품질 체크 (최대 -20점)
│   └── completeness.py   # 파싱 완결성 체크 (최대 -20점)
├── requirements.txt
└── README.md
```

---

## 검토했으나 채택하지 못한 방법들

설계 과정에서 검토한 모든 방법과 불가 이유를 기록.

### Ground Truth 기반 메트릭 (OmniDocBench, DP-Bench)

**방법**: 정답 텍스트와 파싱 결과를 비교해 NED(Normalized Edit Distance), TEDS 등 산출.
OmniDocBench, DP-Bench(업스테이지 자체 벤치마크) 모두 이 방식.

**불가 이유**: Ground truth(정답 레이블) 없음. 레이블링 리소스도 없음.

---

### VLM-as-Judge / DOCR-Inspector

**방법**: 원본 문서 이미지와 파싱 결과를 VLM(비전-언어 모델)에 동시 입력해 품질 판단.
DOCR-Inspector는 28가지 오류 유형을 ground truth 없이 감지 가능.

**불가 이유**: 내부망 환경으로 외부 LLM/VLM 접근 불가. 내부망에 LLM 없음.

---

### pdfplumber pseudo-GT

**방법**: pdfplumber로 PDF에서 텍스트를 직접 추출해 Upstage 출력과 NED 비교.

**불가 이유 (복수)**:
1. **순환 논리**: 업스테이지 파서를 쓰는 이유가 pdfplumber의 한계 때문인데, 더 성능 낮은 도구로 평가하는 구조.
2. **읽기 순서 오류**: pdfplumber는 PDF 내부 저장 순서로 추출하므로 시각적 읽기 순서와 불일치. 다단 컬럼, 사이드바에서 심각.
3. **표 추출 품질**: pdfplumber의 표 추출은 병합 셀, 복잡한 테두리에서 자주 실패.
4. **한글 인코딩**: 커스텀 폰트 인코딩 사용 PDF에서 깨진 문자 출력.
5. **역방향 오류**: pdfplumber가 틀리고 Upstage가 맞아도 NED 점수가 낮게 나오는 문제.

> pdfplumber는 현재 **페이지 수 추출 용도로만** 사용 (텍스트 비교 불가).

---

### LangCheck

**방법**: LLM 기반 텍스트 품질 평가 라이브러리. reference-free 메트릭 포함.

**불가 이유**: 내부망, 외부 LLM API 접근 불가. 일부 로컬 실행 가능한 메트릭은 영어/일본어 중심.

---

### DeepEval / RAGAS

**방법**: RAG 파이프라인 품질 평가 프레임워크. Faithfulness, Contextual Recall 등.

**불가 이유**: 내부망, LLM 호출 필요.

---

### SCORE (Semantic Evaluation Framework)

**방법**: 생성형 문서 파싱을 위한 시맨틱 평가. ground truth 없이 의미 정확성 판단.

**불가 이유**: 내부망, LLM 기반 의미 판단 모델 필요.

---

### BERTScore

**방법**: BERT 임베딩 기반 시맨틱 유사도.

**불가 이유**: 비교 대상(참조 텍스트 또는 ground truth) 필요. 단독으로는 사용 불가.

---

### Tesseract OCR 이중 추출 비교

**방법**: PDF를 이미지로 변환 후 Tesseract로 OCR, Upstage 출력과 비교.

**불가 이유**: Tesseract는 업스테이지 파서보다 한국어 성능이 낮음. 더 못한 OCR 결과로 더 나은 파서를 채점하는 역방향 오류.

---

### 인간 샘플링 검수

**방법**: 자동 평가를 통과한 문서 일부를 사람이 직접 검수.

**불가 이유**: 검수 인력/리소스 없음.

---

### 통계적 이상값 탐지 단독 사용

**방법**: 누적 문서 점수 분포에서 z-score < -2.0인 문서를 이상으로 판단.

**불가 이유**: 단독으로는 기준선(baseline)이 없어 초기 운영 시 무의미. 절댓값 점수와 병행해야 유효하므로 보조 기능으로만 탑재.

---

### rapidfuzz (채택 검토 후 제거)

**방법**: html↔markdown 일관성 계산에 SequenceMatcher 대신 사용.

**제거 이유**: html↔markdown 일관성 자체가 약한 신호인데, 이를 더 정확히 측정해도 전체 시스템 신뢰도에 변화 없음. 의존성 비용 대비 실익 없음.

---

### langdetect (채택 검토 후 제거)

**방법**: 파싱 텍스트 언어를 감지해 한국어 여부 직접 판단.

**제거 이유**:
1. **비결정성**: seed 고정 없이는 같은 텍스트에 다른 결과 가능 → 점수 시스템에 부적합.
2. **한글 비율 지표와 중복**: 한글 문자 비율 15% 초과 시 자동 감지로 대체. 독립적인 추가 신호 없음.

---

### 한국 금융 NLP 모델 (₩on, FINKRX)

**방법**: 한국어 금융 도메인 특화 모델로 파싱 결과의 하류 작업 성능 평가.

**불가 이유**: 내부망, 외부 모델 접근 불가.
