#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MAN_SOURCE="${ROOT_DIR}/docs/man/generated/ableton-cli.1"
TARGET_DIR="${1:-/usr/local/share/man/man1}"

if [[ ! -f "${MAN_SOURCE}" ]]; then
  echo "Missing man source: ${MAN_SOURCE}. Run scripts/generate_man.sh first." >&2
  exit 1
fi

install -d "${TARGET_DIR}"
install -m 0644 "${MAN_SOURCE}" "${TARGET_DIR}/ableton-cli.1"
echo "Installed man page to ${TARGET_DIR}/ableton-cli.1"
