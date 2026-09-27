# ynab-mcp

A personal [FastMCP](https://gofastmcp.com) server that lets Claude read and manage a YNAB budget. It runs on a home server behind a Cloudflare Tunnel and is gated by GitHub OAuth plus an allowlist of GitHub usernames.

## How auth works

```
Claude ──OAuth 2.1 + DCR──▶ ynab-mcp (FastMCP OAuth proxy) ──OAuth──▶ GitHub
                               │
                               └── Personal Access Token ──▶ YNAB API
```

- Claude's custom connectors need an MCP server that supports OAuth discovery and Dynamic Client Registration. GitHub doesn't support DCR, so FastMCP's `GitHubProvider` provides it and sends the actual login to your GitHub OAuth App.
- GitHub will authenticate *any* GitHub user. `ALLOWED_GITHUB_LOGINS` is what keeps the server private: every tool, resource and prompt is checked against that list in `AuthMiddleware`.
- The server talks to YNAB with your Personal Access Token. Claude never sees it.
- OAuth state (client registrations, tokens) is stored encrypted under `FASTMCP_HOME` (`/data/fastmcp` in the container, on a named volume).
- Don't put Cloudflare Access in front of this hostname. Claude's connector backend can't complete an Access login.

## Setup

1. **YNAB token.** Create one in YNAB under Settings → Developer Settings → New Token.
2. **Cloudflare Tunnel.** In Zero Trust → Networks → Tunnels, create a tunnel and copy its token. Add a public hostname (for example `ynab-mcp.example.com`) that points to service `http://ynab-mcp:8000`.
3. **GitHub OAuth App.** Create one at https://github.com/settings/developers → New OAuth App:
   - Homepage URL: `https://ynab-mcp.example.com`
   - Authorization callback URL: `https://ynab-mcp.example.com/auth/callback`
4. **Configure.** Run `cp .env.example .env` and fill it in. Generate `JWT_SIGNING_KEY` with `openssl rand -hex 32`.
5. **Run.** `docker compose up -d --build`, then check `https://ynab-mcp.example.com/health` returns `ok`.
6. **Connect Claude.** In Settings → Connectors → Add custom connector, use URL `https://ynab-mcp.example.com/mcp`. Sign in with GitHub when prompted.

## Development

Requires Python 3.12+ and [Poetry](https://python-poetry.org) 2.x. The virtualenv lives in `.venv/` (see `poetry.toml`).

```sh
poetry install
poetry run pytest
poetry run ruff check . && poetry run ruff format .

# Add dependencies
poetry add <package>
poetry add --group dev <package>

# Run locally without OAuth (never expose this):
AUTH_DISABLED=true YNAB_ACCESS_TOKEN=... poetry run python -m ynab_mcp
npx @modelcontextprotocol/inspector   # connect to http://localhost:8000/mcp
```

To test OAuth locally, make a second GitHub OAuth App with callback `http://localhost:8000/auth/callback` and set `BASE_URL=http://localhost:8000`.

## Adding a tool

1. Add a module in `src/ynab_mcp/tools/` with a `register(mcp, ynab, settings)` function, following [`plans.py`](src/ynab_mcp/tools/plans.py). Register it in [`tools/__init__.py`](src/ynab_mcp/tools/__init__.py).
2. Use `ynab.get/post/put/patch/delete` from [`ynab_client.py`](src/ynab_mcp/ynab_client.py). Paths follow the [YNAB API](https://api.ynab.com), where budgets are now called `/plans/{plan_id}`. API errors surface to the agent as `ToolError`s.
3. YNAB amounts are milliunits. Convert with `from_milliunits` / `to_milliunits`, and return compact dicts rather than raw API payloads, because agents do better with less noise.
4. Annotate read-only tools with `annotations={"readOnlyHint": True}`, and destructive ones with `{"destructiveHint": True}`.
5. Validate IDs that go into URL paths. Reuse the `PlanId` type.
6. Add a test in `tests/` that mocks YNAB with `respx`.

The YNAB API allows 200 requests per hour per token. Prefer endpoints that return a lot per call, such as `/plans/{id}/categories` or `/plans/{id}/transactions?since_date=...`, over one call per item.
