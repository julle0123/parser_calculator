"""Repository 공통 기반 — filter dict + data dict → SQLAlchemy WHERE / SET 변환."""

from __future__ import annotations

from typing import Any


class BaseRepository:
    """모든 Repository 의 부모 클래스.

    filter 딕셔너리 형식:
        {컬럼명: 연산자}
        연산자 종류: "=", "!=", "like", ">", ">=", "<", "<=", "in", "not in"

    data 딕셔너리:
        - 단건 : dict          → insert_one / update_one / select_one / delete_one
        - 다건 : list[dict]    → insert_many / update_many
    """

    @property
    def table(self) -> Any:
        raise NotImplementedError

    def _where(self, filter: dict[str, str], data: dict[str, Any]) -> list:
        """filter + data → SQLAlchemy WHERE 절 리스트."""
        clauses = []
        for col_name, operator in filter.items():
            value = data[col_name]
            col = getattr(self.table, col_name)
            match operator:
                case "=":
                    clauses.append(col == value)
                case "!=":
                    clauses.append(col != value)
                case "like":
                    clauses.append(col.like(value))
                case ">":
                    clauses.append(col > value)
                case ">=":
                    clauses.append(col >= value)
                case "<":
                    clauses.append(col < value)
                case "<=":
                    clauses.append(col <= value)
                case "in":
                    clauses.append(col.in_(value))
                case "not in":
                    clauses.append(col.not_in(value))
                case _:
                    raise ValueError(f"지원하지 않는 연산자: '{operator}'")
        return clauses

    def _set_values(self, filter: dict[str, str], data: dict[str, Any]) -> dict[str, Any]:
        """update SET 값 — filter 조건 컬럼을 제외한 나머지 data 필드."""
        return {k: v for k, v in data.items() if k not in filter}
