# 코드 변경 내역

---

## 1. HTML↔MD 일관성 체크 — 전체 element 대상으로 확장

**변경 파일:** `components/text_quality.py`

**변경 전**
```python
# 최대 50쌍만 샘플링 (element가 많아도 비교 비용 제한)
sampled = pair_details[:50]
sims = [s for s, *_ in sampled]
avg_sim = sum(sims) / len(sims)
...
"sample_pairs": len(sampled),
```

**변경 후**
```python
sims = [s for s, *_ in pair_details]
avg_sim = sum(sims) / len(sims)
...
"pairs": len(pair_details),
```

**이유**  
`pair_details`는 루프에서 이미 `SequenceMatcher.ratio()`까지 전부 계산이 완료된 상태였음.  
앞 50개만 잘라 평균 내면 비용 절감 효과는 없으면서 문서 앞부분에만 편향된 평가가 됨.

**함께 변경**
- 출력 필드명 `sample_pairs` → `pairs`
- `worst` 정렬 대상도 `sampled` → `pair_details` 전체로 통일
- `README.md` 출력 예시 필드명 동기화

---

## 2. 클래스 기반 리팩터링 및 모듈화

### 2-1. `BaseChecker` 추상 클래스 추가

**추가 파일:** `components/base.py`

```python
from abc import ABC, abstractmethod

class BaseChecker(ABC):
    @abstractmethod
    def score(self, elements: list[dict]) -> list[dict]:
        ...
```

**사용한 것들**

| 항목 | 설명 |
|------|------|
| `ABC` | Abstract Base Class. 직접 인스턴스화를 막고 상속 전용 클래스로 만듦 |
| `@abstractmethod` | 서브클래스가 반드시 `score()`를 구현하도록 강제. 구현하지 않으면 인스턴스화 시 `TypeError` 발생 |
| `...` (Ellipsis) | 추상 메서드 본문 자리. `pass`와 동일하지만 "미구현 인터페이스"임을 더 명확하게 표현 |

**이유**  
네 개 체커가 모두 `score(elements)` 인터페이스를 공유함. 추상 클래스로 묶으면:
- `DocumentScorer`가 체커 타입을 `list[BaseChecker]`로 선언할 수 있어 외부에서 커스텀 체커를 주입 가능
- 새 체커 추가 시 `score()` 구현을 빠뜨리는 실수를 컴파일 타임에 잡을 수 있음

---

### 2-2. 각 컴포넌트를 클래스로 전환

**변경 파일:** `components/confidence.py`, `structure.py`, `text_quality.py`, `completeness.py`

**변경 전**
```python
def score_confidence(elements: list[dict]) -> list[dict]:
    ...

def score_structure(elements: list[dict], total_pages: int | None) -> list[dict]:
    ...
```

**변경 후**
```python
class ConfidenceChecker(BaseChecker):
    def score(self, elements: list[dict]) -> list[dict]:
        ...

class StructureChecker(BaseChecker):
    def __init__(self, total_pages: int | None = None):
        self.total_pages = total_pages

    def score(self, elements: list[dict]) -> list[dict]:
        ...  # self.total_pages 사용
```

**`StructureChecker`에서 `total_pages`를 `__init__`으로 이동한 이유**  
원래 `score_structure(elements, total_pages)`처럼 매 호출마다 파라미터로 받았음.  
클래스화하면서 `score(elements)` 인터페이스를 통일해야 했고,  
`total_pages`는 문서가 아니라 체커 설정값에 해당하므로 생성자에 두는 것이 맞음.

---

### 2-3. 헬퍼 함수를 `@staticmethod`로 내부화

**변경 전** — 모듈 레벨 private 함수
```python
def _strip_html(html: str) -> str: ...
def _is_garbled(ch: str) -> bool: ...
def _is_valid_coord(coord: dict) -> bool: ...
```

**변경 후** — 클래스 내부 static 메서드
```python
class TextQualityChecker(BaseChecker):
    @staticmethod
    def _strip_html(html: str) -> str: ...

    @staticmethod
    def _is_garbled(ch: str) -> bool: ...
```

**`@staticmethod`를 선택한 이유**

| 구분 | 설명 |
|------|------|
| `self` 불필요 | 헬퍼 함수들은 인자만 받아 결과를 반환하는 순수 함수. 인스턴스 상태에 접근하지 않음 |
| 캡슐화 | 모듈 레벨에 두면 `from components.text_quality import _strip_html`처럼 내부 구현에 직접 접근 가능. 클래스 안에 두면 `TextQualityChecker._strip_html`처럼 클래스를 통해서만 접근하게 되어 경계가 명확해짐 |
| 의도 명시 | 함수 본문을 보지 않아도 `@staticmethod`만으로 "이 메서드는 인스턴스 상태를 건드리지 않는다"는 것을 바로 알 수 있음 |

**`score()`를 `@staticmethod`로 두지 않은 이유**  
`StructureChecker.score()`는 `self.total_pages`를 실제로 사용함.  
나머지 `score()` 메서드들은 `self`를 직접 쓰지 않더라도 `BaseChecker`의 추상 메서드를 구현하는 인터페이스이므로 일반 메서드로 유지.

---

### 2-4. `DocumentScorer` 클래스

