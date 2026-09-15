from pathlib import Path

from app.parsing import parse_source

FIXTURE = Path(__file__).parent / "fixtures" / "auth_service.py"


def test_python_tree_sitter_extracts_class_and_methods():
    source = FIXTURE.read_text(encoding="utf-8")
    result = parse_source("src/auth/auth_service.py", source, "python")
    names = {symbol.qualified_name: symbol for symbol in result.symbols}
    assert "AuthService" in names
    assert "AuthService.authenticate_user" in names
    assert "AuthService.find_user" in names
    assert "AuthService.issue_token" in names
    assert "helper" in names
    auth = names["AuthService.authenticate_user"]
    assert auth.start_line == 4
    assert auth.end_line >= 8
    assert "def authenticate_user" in auth.code
    cls = names["AuthService"]
    assert cls.start_line == 1
    assert result.parser_capability == "tree_sitter"


def test_malformed_python_does_not_raise():
    result = parse_source("bad.py", "def broken(\n", "python")
    assert result.file_path == "bad.py"
    assert result.symbols
