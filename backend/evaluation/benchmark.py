"""
Evaluation benchmark — labeled questions against the golden repository.

Each question has:
  - question: natural language query
  - intent: expected QueryIntent
  - expected_symbols: list of qualified names that MUST appear in top-K results
  - expected_files: list of file paths that MUST appear in citations
  - category: string tag for grouping results
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class BenchmarkQuestion:
    question: str
    intent: str
    expected_symbols: list[str]
    expected_files: list[str]
    category: str
    notes: str = ""


GOLDEN_BENCHMARK: list[BenchmarkQuestion] = [
    BenchmarkQuestion(
        question="Where is authentication implemented?",
        intent="LOCATION",
        expected_symbols=["AuthService", "AuthService.authenticate_user", "AuthService.login"],
        expected_files=["src/auth/auth_service.py"],
        category="location",
    ),
    BenchmarkQuestion(
        question="Where is database configuration?",
        intent="CONFIGURATION",
        expected_symbols=["Settings", "Settings.from_env"],
        expected_files=["src/config/settings.py", "src/database/connection.py"],
        category="configuration",
    ),
    BenchmarkQuestion(
        question="How does login work?",
        intent="FLOW",
        expected_symbols=["AuthService.login", "AuthService.authenticate_user", "JWTService.generate_access_token"],
        expected_files=["src/auth/auth_service.py", "src/auth/jwt_service.py"],
        category="flow",
    ),
    BenchmarkQuestion(
        question="Trace user registration",
        intent="FLOW",
        expected_symbols=["AuthService.register", "UserRepository.create"],
        expected_files=["src/auth/auth_service.py", "src/users/user_repository.py"],
        category="flow",
    ),
    BenchmarkQuestion(
        question="What calls AuthService?",
        intent="DEPENDENCY",
        expected_symbols=["AuthService"],
        expected_files=["src/api/auth.py"],
        category="dependency",
    ),
    BenchmarkQuestion(
        question="What does UserRepository do?",
        intent="EXPLANATION",
        expected_symbols=["UserRepository"],
        expected_files=["src/users/user_repository.py"],
        category="explanation",
    ),
    BenchmarkQuestion(
        question="Where is JWT generated?",
        intent="LOCATION",
        expected_symbols=["JWTService.generate_access_token", "JWTService.generate_refresh_token"],
        expected_files=["src/auth/jwt_service.py"],
        category="location",
    ),
    BenchmarkQuestion(
        question="Where is JWT validated?",
        intent="LOCATION",
        expected_symbols=["JWTService.decode_access_token"],
        expected_files=["src/auth/jwt_service.py"],
        category="location",
    ),
    BenchmarkQuestion(
        question="Explain the architecture of this repository",
        intent="ARCHITECTURE",
        expected_symbols=[],
        expected_files=["src/auth/auth_service.py", "src/orders/order_service.py", "src/api/app.py"],
        category="architecture",
        notes="Architecture questions may not have exact symbols but should cover main modules.",
    ),
    BenchmarkQuestion(
        question="What happens when an order is created?",
        intent="FLOW",
        expected_symbols=["OrderService.create_order", "OrderRepository.create"],
        expected_files=["src/orders/order_service.py", "src/orders/order_repository.py"],
        category="flow",
    ),
    BenchmarkQuestion(
        question="Which files depend on OrderService?",
        intent="DEPENDENCY",
        expected_symbols=["OrderService"],
        expected_files=["src/api/orders.py"],
        category="dependency",
    ),
    BenchmarkQuestion(
        question="What environment variables does this project require?",
        intent="CONFIGURATION",
        expected_symbols=["Settings.from_env"],
        expected_files=["src/config/settings.py"],
        category="configuration",
    ),
    BenchmarkQuestion(
        question="What should a new developer read first?",
        intent="ONBOARDING",
        expected_symbols=[],
        expected_files=["README.md", "src/api/app.py"],
        category="onboarding",
    ),
    BenchmarkQuestion(
        question="What could be affected if AuthService changes?",
        intent="IMPACT",
        expected_symbols=["AuthService"],
        expected_files=["src/api/auth.py"],
        category="impact",
    ),
    BenchmarkQuestion(
        question="Find the implementation of authenticate_user",
        intent="SYMBOL_LOOKUP",
        expected_symbols=["AuthService.authenticate_user"],
        expected_files=["src/auth/auth_service.py"],
        category="symbol_lookup",
    ),
    BenchmarkQuestion(
        question="How does payment processing work?",
        intent="FLOW",
        expected_symbols=["PaymentService.create_payment_intent", "PaymentService.handle_webhook"],
        expected_files=["src/orders/payment_service.py"],
        category="flow",
    ),
    BenchmarkQuestion(
        question="Where is password hashing implemented?",
        intent="LOCATION",
        expected_symbols=["PasswordService.hash_password", "PasswordService.verify_password"],
        expected_files=["src/auth/password_service.py"],
        category="location",
    ),
    BenchmarkQuestion(
        question="What database tables are involved in order creation?",
        intent="DEPENDENCY",
        expected_symbols=["Order", "OrderItem"],
        expected_files=["src/database/models.py"],
        category="dependency",
    ),
]
