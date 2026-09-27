from ynab_mcp.config import Settings
from ynab_mcp.server import create_server


def main() -> None:
    settings = Settings()
    create_server(settings).run(transport="http", host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
