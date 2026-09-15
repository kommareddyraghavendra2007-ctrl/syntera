from __future__ import annotations

from abc import ABC, abstractmethod

from app.parsing.types import ParseResult


class CodeParser(ABC):
    @abstractmethod
    def supported_languages(self) -> set[str]:
        raise NotImplementedError

    @abstractmethod
    def parse(self, file_path: str, source: str, language: str) -> ParseResult:
        raise NotImplementedError
