from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from ynab_mcp.config import Settings
from ynab_mcp.ynab_client import YnabClient, from_milliunits

# Plan IDs are UUIDs, or the aliases YNAB accepts. Validated so model-supplied
# values can't reach other API paths.
PlanId = Annotated[
    str | None,
    Field(
        description='Plan ID from list_plans, or "last-used". Defaults to the configured plan.',
        pattern=r"^([0-9a-fA-F-]{36}|last-used|default)$",
    ),
]
Month = Annotated[
    str,
    Field(
        description='Month as YYYY-MM-01, or "current" for the current calendar month (UTC).',
        pattern=r"^(current|\d{4}-\d{2}-01)$",
    ),
]


def register(mcp: FastMCP, ynab: YnabClient, settings: Settings) -> None:
    @mcp.tool(annotations={"readOnlyHint": True})
    async def list_plans() -> list[dict[str, Any]]:
        """List the user's YNAB plans (YNAB's newer name for budgets).

        Use a plan's `id` as `plan_id` in other tools.
        """
        data = await ynab.get("/plans")
        return [
            {
                "id": plan["id"],
                "name": plan["name"],
                "last_modified_on": plan.get("last_modified_on"),
                "currency": (plan.get("currency_format") or {}).get("iso_code"),
            }
            for plan in data["plans"]
        ]

    @mcp.tool(annotations={"readOnlyHint": True})
    async def get_month_summary(plan_id: PlanId = None, month: Month = "current") -> dict[str, Any]:
        """Summarize one month of a plan: income, assigned, activity and Ready to Assign.

        Amounts are in the plan's currency units (not milliunits).
        """
        plan = plan_id or settings.ynab_default_plan_id
        data = await ynab.get(f"/plans/{plan}/months/{month}")
        m = data["month"]
        return {
            "month": m["month"],
            "income": from_milliunits(m["income"]),
            "assigned": from_milliunits(m["budgeted"]),
            "activity": from_milliunits(m["activity"]),
            "ready_to_assign": from_milliunits(m["to_be_budgeted"]),
            "age_of_money_days": m.get("age_of_money"),
            "note": m.get("note"),
        }
