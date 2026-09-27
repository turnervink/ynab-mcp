from fastmcp.server.auth import AuthCheck, AuthContext
from fastmcp.server.auth.providers.github import GitHubProvider

from ynab_mcp.config import Settings


def build_github_auth(settings: Settings) -> GitHubProvider:
    """GitHub login, exposed to MCP clients as OAuth 2.1 + DCR by FastMCP's OAuth proxy.

    Client registrations and tokens are stored encrypted (keyed off JWT_SIGNING_KEY)
    under FASTMCP_HOME, which must be on persistent storage so logins survive restarts.
    """
    assert settings.github_client_id and settings.github_client_secret
    assert settings.base_url and settings.jwt_signing_key
    return GitHubProvider(
        client_id=settings.github_client_id,
        client_secret=settings.github_client_secret.get_secret_value(),
        base_url=settings.base_url,
        jwt_signing_key=settings.jwt_signing_key.get_secret_value(),
        # Only need to read the user's login; the default ("user") grants profile write.
        required_scopes=["read:user"],
        allowed_client_redirect_uris=settings.allowed_client_redirect_uris,
    )


def allow_github_logins(logins: list[str]) -> AuthCheck:
    """Auth check that only passes for the given GitHub usernames.

    GitHub will authenticate *any* GitHub user, so this is what actually keeps
    the server private.
    """
    allowed = {login.lower() for login in logins}

    def check(ctx: AuthContext) -> bool:
        if ctx.token is None:
            return False
        login = ctx.token.claims.get("login")
        return isinstance(login, str) and login.lower() in allowed

    return check
