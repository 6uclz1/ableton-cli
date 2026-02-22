from __future__ import annotations

from .app_factory import create_app

app = create_app()


def main() -> None:
    app()
