#!/usr/bin/env bash
set -euo pipefail

uv run ableton-cli --output json ping
uv run ableton-cli --output json song info
uv run ableton-cli --output json transport tempo set 120
uv run ableton-cli --output json tracks list
uv run ableton-cli --output json track volume set 0 0.7
