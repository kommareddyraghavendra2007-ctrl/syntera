from app.parsing.fallback import TextFallbackParser
from app.parsing.tree_sitter_parser import TreeSitterParser
from app.parsing.types import ParseResult

_tree = TreeSitterParser()
_fallback = TextFallbackParser()


def parse_source(file_path: str, source: str, language: str | None) -> ParseResult:
    lang = language or "text"
    if lang in _tree.supported_languages() or file_path.endswith(".tsx"):
        return _tree.parse(file_path, source, lang if lang != "tsx" else "typescript")
    return _fallback.parse(file_path, source, lang)
