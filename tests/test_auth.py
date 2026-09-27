from unittest.mock import Mock

import pytest
from fastmcp.server.auth import AccessToken, AuthContext
from pydantic import ValidationError

from ynab_mcp.auth import allow_github_logins
from ynab_mcp.config import Settings


def _ctx(login: str | None) -> AuthContext:
    token = None
    if login is not None:
        token = AccessToken(token="t", client_id="c", scopes=[], claims={"login": login})
    return AuthContext(token=token, component=Mock())


def test_allowlist_accepts_listed_login_case_insensitively() -> None:
    check = allow_github_logins(["octocat"])
    assert check(_ctx("octocat"))
    assert check(_ctx("OctoCat"))


def test_allowlist_rejects_other_logins_and_anonymous() -> None:
    check = allow_github_logins(["octocat"])
    assert not check(_ctx("someone-else"))
    assert not check(_ctx(None))


def test_settings_require_auth_config_unless_disabled() -> None:
    with pytest.raises(ValidationError, match="GITHUB_CLIENT_ID"):
        Settings(_env_file=None, ynab_access_token="x")

    Settings(_env_file=None, ynab_access_token="x", auth_disabled=True)


def test_settings_parse_comma_separated_logins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOWED_GITHUB_LOGINS", "Alice, bob")
    settings = Settings(_env_file=None, ynab_access_token="x", auth_disabled=True)
    assert settings.allowed_github_logins == ["alice", "bob"]
