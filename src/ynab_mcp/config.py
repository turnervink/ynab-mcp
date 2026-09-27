from typing import Annotated, Self

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Redirect URIs that MCP clients may register via DCR. Claude's hosted connector
# callback, plus loopback for Claude Code / MCP Inspector during local testing.
DEFAULT_CLIENT_REDIRECT_URIS = [
    "https://claude.ai/api/mcp/auth_callback",
    "https://claude.com/api/mcp/auth_callback",
    "http://localhost:*",
    "http://127.0.0.1:*",
]


class Settings(BaseSettings):
    """Server configuration, loaded from environment variables and `.env`."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # YNAB
    ynab_access_token: SecretStr
    ynab_default_plan_id: str = "last-used"

    # HTTP
    host: str = "0.0.0.0"
    port: int = 8000

    # Auth (GitHub OAuth via FastMCP's OAuth proxy)
    auth_disabled: bool = False
    base_url: str | None = None
    github_client_id: str | None = None
    github_client_secret: SecretStr | None = None
    jwt_signing_key: SecretStr | None = None
    allowed_github_logins: Annotated[list[str], NoDecode] = []
    allowed_client_redirect_uris: Annotated[list[str], NoDecode] = DEFAULT_CLIENT_REDIRECT_URIS

    @field_validator("allowed_github_logins", "allowed_client_redirect_uris", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("allowed_github_logins")
    @classmethod
    def _lowercase_logins(cls, value: list[str]) -> list[str]:
        # GitHub logins are case-insensitive.
        return [login.lower() for login in value]

    @model_validator(mode="after")
    def _require_auth_config(self) -> Self:
        if self.auth_disabled:
            return self
        required = {
            "BASE_URL": self.base_url,
            "GITHUB_CLIENT_ID": self.github_client_id,
            "GITHUB_CLIENT_SECRET": self.github_client_secret,
            "JWT_SIGNING_KEY": self.jwt_signing_key,
            "ALLOWED_GITHUB_LOGINS": self.allowed_github_logins,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(
                f"Missing auth settings: {', '.join(missing)}. "
                "Set them, or set AUTH_DISABLED=true for local development only."
            )
        return self
