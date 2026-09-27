import pytest
import respx
from fastmcp import Client

from ynab_mcp.config import Settings
from ynab_mcp.server import create_server
from ynab_mcp.ynab_client import YNAB_API_URL

PAYEES = [
    {"id": "p-london", "name": "London Drugs", "transfer_account_id": None, "deleted": False},
    {"id": "p-old", "name": "London Fog Cafe", "transfer_account_id": None, "deleted": True},
    {
        "id": "p-transfer",
        "name": "Transfer : Savings",
        "transfer_account_id": "acct-1",
        "deleted": False,
    },
]


@pytest.fixture
def client() -> Client:
    settings = Settings(_env_file=None, ynab_access_token="test-token", auth_disabled=True)
    return Client(create_server(settings))


@pytest.fixture
def payees_route() -> respx.Route:
    with respx.mock:
        yield respx.get(f"{YNAB_API_URL}/plans/last-used/payees").respond(
            json={"data": {"payees": PAYEES, "server_knowledge": 1}}
        )


async def test_list_payees_skips_deleted_and_transfers(
    client: Client, payees_route: respx.Route
) -> None:
    async with client:
        result = await client.call_tool("list_payees", {})

    assert result.data == [{"id": "p-london", "name": "London Drugs"}]


async def test_list_payees_can_include_transfers(client: Client, payees_route: respx.Route) -> None:
    async with client:
        result = await client.call_tool("list_payees", {"include_transfers": True})

    assert result.data == [
        {"id": "p-london", "name": "London Drugs"},
        {"id": "p-transfer", "name": "Transfer : Savings", "transfer_account_id": "acct-1"},
    ]
