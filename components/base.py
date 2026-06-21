from abc import ABC, abstractmethod


class BaseChecker(ABC):
    @abstractmethod
    def score(self, elements: list[dict]) -> list[dict]:
        ...