**변경 파일:** `scorer.py`

**변경 전**
```python
def evaluate(parsed: dict, total_pages: int | None = None) -> dict:
    ...

def compute_zscore(score: float, history: list[float]) -> float | None:
    ...
```

**변경 후**
```python
class DocumentScorer:
    def __init__(
        self,
        total_pages: int | None = None,
        checkers: list[BaseChecker] | None = None,
    ):
        self._checkers: list[BaseChecker] = checkers or [
            ConfidenceChecker(),
            StructureChecker(total_pages=total_pages),
            TextQualityChecker(),
            CompletenessChecker(),
        ]

    def evaluate(self, parsed: dict) -> dict:
        ...

    @staticmethod
    def compute_zscore(score: float, history: list[float]) -> float | None:
        ...
```

**설계 포인트**

| 항목 | 설명 |
|------|------|
| `checkers` 파라미터 | 기본 4개 체커 대신 외부에서 커스텀 체커 목록을 주입할 수 있음. 테스트나 외부 통합 시 특정 체커만 교체 가능 |
| `list[BaseChecker] \| None` | `None`이면 기본 체커 목록 사용. `None`을 기본값으로 두고 내부에서 처리하는 패턴 (mutable default argument 문제 회피) |
| `compute_zscore` → `@staticmethod` | 인스턴스 상태가 전혀 필요 없는 순수 계산 함수. `DocumentScorer.compute_zscore(score, history)`처럼 인스턴스 없이 호출 가능 |
| `_get_grade`, `_GRADE_TABLE`, `_CAUTION` | 모든 `DocumentScorer` 인스턴스가 공유하는 상수/함수이므로 모듈 레벨에 유지 |

---

### 2-5. `components/__init__.py` — 클래스 export

**변경 전** — 사실상 빈 파일

**변경 후**
```python
from .base import BaseChecker
from .confidence import ConfidenceChecker
from .structure import StructureChecker
from .text_quality import TextQualityChecker
from .completeness import CompletenessChecker

__all__ = [
    "BaseChecker",
    "ConfidenceChecker",
    ...
]
```

**상대 import (`.base`, `.confidence` 등) 사용 이유**  
`components` 패키지 내부에서 서로를 참조할 때 절대 경로(`from components.base import ...`) 대신 상대 경로(`.base`)를 씀.  
패키지 디렉터리가 이동하거나 이름이 바뀌어도 내부 참조가 깨지지 않음.

**`__all__` 사용 이유**  
`from components import *`를 했을 때 노출되는 이름을 명시적으로 제한.  
현재 코드에서 `import *`를 직접 쓰지는 않지만, 외부 코드에서 이 패키지를 가져다 쓸 때 "공개 API가 무엇인지"를 선언하는 문서 역할.

---

### 2-6. 타입 힌트 정리

코드 전반에서 사용한 타입 힌트 패턴:

| 표현 | 의미 |
|------|------|
| `list[dict]` | dict 원소를 갖는 리스트 (Python 3.9+, `List[dict]` 불필요) |
| `int \| None` | int 또는 None (Python 3.10+, `Optional[int]` 불필요) |
| `list[BaseChecker] \| None` | BaseChecker 인스턴스 리스트 또는 None |
| `tuple[str, str]` | 문자열 두 개짜리 튜플 |
| `float \| None` | float 또는 None |

---

### 2-7. 호출부 변경

**변경 파일:** `evaluate.py`, `batch_run.py`, `routers/evaluate.py`, `routers/batch.py`

```python
# 변경 전
from scorer import evaluate, compute_zscore
result = evaluate(parsed, total_pages=total_pages)
z = compute_zscore(result["score"], history)

# 변경 후
from scorer import DocumentScorer
result = DocumentScorer(total_pages=total_pages).evaluate(parsed)
z = DocumentScorer.compute_zscore(result["score"], history)
```

---

## 3. 버그 수정

### 3-1. `completeness._is_content_empty` — `text` 필드 복원

**변경 파일:** `components/completeness.py`

리팩터링 과정에서 `content.text` 체크를 실수로 제거함.  
`html`/`markdown`이 모두 없고 `text`만 있는 element가 "빈 element"로 잘못 카운트되어 `empty_element_ratio` 감점이 늘어나는 문제.  
원본 동작(세 필드 중 하나라도 있으면 비어있지 않음)으로 복원.

```python
# 버그 있던 코드
return not any([
    (content.get("html") or "").strip(),
    (content.get("markdown") or "").strip(),
])

# 복원
return not any([
    (content.get("html") or "").strip(),
    (content.get("text") or "").strip(),
    (content.get("markdown") or "").strip(),
])
```

### 3-2. `batch_run.py` — `DocumentScorer` 루프 밖으로 이동

파일마다 `DocumentScorer()` 인스턴스를 새로 생성하던 것을 루프 밖으로 이동.  
batch 평가는 `total_pages`를 사용하지 않으므로 동일 인스턴스를 재사용해도 무방함.

```python
# 변경 전 — 파일마다 새 인스턴스
for path in files:
    r = DocumentScorer().evaluate(parsed)

# 변경 후 — 인스턴스 재사용
scorer = DocumentScorer()
for path in files:
    r = scorer.evaluate(parsed)
```
