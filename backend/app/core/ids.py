from uuid import uuid5, UUID, NAMESPACE_URL

from app.parsing.types import ExtractedSymbol


def symbol_id(repository_id: str, file_path: str, symbol: ExtractedSymbol) -> str:
    key = "|".join(
        [
            repository_id,
            file_path,
            symbol.symbol_type,
            symbol.qualified_name,
            str(symbol.start_line),
            str(symbol.end_line),
        ]
    )
    return str(uuid5(NAMESPACE_URL, key))


def file_id(repository_id: str, file_path: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"{repository_id}|file|{file_path}"))
