#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${ROOT_DIR}/docs/man/generated"
OUTPUT_FILE="${OUTPUT_DIR}/ableton-cli.1"
INCLUDE_FILE="${ROOT_DIR}/docs/man/ableton-cli.1.in"

if ! command -v help2man >/dev/null 2>&1; then
  echo "help2man is required to generate man pages" >&2
  exit 1
fi

mkdir -p "${OUTPUT_DIR}"
WRAPPER_SCRIPT="$(mktemp)"
trap 'rm -f "${WRAPPER_SCRIPT}"' EXIT

cat >"${WRAPPER_SCRIPT}" <<'WRAP'
#!/usr/bin/env bash
set -euo pipefail
uv run ableton-cli "$@"
WRAP
chmod +x "${WRAPPER_SCRIPT}"

help2man \
  --no-info \
  --name "Control and inspect Ableton Live via local Remote Script" \
  --include "${INCLUDE_FILE}" \
  --output "${OUTPUT_FILE}" \
  "${WRAPPER_SCRIPT}"

echo "Generated ${OUTPUT_FILE}"
