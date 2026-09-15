from enum import StrEnum


class IndexStatus(StrEnum):
    QUEUED = "QUEUED"
    CLONING = "CLONING"
    SCANNING = "SCANNING"
    PARSING = "PARSING"
    EXTRACTING_SYMBOLS = "EXTRACTING_SYMBOLS"
    BUILDING_GRAPH = "BUILDING_GRAPH"
    GENERATING_EMBEDDINGS = "GENERATING_EMBEDDINGS"
    INDEXING = "INDEXING"
    VALIDATING = "VALIDATING"
    READY = "READY"
    FAILED = "FAILED"


class SymbolType(StrEnum):
    FILE = "file"
    MODULE = "module"
    CLASS = "class"
    INTERFACE = "interface"
    STRUCT = "struct"
    ENUM = "enum"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"
    CONSTANT = "constant"
    ENDPOINT = "endpoint"
    CONFIGURATION = "configuration"
    TEST = "test"
    DOCUMENTATION = "documentation"
    IMPORT = "import"
    UNKNOWN = "unknown"


class RelationType(StrEnum):
    IMPORTS = "IMPORTS"
    CALLS = "CALLS"
    DEFINES = "DEFINES"
    CONTAINS = "CONTAINS"
    EXTENDS = "EXTENDS"
    IMPLEMENTS = "IMPLEMENTS"
    USES = "USES"
    REFERENCES = "REFERENCES"
    ROUTES_TO = "ROUTES_TO"
    TESTS = "TESTS"
    CONFIGURES = "CONFIGURES"
    DEPENDS_ON = "DEPENDS_ON"


class QueryIntent(StrEnum):
    LOCATION = "LOCATION"
    EXPLANATION = "EXPLANATION"
    ARCHITECTURE = "ARCHITECTURE"
    FLOW = "FLOW"
    DEPENDENCY = "DEPENDENCY"
    IMPACT = "IMPACT"
    DEBUGGING = "DEBUGGING"
    CONFIGURATION = "CONFIGURATION"
    SYMBOL_LOOKUP = "SYMBOL_LOOKUP"
    DOCUMENTATION = "DOCUMENTATION"
    ONBOARDING = "ONBOARDING"
    COMPARISON = "COMPARISON"
    GENERAL_CODEBASE_QA = "GENERAL_CODEBASE_QA"


class EvidenceKind(StrEnum):
    CONFIRMED = "CONFIRMED_FROM_CODE"
    INFERRED = "INFERRED_FROM_CODE"
    NOT_FOUND = "NOT_FOUND"


class ParserCapability(StrEnum):
    TREE_SITTER = "tree_sitter"
    TEXT_FALLBACK = "text_fallback"
    SKIPPED = "skipped"
