from __future__ import annotations

#: The command-set hash the CLI expects an installed Remote Script to report.
#:
#: This value is NOT an internal detail. ``doctor`` and ``ping`` compare it
#: against ``command_backend_registry._command_set_hash()`` from the copy of the
#: Remote Script that is already installed in the user's Ableton Live. Changing
#: it is a BREAKING CHANGE: every user must reinstall the Remote Script and
#: restart Live before any command works again.
#:
#: So this constant is deliberately hard-coded rather than recomputed. Pure
#: refactors must leave it untouched. Only edit it together with an intentional,
#: documented change to the set of remote commands.
EXPECTED_COMMAND_SET_HASH = "0a8c1422198cdaac2ecbaed0ef3c0f7c4fda61d592e3e7fd60011b0802d22532"

#: Size of the remote command set the hash is computed over. Pinned separately
#: so an accidental add+drop that happens to collide is still caught, and so a
#: failure message tells you which direction the set moved.
EXPECTED_REMOTE_COMMAND_COUNT = 161


def test_command_set_hash_is_unchanged() -> None:
    from ableton_cli.capabilities import compute_command_set_hash
    from ableton_cli.command_specs import remote_command_names

    names = remote_command_names()
    assert len(names) == EXPECTED_REMOTE_COMMAND_COUNT
    assert compute_command_set_hash(names) == EXPECTED_COMMAND_SET_HASH


def test_remote_script_registry_reports_the_same_hash() -> None:
    from remote_script.AbletonCliRemote.command_backend_registry import (
        _command_set_hash,
        _supported_command_names,
    )

    assert _command_set_hash(_supported_command_names()) == EXPECTED_COMMAND_SET_HASH
