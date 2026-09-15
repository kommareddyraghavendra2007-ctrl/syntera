from pathlib import Path

from app.ingestion.filters import classify_file, detect_language, should_ignore_relative_path
from app.ingestion.scanner import scan_repository_files


def test_ignores_vendor_and_build_directories():
    assert should_ignore_relative_path("node_modules/lodash/index.js")
    assert should_ignore_relative_path("backend/__pycache__/x.pyc")
    assert should_ignore_relative_path("dist/bundle.js")
    assert should_ignore_relative_path("target/classes/App.class")
    assert should_ignore_relative_path("build/output.bin")


def test_keeps_source_and_important_context():
    assert not should_ignore_relative_path("src/auth/AuthService.py")
    assert not should_ignore_relative_path("README.md")
    assert not should_ignore_relative_path("package.json")
    assert not should_ignore_relative_path("pyproject.toml")
    assert not should_ignore_relative_path("Dockerfile")


def test_language_detection():
    assert detect_language("src/main.py") == "python"
    assert detect_language("src/app.ts") == "typescript"
    assert detect_language("src/App.java") == "java"
    assert detect_language("readme.md") is None


def test_classify_secret_and_tests():
    assert classify_file(".env") == "secret"
    assert classify_file("tests/test_auth.py") == "test"
    assert classify_file("src/auth.py") == "source"


def test_scanner_skips_ignored_and_finds_source(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("def ping():\n    return 1\n", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "lib.js").write_text("module.exports = 1", encoding="utf-8")
    (tmp_path / "README.md").write_text("# demo", encoding="utf-8")
    files = scan_repository_files(tmp_path)
    paths = {item.path for item in files}
    assert "src/app.py" in paths
    assert "README.md" in paths
    assert "node_modules/lib.js" not in paths
