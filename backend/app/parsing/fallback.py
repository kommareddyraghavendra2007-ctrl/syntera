from __future__ import annotations

import re
from hashlib import sha256

from app.core.enums import ParserCapability, SymbolType
from app.parsing.base import CodeParser
from app.parsing.types import ExtractedSymbol, ParseResult

_IDENTIFIER = re.compile(r"^(?:export\s+)?(?:async\s+)?(?:def|class|function|interface|struct|enum)\s+([A-Za-z_][\w]*)", re.M)
_PY_DEF = re.compile(r"^([ \t]*)(?:async\s+)?def\s+([A-Za-z_][\w]*)\s*\(", re.M)
_PY_CLASS = re.compile(r"^([ \t]*)class\s+([A-Za-z_][\w]*)\s*[:(]", re.M)
_JS_FN = re.compile(r"^(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_][\w]*)\s*\(", re.M)
_JS_CLASS = re.compile(r"^(?:export\s+)?class\s+([A-Za-z_][\w]*)\b", re.M)
_JAVA_CLASS = re.compile(r"\b(?:class|interface|enum)\s+([A-Za-z_][\w]*)")
_JAVA_METHOD = re.compile(
    r"^\s*(?:public|private|protected)?\s*(?:static\s+)?[\w.<>,\[\]]+\s+([A-Za-z_][\w]*)\s*\(",
    re.M,
)
_GO_FN = re.compile(r"^func\s+(?:\([^)]+\)\s*)?([A-Za-z_][\w]*)\s*\(", re.M)
_C_FN = re.compile(
    r"^\s*[\w\s\*]+\s+([A-Za-z_][\w]*)\s*\([^;]*\)\s*\{",
    re.M,
)


