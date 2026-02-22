from __future__ import annotations

from .app import create_app

app = create_app()


def main() -> None:
    app()
