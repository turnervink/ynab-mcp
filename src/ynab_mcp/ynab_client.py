from decimal import Decimal
from typing import Any

import httpx
from fastmcp.exceptions import ToolError

YNAB_API_URL = "https://api.ynab.com/v1"


class YnabClient:
    """Thin async wrapper around the YNAB REST API (https://api.ynab.com).

    Returns the `data` payload of each response and turns API failures into
    `ToolError`s so the agent sees a readable message.
    """

    def __init__(self, access_token: str, base_url: str = YNAB_API_URL) -> None:
        self._access_token = access_token
        self._base_url = base_url
        self._http: httpx.AsyncClient | None = None

    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                base_url=self._base_url,
                headers={"Authorization": f"Bearer {self._access_token}"},
                timeout=30.0,
            )
        return self._http

    async def aclose(self) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._request("GET", path, params=params)

    async def post(self, path: str, json: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", path, json=json)

    async def put(self, path: str, json: dict[str, Any]) -> dict[str, Any]:
        return await self._request("PUT", path, json=json)

    async def patch(self, path: str, json: dict[str, Any]) -> dict[str, Any]:
        return await self._request("PATCH", path, json=json)

    async def delete(self, path: str) -> dict[str, Any]:
        return await self._request("DELETE", path)

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = await self._client().request(method, path, **kwargs)
        except httpx.HTTPError as e:
            raise ToolError(f"Could not reach YNAB: {e}") from e

        if response.status_code == 429:
            raise ToolError(
                "YNAB rate limit reached (200 requests per hour per token). Try again later."
            )
        if response.is_error:
            raise ToolError(f"YNAB API error {response.status_code}: {_error_detail(response)}")
        return response.json()["data"]


def _error_detail(response: httpx.Response) -> str:
    try:
        error = response.json()["error"]
        return f"{error['name']}: {error['detail']}"
    except (ValueError, KeyError, TypeError):
        return response.text or response.reason_phrase


def from_milliunits(milliunits: int) -> float:
    """YNAB amounts are integers in thousandths of a currency unit."""
    return milliunits / 1000


def to_milliunits(amount: float | Decimal | str) -> int:
    return int((Decimal(str(amount)) * 1000).to_integral_value())