class TextFallbackParser(CodeParser):
    def supported_languages(self) -> set[str]:
        return {"*"}

    def parse(self, file_path: str, source: str, language: str) -> ParseResult:
        symbols: list[ExtractedSymbol] = []
        lines = source.splitlines()
        if language == "python":
            symbols.extend(self._python_symbols(file_path, source, lines))
        elif language in {"javascript", "typescript"}:
            symbols.extend(self._js_symbols(file_path, source, lines, language))
        elif language == "java":
            symbols.extend(self._java_symbols(file_path, source, lines))
        elif language == "go":
            symbols.extend(self._go_symbols(file_path, source, lines))
        elif language in {"c", "cpp"}:
            symbols.extend(self._c_symbols(file_path, source, lines, language))
        if not symbols:
            symbols.append(
                ExtractedSymbol(
                    symbol_type=SymbolType.FILE,
                    symbol_name=file_path.rsplit("/", 1)[-1],
                    qualified_name=file_path,
                    start_line=1,
                    end_line=max(1, len(lines)),
                    code=source[:4000],
                    language=language,
                    file_path=file_path,
                    module_name=file_path,
                )
            )
        return ParseResult(
            file_path=file_path,
            language=language,
            parser_capability=ParserCapability.TEXT_FALLBACK,
            symbols=symbols,
        )

    def _python_symbols(self, file_path: str, source: str, lines: list[str]) -> list[ExtractedSymbol]:
        symbols: list[ExtractedSymbol] = []
        class_stack: list[tuple[int, str]] = []
        combined = list(_PY_CLASS.finditer(source)) + list(_PY_DEF.finditer(source))
        combined.sort(key=lambda m: m.start())
        for match in combined:
            indent = len(match.group(1).replace("\t", "    "))
            name = match.group(2)
            start_line = source[: match.start()].count("\n") + 1
            while class_stack and class_stack[-1][0] >= indent:
                class_stack.pop()
            is_class = match.re is _PY_CLASS
            parent = class_stack[-1][1] if class_stack else None
            if is_class:
                class_stack.append((indent, name))
                symbol_type = SymbolType.CLASS
                qualified = name
            else:
                symbol_type = SymbolType.METHOD if parent else SymbolType.FUNCTION
                qualified = f"{parent}.{name}" if parent else name
            end_line = _block_end(lines, start_line, indent)
            symbols.append(
                _symbol(file_path, "python", symbol_type, name, qualified, start_line, end_line, lines, parent)
            )
        return symbols

    def _js_symbols(self, file_path: str, source: str, lines: list[str], language: str) -> list[ExtractedSymbol]:
        symbols: list[ExtractedSymbol] = []
        for match in _JS_CLASS.finditer(source):
            start_line = source[: match.start()].count("\n") + 1
            name = match.group(1)
            end_line = _brace_end(lines, start_line)
            symbols.append(_symbol(file_path, language, SymbolType.CLASS, name, name, start_line, end_line, lines, None))
        for match in _JS_FN.finditer(source):
            start_line = source[: match.start()].count("\n") + 1
            name = match.group(1)
            end_line = _brace_end(lines, start_line)
            symbols.append(
                _symbol(file_path, language, SymbolType.FUNCTION, name, name, start_line, end_line, lines, None)
            )
        return symbols

    def _java_symbols(self, file_path: str, source: str, lines: list[str]) -> list[ExtractedSymbol]:
        symbols: list[ExtractedSymbol] = []
        class_name = None
        for match in _JAVA_CLASS.finditer(source):
            class_name = match.group(1)
            start_line = source[: match.start()].count("\n") + 1
            end_line = _brace_end(lines, start_line)
            symbols.append(
                _symbol(file_path, "java", SymbolType.CLASS, class_name, class_name, start_line, end_line, lines, None)
            )
        for match in _JAVA_METHOD.finditer(source):
            name = match.group(1)
            if name in {"if", "for", "while", "switch", "catch", "return"}:
                continue
            start_line = source[: match.start()].count("\n") + 1
            end_line = _brace_end(lines, start_line)
            qualified = f"{class_name}.{name}" if class_name else name
            symbols.append(
                _symbol(
                    file_path,
                    "java",
                    SymbolType.METHOD if class_name else SymbolType.FUNCTION,
                    name,
                    qualified,
                    start_line,
                    end_line,
                    lines,
                    class_name,
                )
            )
        return symbols

    def _go_symbols(self, file_path: str, source: str, lines: list[str]) -> list[ExtractedSymbol]:
        symbols: list[ExtractedSymbol] = []
        for match in _GO_FN.finditer(source):
            name = match.group(1)
            start_line = source[: match.start()].count("\n") + 1
            end_line = _brace_end(lines, start_line)
            symbols.append(
                _symbol(file_path, "go", SymbolType.FUNCTION, name, name, start_line, end_line, lines, None)
            )
        return symbols

    def _c_symbols(self, file_path: str, source: str, lines: list[str], language: str) -> list[ExtractedSymbol]:
        symbols: list[ExtractedSymbol] = []
        for match in _C_FN.finditer(source):
            name = match.group(1)
            start_line = source[: match.start()].count("\n") + 1
            end_line = _brace_end(lines, start_line)
            symbols.append(
                _symbol(file_path, language, SymbolType.FUNCTION, name, name, start_line, end_line, lines, None)
            )
        return symbols


def _symbol(
    file_path: str,
    language: str,
    symbol_type: str,
    name: str,
    qualified: str,
    start_line: int,
    end_line: int,
    lines: list[str],
    parent: str | None,
) -> ExtractedSymbol:
    snippet = "\n".join(lines[start_line - 1 : end_line])
    return ExtractedSymbol(
        symbol_type=symbol_type,
        symbol_name=name,
        qualified_name=qualified,
        class_name=parent,
        module_name=file_path,
        start_line=start_line,
        end_line=end_line,
        code=snippet,
        language=language,
        file_path=file_path,
        parent_symbol=parent,
    )


def _block_end(lines: list[str], start_line: int, indent: int) -> int:
    end = start_line
    for idx in range(start_line, len(lines)):
        line = lines[idx]
        if not line.strip():
            end = idx + 1
            continue
        current = len(line) - len(line.lstrip(" \t"))
        if current <= indent and line.strip():
            break
        end = idx + 1
    return max(end, start_line)


def _brace_end(lines: list[str], start_line: int) -> int:
    depth = 0
    started = False
    for idx in range(start_line - 1, len(lines)):
        depth += lines[idx].count("{") - lines[idx].count("}")
        if "{" in lines[idx]:
            started = True
        if started and depth <= 0:
            return idx + 1
    return len(lines) or start_line


def content_hash(text: str) -> str:
    return sha256(text.encode("utf-8", errors="replace")).hexdigest()
