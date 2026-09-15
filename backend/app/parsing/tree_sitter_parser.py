from __future__ import annotations

from functools import lru_cache

from tree_sitter import Language, Node, Parser

from app.core.enums import ParserCapability, SymbolType
from app.core.logging import get_logger
from app.parsing.base import CodeParser
from app.parsing.fallback import TextFallbackParser
from app.parsing.types import ExtractedCall, ExtractedImport, ExtractedRoute, ExtractedSymbol, ParseResult

logger = get_logger(__name__)

ROUTE_DECORATOR_RE = None


def _load_language(name: str) -> Language | None:
    try:
        if name == "python":
            import tree_sitter_python as mod

            return Language(mod.language())
        if name == "javascript":
            import tree_sitter_javascript as mod

            return Language(mod.language())
        if name == "typescript":
            import tree_sitter_typescript as mod

            return Language(mod.language_typescript())
        if name == "tsx":
            import tree_sitter_typescript as mod

            return Language(mod.language_tsx())
        if name == "java":
            import tree_sitter_java as mod

            return Language(mod.language())
        if name == "go":
            import tree_sitter_go as mod

            return Language(mod.language())
        if name == "c":
            import tree_sitter_c as mod

            return Language(mod.language())
        if name == "cpp":
            import tree_sitter_cpp as mod

            return Language(mod.language())
    except Exception as exc:  # pragma: no cover - environment specific
        logger.warning("tree_sitter_language_unavailable", extra={"language": name, "error": str(exc)})
        return None
    return None


@lru_cache(maxsize=16)
def parser_for(language: str) -> Parser | None:
    grammar = language
    if language == "tsx":
        grammar = "tsx"
    lang = _load_language(grammar)
    if lang is None:
        return None
    return Parser(lang)


class TreeSitterParser(CodeParser):
    def __init__(self) -> None:
        self._fallback = TextFallbackParser()

    def supported_languages(self) -> set[str]:
        return {"python", "javascript", "typescript", "tsx", "java", "go", "c", "cpp"}

    def parse(self, file_path: str, source: str, language: str) -> ParseResult:
        grammar = "tsx" if file_path.endswith(".tsx") else language
        parser = parser_for(grammar)
        if parser is None:
            return self._fallback.parse(file_path, source, language)
        try:
            tree = parser.parse(source.encode("utf-8", errors="replace"))
        except Exception as exc:
            result = self._fallback.parse(file_path, source, language)
            result.errors.append(f"tree-sitter parse failed: {exc}")
            return result
        walker = _LanguageWalker(file_path, source, language, tree.root_node)
        try:
            return walker.walk()
        except Exception as exc:
            result = self._fallback.parse(file_path, source, language)
            result.errors.append(f"tree-sitter walk failed: {exc}")
            return result


