from __future__ import annotations

import math
from typing import Any

from ..command_backend_validators import _is_absolute_filesystem_path
from .base import _invalid_argument, _not_supported_by_live_api


class LiveBackendScenesArrangementMixin:
    def _focus_arranger_view(self) -> None:
        app = self._application()
        view = getattr(app, "view", None)
        if view is None:
            raise _not_supported_by_live_api(
                message="Application view API is not available in Live API",
                hint="Use a Live version exposing application.view.",
            )
        focus_view = getattr(view, "focus_view", None)
        if not callable(focus_view):
            raise _not_supported_by_live_api(
                message="Application focus_view API is not available in Live API",
                hint="Use a Live version exposing application.view.focus_view.",
            )
        focus_view("Arranger")

    def _arrangement_clips(self, track: int) -> list[Any]:
        target_track = self._track_at(track)
        arrangement_clips = getattr(target_track, "arrangement_clips", None)
        if arrangement_clips is None:
            raise _not_supported_by_live_api(
                message="Arrangement clip list API is not available in Live API",
                hint="Use a Live version exposing track.arrangement_clips.",
            )
        try:
            return list(arrangement_clips)
        except TypeError as exc:
            raise _not_supported_by_live_api(
                message="Arrangement clip container API is not iterable in Live API",
                hint="Use a Live version exposing iterable track.arrangement_clips.",
            ) from exc

    def _arrangement_clip_at(self, track: int, index: int) -> Any:
        clips = self._arrangement_clips(track)
        if index < 0 or index >= len(clips):
            raise _invalid_argument(
                message=f"arrangement clip index out of range: {index}",
                hint="Use a valid index from arrangement clip list.",
            )
        return clips[index]

    def _require_midi_arrangement_clip(self, track: int, index: int, *, hint: str) -> Any:
        clip = self._arrangement_clip_at(track, index)
        if not bool(getattr(clip, "is_midi_clip", False)):
            raise _invalid_argument(
                message=f"arrangement clip at index {index} is not a MIDI clip",
                hint=hint,
            )
        return clip

    def _arrangement_notes_payload(
        self,
        *,
        track: int,
        index: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
        notes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        payload_notes = [
            {
                "pitch": int(note["pitch"]),
                "start_time": float(note["start_time"]),
                "duration": float(note["duration"]),
                "velocity": int(note["velocity"]),
                "mute": bool(note["mute"]),
            }
            for note in notes
        ]
        return {
            "track": track,
            "index": index,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
            "notes": payload_notes,
            "note_count": len(payload_notes),
        }

    def scenes_list(self) -> dict[str, Any]:
        scenes = []
        for index, scene in enumerate(list(getattr(self._song(), "scenes", []))):
            scenes.append({"index": index, "name": str(getattr(scene, "name", ""))})
        return {"scenes": scenes}

    def create_scene(self, index: int) -> dict[str, Any]:
        song = self._song()
        scenes = list(getattr(song, "scenes", []))
        if index != -1 and index > len(scenes):
            raise _invalid_argument(
                message=f"index out of range: {index}",
                hint="Use -1 for append or a valid insertion index.",
            )

        target_index = len(scenes) if index == -1 else index
        song.create_scene(target_index)
        created = self._scene_at(target_index)
        return {"index": target_index, "name": str(getattr(created, "name", ""))}

    def set_scene_name(self, scene: int, name: str) -> dict[str, Any]:
        target = self._scene_at(scene)
        target.name = name
        return {"scene": scene, "name": str(target.name)}

    def fire_scene(self, scene: int) -> dict[str, Any]:
        target = self._scene_at(scene)
        target.fire()
        return {"scene": scene, "fired": True}

    def scenes_move(self, from_index: int, to_index: int) -> dict[str, Any]:
        self._scene_at(from_index)
        self._scene_at(to_index)
        move_scene = getattr(self._song(), "move_scene", None)
        if not callable(move_scene):
            raise _not_supported_by_live_api(
                message="Scene move API is not available in Live API",
                hint="Move scenes manually in Ableton Live.",
            )
        move_scene(from_index, to_index)
        return {"from": from_index, "to": to_index, "moved": True}

    def stop_all_clips(self) -> dict[str, Any]:
        song = self._song()
        if not hasattr(song, "stop_all_clips"):
            raise _invalid_argument(
                message="Song does not support stop_all_clips",
                hint="Use a compatible Ableton Live version.",
            )
        song.stop_all_clips()
        return {"stopped": True}

    def arrangement_record_start(self) -> dict[str, Any]:
        song = self._song()
        if hasattr(song, "record_mode"):
            song.record_mode = True
            return {"recording": bool(song.record_mode)}
        start_recording = getattr(song, "start_arrangement_recording", None)
        if callable(start_recording):
            start_recording()
            return {"recording": True}
        raise _not_supported_by_live_api(
            message="Arrangement record start API is not available in Live API",
            hint="Start arrangement recording manually in Ableton Live.",
        )

    def arrangement_record_stop(self) -> dict[str, Any]:
        song = self._song()
        if hasattr(song, "record_mode"):
            song.record_mode = False
            return {"recording": bool(song.record_mode)}
        stop_recording = getattr(song, "stop_arrangement_recording", None)
        if callable(stop_recording):
            stop_recording()
            return {"recording": False}
        raise _not_supported_by_live_api(
            message="Arrangement record stop API is not available in Live API",
            hint="Stop arrangement recording manually in Ableton Live.",
        )

    def arrangement_clip_create(
        self,
        track: int,
        start_time: float,
        length: float,
        audio_path: str | None,
        notes: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        self._focus_arranger_view()
        target_track = self._track_at(track)
        before_count = len(self._arrangement_clips(track))
        is_midi_track = bool(getattr(target_track, "has_midi_input", False))
        is_audio_track = bool(getattr(target_track, "has_audio_input", False))
        normalized_start_time = float(start_time)
        normalized_length = float(length)

        if is_midi_track and not is_audio_track:
            if audio_path is not None:
                raise _invalid_argument(
                    message="audio_path must not be provided for MIDI tracks",
                    hint="Remove --audio-path for MIDI arrangement clip creation.",
                )
            create_midi_clip = getattr(target_track, "create_midi_clip", None)
            if not callable(create_midi_clip):
                raise _not_supported_by_live_api(
                    message="Arrangement MIDI clip creation API is not available in Live API",
                    hint="Use a Live version exposing track.create_midi_clip.",
                )
            create_midi_clip(normalized_start_time, normalized_length)
            notes_added: int | None = None
            if notes is not None:
                clips = self._arrangement_clips(track)
                if len(clips) <= before_count:
                    raise _invalid_argument(
                        message="Arrangement MIDI clip creation did not produce a clip",
                        hint="Retry arrangement clip creation before adding notes.",
                    )
                created_clip = clips[before_count]
                set_notes = getattr(created_clip, "set_notes", None)
                if not callable(set_notes):
                    raise _not_supported_by_live_api(
                        message="Arrangement clip note write API is not available in Live API",
                        hint="Use a Live version exposing clip.set_notes for arrangement clips.",
                    )
                note_payload = self._clip_note_tuples(notes)
                if note_payload:
                    set_notes(note_payload)
                notes_added = len(note_payload)
            result = {
                "track": track,
                "start_time": normalized_start_time,
                "length": normalized_length,
                "kind": "midi",
                "arrangement_view_focused": True,
                "created": True,
            }
            if notes_added is not None:
                result["notes_added"] = notes_added
            return result

        if is_audio_track and not is_midi_track:
            if notes is not None:
                raise _invalid_argument(
                    message="notes are supported only for MIDI tracks",
                    hint="Remove --notes-json/--notes-file for audio arrangement clip creation.",
                )
            if audio_path is None:
                raise _invalid_argument(
                    message="audio_path is required for audio tracks",
                    hint="Pass --audio-path with an absolute audio file path.",
                )
            normalized_audio_path = str(audio_path).strip()
            if not _is_absolute_filesystem_path(normalized_audio_path):
                raise _invalid_argument(
                    message=f"audio_path must be an absolute path, got {normalized_audio_path!r}",
                    hint="Pass an absolute filesystem path for --audio-path.",
                )
            create_audio_clip = getattr(target_track, "create_audio_clip", None)
            if not callable(create_audio_clip):
                raise _not_supported_by_live_api(
                    message="Arrangement audio clip creation API is not available in Live API",
                    hint="Use a Live version exposing track.create_audio_clip.",
                )
            create_audio_clip(normalized_audio_path, normalized_start_time)
            clips = self._arrangement_clips(track)
            if len(clips) <= before_count:
                raise _invalid_argument(
                    message="Arrangement audio clip creation did not produce a clip",
                    hint="Retry arrangement clip creation.",
                )
            created_clip = clips[before_count]
            if hasattr(created_clip, "length"):
                created_clip.length = normalized_length
            return {
                "track": track,
                "start_time": normalized_start_time,
                "length": normalized_length,
                "kind": "audio",
                "audio_path": normalized_audio_path,
                "arrangement_view_focused": True,
                "created": True,
            }

        raise _invalid_argument(
            message=(
                f"track {track} must be exclusively MIDI or audio "
                f"(has_midi_input={is_midi_track}, has_audio_input={is_audio_track})"
            ),
            hint="Use a standard MIDI or audio track for arrangement clip creation.",
        )

    def arrangement_clip_list(self, track: int | None) -> dict[str, Any]:
        if track is None:
            target_tracks = [
                (index, target_track)
                for index, target_track in enumerate(list(self._song().tracks))
            ]
        else:
            target_tracks = [(track, self._track_at(track))]

        clips: list[dict[str, Any]] = []
        for track_index, _target_track in target_tracks:
            for clip_index, clip in enumerate(list(self._arrangement_clips(track_index))):
                clips.append(
                    {
                        "track": track_index,
                        "index": clip_index,
                        "name": str(getattr(clip, "name", "")),
                        "start_time": self._safe_float(getattr(clip, "start_time", None)),
                        "length": self._safe_float(getattr(clip, "length", None)),
                        "is_audio_clip": bool(getattr(clip, "is_audio_clip", False)),
                        "is_midi_clip": bool(getattr(clip, "is_midi_clip", False)),
                    }
                )

        return {
            "track": track,
            "clip_count": len(clips),
            "clips": clips,
        }

    def arrangement_clip_notes_add(
        self,
        track: int,
        index: int,
        notes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        clip = self._require_midi_arrangement_clip(
            track,
            index,
            hint="Choose a MIDI arrangement clip from 'arrangement clip list'.",
        )
        set_notes = getattr(clip, "set_notes", None)
        if not callable(set_notes):
            raise _not_supported_by_live_api(
                message="Arrangement clip note write API is not available in Live API",
                hint="Use a Live version exposing clip.set_notes for arrangement clips.",
            )
        note_payload = self._clip_note_tuples(notes)
        if note_payload:
            set_notes(note_payload)
        return {"track": track, "index": index, "note_count": len(note_payload)}

    def arrangement_clip_notes_get(
        self,
        track: int,
        index: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> dict[str, Any]:
        clip = self._require_midi_arrangement_clip(
            track,
            index,
            hint="Choose a MIDI arrangement clip from 'arrangement clip list'.",
        )
        filtered = self._filtered_clip_notes(clip, start_time, end_time, pitch)
        return self._arrangement_notes_payload(
            track=track,
            index=index,
            start_time=start_time,
            end_time=end_time,
            pitch=pitch,
            notes=filtered,
        )

    def arrangement_clip_notes_clear(
        self,
        track: int,
        index: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> dict[str, Any]:
        clip = self._require_midi_arrangement_clip(
            track,
            index,
            hint="Choose a MIDI arrangement clip from 'arrangement clip list'.",
        )
        remove_notes_by_id = getattr(clip, "remove_notes_by_id", None)
        if not callable(remove_notes_by_id):
            raise _not_supported_by_live_api(
                message="Arrangement clip note remove API is not available in Live API",
                hint="Use a Live version exposing clip.remove_notes_by_id for arrangement clips.",
            )
        filtered = self._filtered_clip_notes(clip, start_time, end_time, pitch)
        to_remove = [int(note["note_id"]) for note in filtered]
        if to_remove:
            remove_notes_by_id(to_remove)
        return {
            "track": track,
            "index": index,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
            "cleared_count": len(to_remove),
        }

    def arrangement_clip_notes_replace(
        self,
        track: int,
        index: int,
        notes: list[dict[str, Any]],
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> dict[str, Any]:
        cleared = self.arrangement_clip_notes_clear(track, index, start_time, end_time, pitch)
        added = self.arrangement_clip_notes_add(track, index, notes)
        return {
            "track": track,
            "index": index,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
            "cleared_count": int(cleared["cleared_count"]),
            "added_count": int(added["note_count"]),
        }

    def arrangement_clip_notes_import_browser(
        self,
        track: int,
        index: int,
        target_uri: str | None,
        target_path: str | None,
        mode: str,
        import_length: bool,
        import_groove: bool,
    ) -> dict[str, Any]:
        if target_uri is None and target_path is None:
            raise _invalid_argument(
                message="Exactly one of target_uri or target_path must be provided",
                hint="Provide a browser URI or path to .alc item.",
            )
        if target_uri is not None and target_path is not None:
            raise _invalid_argument(
                message="target_uri and target_path are mutually exclusive",
                hint="Provide only one browser target.",
            )
        if mode not in {"replace", "append"}:
            raise _invalid_argument(
                message=f"mode must be one of replace/append, got {mode}",
                hint="Use mode replace or append.",
            )

        if target_uri is not None:
            item = self._find_browser_item_by_uri(target_uri)
            if item is None:
                raise _invalid_argument(
                    message=f"Browser item with URI '{target_uri}' not found",
                    hint="Use browser search/items to choose a valid .alc target.",
                )
        else:
            assert target_path is not None
            item = self._resolve_browser_path(target_path)

        if not self._is_midi_clip_browser_item(item):
            raise _invalid_argument(
                message=(
                    "arrangement clip notes import-browser supports only MIDI clip (.alc) items"
                ),
                hint="Choose a .alc target from browser search/items.",
            )

        target_clip = self._require_midi_arrangement_clip(
            track,
            index,
            hint="Choose a MIDI arrangement clip from 'arrangement clip list'.",
        )
        song = self._song()
        source_track_index: int | None = None
        try:
            source_track_index, source_clip = self._load_midi_clip_to_temporary_track(
                song=song, item=item
            )
            notes_imported = self._import_clip_notes(
                source_clip=source_clip,
                target_clip=target_clip,
                notes_mode=mode,
            )
            length_imported = (
                self._import_clip_length(source_clip=source_clip, target_clip=target_clip)
                if import_length
                else False
            )
            groove_imported = (
                self._import_clip_groove(source_clip=source_clip, target_clip=target_clip)
                if import_groove
                else False
            )
        finally:
            if source_track_index is not None:
                self._delete_track(song, source_track_index)

        return {
            "track": track,
            "index": index,
            "target_uri": target_uri,
            "target_path": target_path,
            "mode": mode,
            "import_length": import_length,
            "import_groove": import_groove,
            "notes_imported": notes_imported,
            "length_imported": length_imported,
            "groove_imported": groove_imported,
        }

    def arrangement_clip_delete(
        self,
        track: int,
        index: int | None,
        start: float | None,
        end: float | None,
        delete_all: bool,
    ) -> dict[str, Any]:
        target_track = self._track_at(track)
        clips = self._arrangement_clips(track)
        has_range = start is not None or end is not None
        if has_range and (start is None or end is None):
            raise _invalid_argument(
                message="start and end must be provided together",
                hint="Provide both start and end for range delete mode.",
            )
        mode_count = int(index is not None) + int(has_range) + int(delete_all)
        if mode_count != 1:
            raise _invalid_argument(
                message="Exactly one delete mode must be selected: index, range, or all",
                hint="Use one of: index | start+end | all.",
            )

        mode: str
        deleted_indexes: list[int] = []
        if index is not None:
            self._arrangement_clip_at(track, index)
            mode = "index"
            deleted_indexes = [index]
        elif delete_all:
            mode = "all"
            deleted_indexes = list(range(len(clips)))
        else:
            assert start is not None
            assert end is not None
            if end <= start:
                raise _invalid_argument(
                    message=f"end must be greater than start (start={start}, end={end})",
                    hint="Use a valid [start, end) range.",
                )
            mode = "range"
            for clip_index, clip in enumerate(list(clips)):
                clip_start = self._safe_float(getattr(clip, "start_time", None))
                clip_length = self._safe_float(getattr(clip, "length", None))
                if clip_start is None or clip_length is None:
                    continue
                clip_end = clip_start + max(clip_length, 0.0)
                overlaps = clip_start < end and clip_end > start
                if overlaps:
                    deleted_indexes.append(clip_index)

        if deleted_indexes:
            delete_clip = getattr(target_track, "delete_clip", None)
            if callable(delete_clip):
                for clip_index in sorted(deleted_indexes, reverse=True):
                    delete_clip(clips[clip_index])
            else:
                arrangement_clips = getattr(target_track, "arrangement_clips", None)
                if not isinstance(arrangement_clips, list):
                    raise _not_supported_by_live_api(
                        message="Arrangement clip delete API is not available in Live API",
                        hint=(
                            "Use a Live version exposing track.delete_clip "
                            "or mutable track.arrangement_clips."
                        ),
                    )
                for clip_index in sorted(deleted_indexes, reverse=True):
                    del arrangement_clips[clip_index]

        return {
            "track": track,
            "mode": mode,
            "deleted_count": len(deleted_indexes),
            "deleted_indexes": deleted_indexes,
        }

    def arrangement_from_session(self, scenes: list[dict[str, Any]]) -> dict[str, Any]:
        song = self._song()
        arrangement_cursor = 0.0
        scene_payloads: list[dict[str, Any]] = []
        total_created = 0
        total_notes_added = 0
        for scene_spec in scenes:
            scene_index = int(scene_spec["scene"])
            duration_beats = float(scene_spec["duration_beats"])
            if duration_beats <= 0:
                raise _invalid_argument(
                    message=f"scene duration must be > 0, got {duration_beats}",
                    hint="Use positive duration values in --scenes.",
                )
            self._scene_at(scene_index)

            midi_created = 0
            audio_created = 0
            notes_added = 0

            for track_index, track_obj in enumerate(list(getattr(song, "tracks", []))):
                clip_slots = list(getattr(track_obj, "clip_slots", []))
                if scene_index < 0 or scene_index >= len(clip_slots):
                    continue
                slot = clip_slots[scene_index]
                if not bool(getattr(slot, "has_clip", False)):
                    continue
                source_clip = getattr(slot, "clip", None)
                if source_clip is None:
                    continue

                if bool(getattr(source_clip, "is_midi_clip", False)):
                    before_count = len(self._arrangement_clips(track_index))
                    self.arrangement_clip_create(
                        track=track_index,
                        start_time=arrangement_cursor,
                        length=duration_beats,
                        audio_path=None,
                        notes=None,
                    )
                    target_index = before_count
                    source_notes = list(self._clip_notes_extended(source_clip))
                    source_length = self._safe_float(getattr(source_clip, "length", None))
                    if source_length is None or source_length <= 0:
                        note_end = max(
                            (
                                float(note["start_time"]) + float(note["duration"])
                                for note in source_notes
                            ),
                            default=duration_beats,
                        )
                        source_length = note_end if note_end > 0 else duration_beats
                    repeated_notes: list[dict[str, Any]] = []
                    loop_count = max(int(math.ceil(duration_beats / source_length)), 1)
                    for loop_index in range(loop_count):
                        loop_offset = source_length * loop_index
                        for note in source_notes:
                            note_start = float(note["start_time"]) + loop_offset
                            if note_start >= duration_beats:
                                continue
                            note_duration = float(note["duration"])
                            if note_start + note_duration > duration_beats:
                                note_duration = duration_beats - note_start
                            if note_duration <= 0:
                                continue
                            repeated_notes.append(
                                {
                                    "pitch": int(note["pitch"]),
                                    "start_time": note_start,
                                    "duration": note_duration,
                                    "velocity": int(note["velocity"]),
                                    "mute": bool(note["mute"]),
                                }
                            )
                    if repeated_notes:
                        added = self.arrangement_clip_notes_add(
                            track_index, target_index, repeated_notes
                        )
                        notes_added += int(added["note_count"])
                    midi_created += 1
                    continue

                if bool(getattr(source_clip, "is_audio_clip", False)):
                    file_path = str(getattr(source_clip, "file_path", "")).strip()
                    if not file_path:
                        raise _invalid_argument(
                            message="source session audio clip must expose file_path",
                            hint="Use audio clips with a resolvable file path.",
                        )
                    source_length = self._safe_float(getattr(source_clip, "length", None))
                    if source_length is None or source_length <= 0:
                        raise _invalid_argument(
                            message="source session audio clip must expose positive length",
                            hint="Use audio clips with positive clip length.",
                        )
                    placed = 0.0
                    while placed < duration_beats:
                        self.arrangement_clip_create(
                            track=track_index,
                            start_time=arrangement_cursor + placed,
                            length=source_length,
                            audio_path=file_path,
                            notes=None,
                        )
                        audio_created += 1
                        placed += source_length
                    continue

            created_count = midi_created + audio_created
            scene_payloads.append(
                {
                    "scene": scene_index,
                    "duration_beats": duration_beats,
                    "start_beat": arrangement_cursor,
                    "midi_clips_created": midi_created,
                    "audio_clips_created": audio_created,
                    "notes_added": notes_added,
                    "created_count": created_count,
                }
            )
            total_created += created_count
            total_notes_added += notes_added
            arrangement_cursor += duration_beats

        return {
            "scene_count": len(scene_payloads),
            "total_created": total_created,
            "total_notes_added": total_notes_added,
            "scenes": scene_payloads,
        }

    def tracks_delete(self, track: int) -> dict[str, Any]:
        self._track_at(track)
        delete_track = getattr(self._song(), "delete_track", None)
        if not callable(delete_track):
            raise _not_supported_by_live_api(
                message="Track delete API is not available in Live API",
                hint="Delete tracks manually in Ableton Live.",
            )
        delete_track(track)
        return {"track": track, "deleted": True, "track_count": len(list(self._song().tracks))}
