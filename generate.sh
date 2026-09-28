#!/usr/bin/env bash
# Entry point: parses the flags below, sets up a private virtualenv on first
# run, then runs the generator (python -m ros2_container).
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${REPO_DIR}/.venv"

helpFunction() {
  echo "Generate a ROS 2 dev container (Docker/, .devcontainer/, .vscode/) from a YAML/JSON config."
  echo "All settings, including the output location (output.root), come from the config file."
  echo ""
  echo "Usage: $0 [args]           Generate from the config (default: ./ros2-container.yaml)."
  echo "       $0 init [args]      Write a starter ./ros2-container.yaml to edit."
  echo ""
  echo "Generate args:"
  echo -e "\t-c, --config <FILE>     Config file (YAML or JSON). Repeat to merge several, left to right. Defaults to ./ros2-container.yaml."
  echo -e "\t-f, --force             Overwrite existing files the generator did not create."
  echo -e "\t-k, --check             Write nothing; exit 1 if the generated files are out of date (for CI)."
  echo ""
  echo "Init args:"
  echo -e "\t-d, --distro <DISTRO>   Example config to start from (examples/<DISTRO>.yaml). Defaults to lyrical."
  echo -e "\t-n, --name <NAME>       Project slug. Defaults to the current folder name."
  echo ""
  echo -e "\t-h, --help              Show help"
}

# ----- Pre-process long options so we can use getopts ----- #
command=""
if [[ "${1:-}" == init ]]; then
  command=init
  shift
fi

args=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --config|--distro|--name)
      [[ $# -ge 2 ]] || { echo "Option $1 requires an argument."; helpFunction; exit 1; }
      args+=("-$(cut -c3 <<< "$1")" "$2")
      shift 2
      ;;
    --config=*|--distro=*|--name=*)
      opt="${1%%=*}"
      args+=("-$(cut -c3 <<< "$opt")" "${1#*=}")
      shift
      ;;
    --force)
      args+=('-f')
      shift
      ;;
    --check)
      args+=('-k')
      shift
      ;;
    --help)
      args+=('-h')
      shift
      ;;
    *)
      args+=("$1")
      shift
      ;;
  esac
done

# Restore positional parameters (bash 3.2-safe expansion of a possibly empty array)
set -- ${args[@]+"${args[@]}"}

# ---- getopts parsing ----
pyArgs=()
while getopts ":c:fkd:n:h" opt; do
  case "$opt" in
    c|f|k)
      if [[ "$command" == init ]]; then
        echo "Option -$opt is not valid with init."
        helpFunction
        exit 1
      fi
      case "$opt" in
        c) pyArgs+=("--config" "$OPTARG") ;;
        f) pyArgs+=("--force") ;;
        k) pyArgs+=("--check") ;;
      esac
      ;;
    d|n)
      if [[ "$command" != init ]]; then
        echo "Option -$opt is only valid with init."
        helpFunction
        exit 1
      fi
      case "$opt" in
        d) pyArgs+=("--distro" "$OPTARG") ;;
        n) pyArgs+=("--name" "$OPTARG") ;;
      esac
      ;;
    h)
      helpFunction
      exit 0
      ;;
    \?)
      echo "Invalid option: -$OPTARG"
      helpFunction
      exit 1
      ;;
    :)
      echo "Option -$OPTARG requires an argument."
      helpFunction
      exit 1
      ;;
  esac
done
shift $((OPTIND - 1))

if [[ $# -gt 0 ]]; then
  echo "Unexpected argument: $1"
  helpFunction
  exit 1
fi

# Set up the virtualenv (first run, or when requirements.txt changes)
# ------------------------------------------------------------------
if ! cmp -s "${REPO_DIR}/requirements.txt" "${VENV}/requirements.txt"; then
  python3 -m venv "${VENV}"
  "${VENV}/bin/pip" install --quiet --disable-pip-version-check -r "${REPO_DIR}/requirements.txt"
  cp "${REPO_DIR}/requirements.txt" "${VENV}/requirements.txt"
fi

# Run the generator
# -----------------
# The python CLI takes subcommand-specific flags after the subcommand.
PYTHONPATH="${REPO_DIR}" exec "${VENV}/bin/python" -m ros2_container ${command:+"$command"} ${pyArgs[@]+"${pyArgs[@]}"}
