class AuthService:
    """Handles user authentication."""

    def authenticate_user(self, email: str, password: str) -> str:
        user = self.find_user(email)
        if not user:
            raise ValueError("unknown user")
        return self.issue_token(user)

    def find_user(self, email: str) -> dict | None:
        return {"email": email}

    def issue_token(self, user: dict) -> str:
        return "token"


def helper():
    return True
