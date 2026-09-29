#!/usr/bin/env bash
# Entry point: sets up a private virtualenv on first run, then runs the
# generator (python -m ros2_container), which parses all arguments.
# Run `generate.sh -h` or `generate.sh init -h` for usage.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${REPO_DIR}/.venv"

# Set up the virtualenv (first run, or when requirements.txt changes)
if ! cmp -s "${REPO_DIR}/requirements.txt" "${VENV}/requirements.txt"; then
  python3 -m venv "${VENV}"
  "${VENV}/bin/pip" install --quiet --disable-pip-version-check -r "${REPO_DIR}/requirements.txt"
  cp "${REPO_DIR}/requirements.txt" "${VENV}/requirements.txt"
fi

PYTHONPATH="${REPO_DIR}" exec "${VENV}/bin/python" -m ros2_container "$@"
