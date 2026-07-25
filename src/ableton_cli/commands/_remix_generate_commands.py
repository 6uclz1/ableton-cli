from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer

from ..harmony import VOICINGS
from ..pattern_library import bass_patterns, drum_styles
from ..remix.generators import apply_steps, generate_bass, generate_chords, generate_drums
from ..runtime import execute_command
from ..runtime import get_client as _runtime_get_client
from ._validation import invalid_argument

ProjectOption = Annotated[Path, typer.Option("--project", help="Manifest path")]
SectionOption = Annotated[
    str | None,
    typer.Option("--section", help="Planned section name; its length sets the bar count"),
]
BarsOption = Annotated[
    int | None,
    typer.Option("--bars", help="Bar count when no --section is given (default 4)"),
]
HumanizeOption = Annotated[
    float,
    typer.Option("--humanize", help="Timing/velocity jitter in [0.0, 1.0]; needs --seed"),
]
SeedOption = Annotated[
    int | None,
    typer.Option("--seed", help="Seed for reproducible humanization"),
]
KeyOption = Annotated[
    str | None,
    typer.Option("--key", help="Key like 'F minor'; defaults to the manifest target key"),
]
ApplyOption = Annotated[
    bool,
    typer.Option("--apply", help="Write the pattern into --track/--clip"),
]
TrackOption = Annotated[int | None, typer.Option("--track", help="Target track index (0-based)")]
ClipOption = Annotated[int | None, typer.Option("--clip", help="Target clip slot index (0-based)")]


def get_client(ctx: typer.Context):  # noqa: ANN201
    return _runtime_get_client(ctx)


def _finish(
    ctx: typer.Context,
    generated: dict[str, Any],
    *,
    apply: bool,
    track: int | None,
    clip: int | None,
) -> dict[str, Any]:
    """Attach batch steps, and run them when ``--apply`` is set."""
    if not apply:
        return {**generated, "applied": False}
    if track is None or clip is None:
        raise invalid_argument(
            message="--apply needs both --track and --clip",
            hint="Pass --track <index> --clip <slot>, or drop --apply to only return notes.",
        )
    steps = apply_steps(
        track=track,
        clip=clip,
        length_beats=float(generated["length_beats"]),
        notes=list(generated["pattern"]["notes"]),
        label=str(generated["kind"]),
    )
    batch = get_client(ctx).execute_batch(steps)
    return {**generated, "applied": True, "track": track, "clip": clip, "batch": batch}


def register_commands(generate_app: typer.Typer) -> None:
    @generate_app.command("drums")
    def remix_generate_drums(
        ctx: typer.Context,
        project: ProjectOption,
        style: Annotated[
            str,
            typer.Option("--style", help=f"Drum style: one of {', '.join(drum_styles())}"),
        ] = "dnb",
        section: SectionOption = None,
        bars: BarsOption = None,
        humanize: HumanizeOption = 0.0,
        seed: SeedOption = None,
        apply: ApplyOption = False,
        track: TrackOption = None,
        clip: ClipOption = None,
    ) -> None:
        execute_command(
            ctx,
            command="remix generate drums",
            args={
                "project": str(project),
                "style": style,
                "section": section,
                "bars": bars,
                "humanize": humanize,
                "seed": seed,
                "apply": apply,
                "track": track,
                "clip": clip,
            },
            action=lambda: _finish(
                ctx,
                generate_drums(
                    project,
                    style=style,
                    section=section,
                    bars=bars,
                    humanize=humanize,
                    seed=seed,
                ),
                apply=apply,
                track=track,
                clip=clip,
            ),
        )

    @generate_app.command("bass")
    def remix_generate_bass(
        ctx: typer.Context,
        project: ProjectOption,
        pattern: Annotated[
            str,
            typer.Option("--pattern", help=f"Bass pattern: one of {', '.join(bass_patterns())}"),
        ] = "offbeat",
        key: KeyOption = None,
        section: SectionOption = None,
        bars: BarsOption = None,
        follow_chords: Annotated[
            bool,
            typer.Option(
                "--follow-chords/--no-follow-chords",
                help="Follow roots from the last generated chord progression when present",
            ),
        ] = True,
        humanize: HumanizeOption = 0.0,
        seed: SeedOption = None,
        apply: ApplyOption = False,
        track: TrackOption = None,
        clip: ClipOption = None,
    ) -> None:
        execute_command(
            ctx,
            command="remix generate bass",
            args={
                "project": str(project),
                "pattern": pattern,
                "key": key,
                "section": section,
                "bars": bars,
                "follow_chords": follow_chords,
                "humanize": humanize,
                "seed": seed,
                "apply": apply,
                "track": track,
                "clip": clip,
            },
            action=lambda: _finish(
                ctx,
                generate_bass(
                    project,
                    pattern=pattern,
                    key=key,
                    section=section,
                    bars=bars,
                    follow_chords=follow_chords,
                    humanize=humanize,
                    seed=seed,
                ),
                apply=apply,
                track=track,
                clip=clip,
            ),
        )

    @generate_app.command("chords")
    def remix_generate_chords(
        ctx: typer.Context,
        project: ProjectOption,
        progression: Annotated[
            str,
            typer.Option("--progression", help="Roman numerals ('i-VI-III-VII') or chord symbols"),
        ],
        key: KeyOption = None,
        section: SectionOption = None,
        bars_per_chord: Annotated[
            float, typer.Option("--bars-per-chord", help="Bars each chord is held for")
        ] = 1.0,
        voicing: Annotated[
            str, typer.Option("--voicing", help=f"Voicing: one of {', '.join(VOICINGS)}")
        ] = "close",
        base_pitch: Annotated[
            int, typer.Option("--base-pitch", help="Lowest MIDI pitch the voicing builds from")
        ] = 60,
        voice_leading: Annotated[
            bool,
            typer.Option(
                "--voice-leading/--no-voice-leading",
                help="Pick the inversion closest to the previous chord",
            ),
        ] = True,
        apply: ApplyOption = False,
        track: TrackOption = None,
        clip: ClipOption = None,
    ) -> None:
        execute_command(
            ctx,
            command="remix generate chords",
            args={
                "project": str(project),
                "progression": progression,
                "key": key,
                "section": section,
                "bars_per_chord": bars_per_chord,
                "voicing": voicing,
                "base_pitch": base_pitch,
                "voice_leading": voice_leading,
                "apply": apply,
                "track": track,
                "clip": clip,
            },
            action=lambda: _finish(
                ctx,
                generate_chords(
                    project,
                    progression=progression,
                    key=key,
                    section=section,
                    bars_per_chord=bars_per_chord,
                    voicing=voicing,
                    base_pitch=base_pitch,
                    voice_leading=voice_leading,
                ),
                apply=apply,
                track=track,
                clip=clip,
            ),
        )