class _LanguageWalker:
    def __init__(self, file_path: str, source: str, language: str, root: Node) -> None:
        self.file_path = file_path
        self.source = source
        self.lines = source.splitlines()
        self.language = language
        self.root = root
        self.symbols: list[ExtractedSymbol] = []
        self.imports: list[ExtractedImport] = []
        self.calls: list[ExtractedCall] = []
        self.routes: list[ExtractedRoute] = []
        self.class_stack: list[str] = []

    def walk(self) -> ParseResult:
        self._visit(self.root)
        if not self.symbols:
            self.symbols.append(
                ExtractedSymbol(
                    symbol_type=SymbolType.FILE,
                    symbol_name=self.file_path.rsplit("/", 1)[-1],
                    qualified_name=self.file_path,
                    start_line=1,
                    end_line=max(1, len(self.lines)),
                    code=self.source[:4000],
                    language=self.language,
                    file_path=self.file_path,
                    module_name=self.file_path,
                )
            )
        return ParseResult(
            file_path=self.file_path,
            language=self.language,
            parser_capability=ParserCapability.TREE_SITTER,
            symbols=self.symbols,
            imports=self.imports,
            calls=self.calls,
            routes=self.routes,
        )

    def _visit(self, node: Node) -> None:
        handler = {
            "class_definition": self._python_class,
            "function_definition": self._python_function,
            "decorated_definition": self._python_decorated,
            "import_statement": self._python_import,
            "import_from_statement": self._python_import,
            "class_declaration": self._generic_class,
            "class_specifier": self._generic_class,
            "interface_declaration": self._generic_interface,
            "struct_specifier": self._generic_struct,
            "enum_declaration": self._generic_enum,
            "function_declaration": self._generic_function,
            "method_declaration": self._generic_method,
            "method_definition": self._generic_method,
            "constructor_declaration": self._generic_method,
            "function_definition_c": self._c_function,
            "preproc_include": self._c_include,
            "type_declaration": self._go_type,
            "call": self._call,
            "call_expression": self._call,
            "method_invocation": self._call,
        }.get(node.type)

        if node.type == "function_definition" and self.language in {"c", "cpp"}:
            handler = self._c_function

        if handler:
            handler(node)
        else:
            for child in node.children:
                self._visit(child)

    def _python_class(self, node: Node) -> None:
        name = self._field_text(node, "name") or "AnonymousClass"
        symbol = self._make_symbol(SymbolType.CLASS, name, node, parent=None)
        self.symbols.append(symbol)
        self.class_stack.append(name)
        body = node.child_by_field_name("body")
        if body:
            for child in body.children:
                self._visit(child)
        else:
            for child in node.children:
                self._visit(child)
        self.class_stack.pop()

    def _python_function(self, node: Node) -> None:
        name = self._field_text(node, "name") or "anonymous"
        parent = self.class_stack[-1] if self.class_stack else None
        symbol_type = SymbolType.METHOD if parent else SymbolType.FUNCTION
        self.symbols.append(self._make_symbol(symbol_type, name, node, parent=parent))
        for child in node.children:
            if child.type in {"block", "body"}:
                self._visit(child)
            elif child.type == "call":
                self._call(child)

    def _python_decorated(self, node: Node) -> None:
        decorators = [child for child in node.children if child.type == "decorator"]
        definition = next(
            (child for child in node.children if child.type in {"function_definition", "class_definition"}),
            None,
        )
        if definition is None:
            for child in node.children:
                self._visit(child)
            return
        before = len(self.symbols)
        self._visit(definition)
        added = self.symbols[before:]
        for deco in decorators:
            text = self._text(deco)
            route = _route_from_decorator(text, added[-1].symbol_name if added else None, deco.start_point[0] + 1)
            if route:
                self.routes.append(route)
                if added:
                    handler = added[-1]
                    self.symbols.append(
                        ExtractedSymbol(
                            symbol_type=SymbolType.ENDPOINT,
                            symbol_name=f"{route.method} {route.path}",
                            qualified_name=f"{route.method} {route.path}",
                            class_name=handler.class_name,
                            module_name=self.file_path,
                            start_line=handler.start_line,
                            end_line=handler.end_line,
                            code=handler.code,
                            language=self.language,
                            file_path=self.file_path,
                            parent_symbol=handler.qualified_name,
                        )
                    )

    def _python_import(self, node: Node) -> None:
        text = self._text(node)
        module = text.replace("import", "").replace("from", "").strip().split()[0] if text.split() else text
        self.imports.append(ExtractedImport(module=module, start_line=node.start_point[0] + 1))
        names = [self._text(child) for child in node.children if child.type == "dotted_name"]
        if names:
            self.imports[-1] = ExtractedImport(
                module=names[0], names=names[1:], start_line=node.start_point[0] + 1
            )

    def _generic_class(self, node: Node) -> None:
        name = self._field_text(node, "name") or self._identifier(node) or "AnonymousClass"
        self.symbols.append(self._make_symbol(SymbolType.CLASS, name, node, parent=None))
        self.class_stack.append(name)
        for child in node.children:
            self._visit(child)
        self.class_stack.pop()
        super_nodes = node.child_by_field_name("superclass") or node.child_by_field_name("interfaces")
        if super_nodes:
            pass

    def _generic_interface(self, node: Node) -> None:
        name = self._field_text(node, "name") or self._identifier(node) or "AnonymousInterface"
        self.symbols.append(self._make_symbol(SymbolType.INTERFACE, name, node, parent=None))
        self.class_stack.append(name)
        for child in node.children:
            self._visit(child)
        self.class_stack.pop()

    def _generic_struct(self, node: Node) -> None:
        name = self._field_text(node, "name") or self._identifier(node) or "AnonymousStruct"
        self.symbols.append(self._make_symbol(SymbolType.STRUCT, name, node, parent=None))

    def _generic_enum(self, node: Node) -> None:
        name = self._field_text(node, "name") or self._identifier(node) or "AnonymousEnum"
        self.symbols.append(self._make_symbol(SymbolType.ENUM, name, node, parent=None))

    def _generic_function(self, node: Node) -> None:
        name = self._field_text(node, "name") or self._identifier(node) or "anonymous"
        parent = self.class_stack[-1] if self.class_stack else None
        symbol_type = SymbolType.METHOD if parent else SymbolType.FUNCTION
        self.symbols.append(self._make_symbol(symbol_type, name, node, parent=parent))
        for child in node.children:
            self._visit(child)

    def _generic_method(self, node: Node) -> None:
        name = self._field_text(node, "name") or self._identifier(node) or "anonymous"
        parent = self.class_stack[-1] if self.class_stack else None
        self.symbols.append(self._make_symbol(SymbolType.METHOD, name, node, parent=parent))
        for child in node.children:
            self._visit(child)

    def _c_function(self, node: Node) -> None:
        declarator = node.child_by_field_name("declarator")
        name = self._identifier(declarator) if declarator else self._identifier(node)
        name = name or "anonymous"
        self.symbols.append(self._make_symbol(SymbolType.FUNCTION, name, node, parent=None))
        for child in node.children:
            self._visit(child)

    def _c_include(self, node: Node) -> None:
        self.imports.append(ExtractedImport(module=self._text(node), start_line=node.start_point[0] + 1))

    def _go_type(self, node: Node) -> None:
        name = self._field_text(node, "name") or self._identifier(node)
        if name:
            self.symbols.append(self._make_symbol(SymbolType.STRUCT, name, node, parent=None))

    def _call(self, node: Node) -> None:
        function_node = node.child_by_field_name("function") or node.child_by_field_name("name")
        callee = self._text(function_node) if function_node else self._identifier(node)
        if callee:
            simple = callee.split(".")[-1]
            self.calls.append(
                ExtractedCall(callee=simple, start_line=node.start_point[0] + 1, confidence=0.55)
            )
        for child in node.children:
            if child.type in {"call", "call_expression", "method_invocation"}:
                self._call(child)
            elif child.children:
                for grandchild in child.children:
                    if grandchild.type in {"call", "call_expression", "method_invocation"}:
                        self._call(grandchild)

    def _make_symbol(self, symbol_type: str, name: str, node: Node, parent: str | None) -> ExtractedSymbol:
        qualified = f"{parent}.{name}" if parent else name
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        start_col = node.start_point[1]
        end_col = node.end_point[1]
        doc = _leading_doc(node, self.source)
        return ExtractedSymbol(
            symbol_type=symbol_type,
            symbol_name=name,
            qualified_name=qualified,
            class_name=parent,
            module_name=self.file_path,
            start_line=start_line,
            end_line=end_line,
            start_column=start_col,
            end_column=end_col,
            code=self._text(node),
            documentation=doc,
            parent_symbol=parent,
            language=self.language,
            file_path=self.file_path,
        )

    def _field_text(self, node: Node, field: str) -> str | None:
        child = node.child_by_field_name(field)
        return self._text(child) if child else None

    def _identifier(self, node: Node | None) -> str | None:
        if node is None:
            return None
        if node.type in {"identifier", "type_identifier", "property_identifier", "field_identifier"}:
            return self._text(node)
        for child in node.children:
            found = self._identifier(child)
            if found:
                return found
        return None

    def _text(self, node: Node) -> str:
        return self.source[node.start_byte : node.end_byte]


