from fastmcp import FastMCP

from ynab_mcp.config import Settings
from ynab_mcp.tools import plans
from ynab_mcp.ynab_client import YnabClient


def register_all(mcp: FastMCP, ynab: YnabClient, settings: Settings) -> None:
    """Register every tool module. Add new modules here."""
    plans.register(mcp, ynab, settings)
