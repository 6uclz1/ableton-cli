from __future__ import annotations

from typing import Annotated, Any

import typer

from ..errors import AppError, ErrorCode, ExitCode, read_only_violation
from ..plugins.environment import PluginEnvironment
from ..plugins.github import PinnedSource, pin_source, run_subprocess
from ..plugins.installer import (
    install_plugin,
    pin_managed_plugin,
    sync_plugins,
    uninstall_plugin,
    update_plugin,
)
from ..plugins.manifest import plugin_manifest_path, read_manifest
from ..plugins.model import PLUGIN_API_VERSION
from ..plugins.status import plugin_listing
from ..runtime import RuntimeContext, execute_command, get_runtime

plugins_app = typer.Typer(help="Plugin management commands", no_args_is_help=True)

NameArgument = Annotated[str, typer.Argument(help="Plugin name, as shown by 'plugins list'")]
RefOption = Annotated[
    str | None,
    typer.Option("--ref", help="Branch, tag or full commit SHA (default: the default branch)"),
]


def _listing(runtime: RuntimeContext) -> list[dict[str, Any]]:
    return plugin_listing(
        runtime.plugins, read_manifest(plugin_manifest_path()), PluginEnvironment()
    )


def _guard_writable(runtime: RuntimeContext, command: str) -> None:
    if runtime.read_only:
        raise read_only_violation(command)


def _pinned_args(
    holder: dict[str, PinnedSource], pinned: PinnedSource, **args: Any
) -> dict[str, Any]:
    """Remember the pinned commit for the action and show it in args (and in --plan)."""
    holder["pinned"] = pinned
    return {**args, "source": pinned.source.url, "rev": pinned.rev}


@plugins_app.command("list")
def plugins_list(ctx: typer.Context) -> None:
    def _run() -> dict[str, object]:
        runtime = get_runtime(ctx)
        return {
            "enabled": runtime.plugins.enabled,
            "api_version": PLUGIN_API_VERSION,
            "manifest_path": str(plugin_manifest_path()),
            "plugins": _listing(runtime),
        }

    execute_command(ctx, command="plugins list", args={}, action=_run)


@plugins_app.command("info")
def plugins_info(ctx: typer.Context, name: NameArgument) -> None:
    def _run() -> dict[str, object]:
        for entry in _listing(get_runtime(ctx)):
            if entry["name"] == name:
                return entry
        raise AppError(
            error_code=ErrorCode.INVALID_ARGUMENT,
            message=f"No plugin named '{name}' is installed or recorded in the manifest",
            hint="Run 'ableton-cli plugins list' to see plugin names.",
            exit_code=ExitCode.INVALID_ARGUMENT,
        )

    execute_command(ctx, command="plugins info", args={"name": name}, action=_run)


@plugins_app.command("install")
def plugins_install(
    ctx: typer.Context,
    url: Annotated[
        str, typer.Argument(help="GitHub repository URL, optionally ending in /tree/<ref>")
    ],
    ref: RefOption = None,
) -> None:
    holder: dict[str, PinnedSource] = {}

    def _run() -> dict[str, object]:
        _guard_writable(get_runtime(ctx), "plugins install")
        return install_plugin(
            holder["pinned"],
            manifest_path=plugin_manifest_path(),
            environment=PluginEnvironment(),
        )

    execute_command(
        ctx,
        command="plugins install",
        args={"url": url, "ref": ref},
        resolved_args=lambda: _pinned_args(
            holder, pin_source(url, ref, run=run_subprocess), url=url, ref=ref
        ),
        action=_run,
    )


@plugins_app.command("update")
def plugins_update(ctx: typer.Context, name: NameArgument, ref: RefOption = None) -> None:
    holder: dict[str, PinnedSource] = {}

    def _run() -> dict[str, object]:
        _guard_writable(get_runtime(ctx), "plugins update")
        return update_plugin(
            name,
            holder["pinned"],
            manifest_path=plugin_manifest_path(),
            environment=PluginEnvironment(),
        )

    execute_command(
        ctx,
        command="plugins update",
        args={"name": name, "ref": ref},
        resolved_args=lambda: _pinned_args(
            holder,
            pin_managed_plugin(name, ref, manifest_path=plugin_manifest_path(), run=run_subprocess),
            name=name,
            ref=ref,
        ),
        action=_run,
    )


@plugins_app.command("uninstall")
def plugins_uninstall(ctx: typer.Context, name: NameArgument) -> None:
    def _run() -> dict[str, object]:
        _guard_writable(get_runtime(ctx), "plugins uninstall")
        return uninstall_plugin(
            name, manifest_path=plugin_manifest_path(), environment=PluginEnvironment()
        )

    execute_command(ctx, command="plugins uninstall", args={"name": name}, action=_run)


@plugins_app.command("sync")
def plugins_sync(ctx: typer.Context) -> None:
    def _run() -> dict[str, object]:
        _guard_writable(get_runtime(ctx), "plugins sync")
        return sync_plugins(manifest_path=plugin_manifest_path(), environment=PluginEnvironment())

    execute_command(ctx, command="plugins sync", args={}, action=_run)


def register(app: typer.Typer) -> None:
    app.add_typer(plugins_app, name="plugins")