def _leading_doc(node: Node, source: str) -> str | None:
    if not node.children:
        return None
    for child in node.children:
        if child.type in {"expression_statement", "block", "body"}:
            for grandchild in child.children:
                if grandchild.type == "string" or grandchild.type == "expression_statement":
                    text = source[grandchild.start_byte : grandchild.end_byte].strip()
                    if text.startswith(('"""', "'''")):
                        return text.strip("\"'")
        if child.type == "string":
            text = source[child.start_byte : child.end_byte]
            if text.startswith(('"""', "'''")):
                return text.strip("\"'")
    return None


def _route_from_decorator(text: str, handler: str | None, line: int) -> ExtractedRoute | None:
    import re

    match = re.search(
        r"@(?:app|router|api)\.(get|post|put|patch|delete|options|head)\(\s*['\"]([^'\"]+)['\"]",
        text,
        re.I,
    )
    if not match:
        match = re.search(
            r"@(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping|RequestMapping)\(\s*['\"]([^'\"]+)['\"]",
            text,
        )
    if not match:
        return None
    method = match.group(1).upper().replace("MAPPING", "").replace("REQUEST", "GET")
    if method == "REQUEST":
        method = "GET"
    return ExtractedRoute(method=method, path=match.group(2), handler=handler, start_line=line, framework="detected")
