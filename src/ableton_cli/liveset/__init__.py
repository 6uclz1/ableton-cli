"""Offline reading of Ableton Live Set (``.als``) files.

A Live Set is gzip-compressed XML. This package never talks to Live or the
Remote Script, and it must not import ``ableton_cli.commands`` or the client.
"""
