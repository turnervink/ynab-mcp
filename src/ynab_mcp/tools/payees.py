from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from ynab_mcp.config import Settings
from ynab_mcp.tools.plans import PlanId
from ynab_mcp.ynab_client import YnabClient


def register(mcp: FastMCP, ynab: YnabClient, settings: Settings) -> None:
    @mcp.tool(annotations={"readOnlyHint": True})
    async def list_payees(
        plan_id: PlanId = None,
        include_transfers: Annotated[
            bool,
            Field(description="Include transfer payees (moves between the user's own accounts)."),
        ] = False,
    ) -> list[dict[str, Any]]:
        """List the payees in a plan, for matching transaction names to existing payees.

        Bank descriptions rarely match payee names exactly, so match them using
        your own judgement, e.g. "LONDON DRUGS #123" → "London Drugs",
        "SBUX 1234" → "Starbucks", "AMZN MKTP CA*2K3" → "Amazon". Ignore store
        numbers, locations and card-processor prefixes like "SQ *" or "TST*".

        If no payee clearly fits, or several could, show the user the likely
        options and ask which to use, or whether to create a new payee. Don't
        guess. Call this once and reuse the list for every transaction you match.
        """
        plan = plan_id or settings.ynab_default_plan_id
        data = await ynab.get(f"/plans/{plan}/payees")
        payees = []
        for p in data["payees"]:
            if p.get("deleted"):
                continue
            if p.get("transfer_account_id"):
                if include_transfers:
                    payees.append(
                        {
                            "id": p["id"],
                            "name": p["name"],
                            "transfer_account_id": p["transfer_account_id"],
                        }
                    )
                continue
            payees.append({"id": p["id"], "name": p["name"]})
        return payees
