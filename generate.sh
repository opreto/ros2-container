#!/usr/bin/env bash
# Entry point: sets up a private virtualenv on first run, then runs the generator.
#   generate.sh init                 # write a starter ./ros2-container.yaml
#   generate.sh [-c config.yaml]     # generate Docker/, .devcontainer/, .vscode/
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${REPO_DIR}/.venv"

if ! cmp -s "${REPO_DIR}/requirements.txt" "${VENV}/requirements.txt"; then
  python3 -m venv "${VENV}"
  "${VENV}/bin/pip" install --quiet --disable-pip-version-check -r "${REPO_DIR}/requirements.txt"
  cp "${REPO_DIR}/requirements.txt" "${VENV}/requirements.txt"
fi

PYTHONPATH="${REPO_DIR}" exec "${VENV}/bin/python" -m ros2_container "$@"
