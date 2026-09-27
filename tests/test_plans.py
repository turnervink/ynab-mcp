import httpx
import pytest
import respx
from fastmcp import Client
from fastmcp.exceptions import ToolError

from ynab_mcp.config import Settings
from ynab_mcp.server import create_server
from ynab_mcp.ynab_client import YNAB_API_URL

PLAN_ID = "11111111-2222-3333-4444-555555555555"


@pytest.fixture
def client() -> Client:
    settings = Settings(_env_file=None, ynab_access_token="test-token", auth_disabled=True)
    return Client(create_server(settings))


async def test_lists_tools(client: Client) -> None:
    async with client:
        names = {tool.name for tool in await client.list_tools()}
    assert {"list_plans", "get_month_summary"} <= names


@respx.mock
async def test_list_plans(client: Client) -> None:
    route = respx.get(f"{YNAB_API_URL}/plans").respond(
        json={
            "data": {
                "plans": [
                    {
                        "id": PLAN_ID,
                        "name": "Household",
                        "last_modified_on": "2026-09-01T00:00:00Z",
                        "currency_format": {"iso_code": "USD"},
                    }
                ]
            }
        }
    )
    async with client:
        result = await client.call_tool("list_plans", {})

    assert route.calls.last.request.headers["Authorization"] == "Bearer test-token"
    assert result.data == [
        {
            "id": PLAN_ID,
            "name": "Household",
            "last_modified_on": "2026-09-01T00:00:00Z",
            "currency": "USD",
        }
    ]


@respx.mock
async def test_get_month_summary_converts_milliunits(client: Client) -> None:
    respx.get(f"{YNAB_API_URL}/plans/last-used/months/current").respond(
        json={
            "data": {
                "month": {
                    "month": "2026-09-01",
                    "income": 5_000_000,
                    "budgeted": 4_250_500,
                    "activity": -1_234_560,
                    "to_be_budgeted": 749_500,
                    "age_of_money": 42,
                    "note": None,
                    "deleted": False,
                }
            }
        }
    )
    async with client:
        result = await client.call_tool("get_month_summary", {})

    assert result.data["income"] == 5000.0
    assert result.data["assigned"] == 4250.5
    assert result.data["activity"] == -1234.56
    assert result.data["ready_to_assign"] == 749.5


@respx.mock
async def test_ynab_errors_become_tool_errors(client: Client) -> None:
    respx.get(f"{YNAB_API_URL}/plans").mock(
        return_value=httpx.Response(
            401, json={"error": {"id": "401", "name": "unauthorized", "detail": "Unauthorized"}}
        )
    )
    async with client:
        with pytest.raises(ToolError, match="unauthorized: Unauthorized"):
            await client.call_tool("list_plans", {})


async def test_rejects_invalid_plan_id(client: Client) -> None:
    async with client:
        with pytest.raises(ToolError):
            await client.call_tool("get_month_summary", {"plan_id": "../user"})
