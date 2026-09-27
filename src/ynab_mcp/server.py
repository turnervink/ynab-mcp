from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastmcp import FastMCP
from fastmcp.server.middleware import AuthMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from ynab_mcp.auth import allow_github_logins, build_github_auth
from ynab_mcp.config import Settings
from ynab_mcp.tools import register_all
from ynab_mcp.ynab_client import YnabClient

INSTRUCTIONS = """\
Tools for reading and managing the user's YNAB (You Need A Budget) data.
YNAB now calls budgets "plans". Amounts returned by tools are in currency units.
Call list_plans first if you need a plan ID; otherwise tools default to the user's last-used plan.
"""


def create_server(settings: Settings | None = None) -> FastMCP:
    settings = settings or Settings()
    ynab = YnabClient(settings.ynab_access_token.get_secret_value())

    @asynccontextmanager
    async def lifespan(_: FastMCP) -> AsyncIterator[None]:
        try:
            yield
        finally:
            await ynab.aclose()

    auth = None
    middleware = []
    if not settings.auth_disabled:
        auth = build_github_auth(settings)
        middleware.append(AuthMiddleware(auth=allow_github_logins(settings.allowed_github_logins)))

    mcp = FastMCP(
        "YNAB",
        instructions=INSTRUCTIONS,
        auth=auth,
        middleware=middleware,
        lifespan=lifespan,
    )

    @mcp.custom_route("/health", methods=["GET"])
    async def health(_: Request) -> PlainTextResponse:
        return PlainTextResponse("ok")

    register_all(mcp, ynab, settings)
    return mcp
