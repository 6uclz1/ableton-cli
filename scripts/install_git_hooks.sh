#!/usr/bin/env sh
set -eu

repo_root="$(git rev-parse --show-toplevel)"
hooks_path="${repo_root}/.githooks"

if [ ! -d "${hooks_path}" ]; then
  echo "Hooks directory not found: ${hooks_path}" >&2
  exit 1
fi

git config core.hooksPath "${hooks_path}"
echo "Configured git hooks path: ${hooks_path}"
