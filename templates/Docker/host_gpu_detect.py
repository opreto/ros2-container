#!/usr/bin/env python3
"""Detect whether the host can pass NVIDIA GPUs into Docker containers."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys


def host_has_nvidia_docker(*, probe_docker: bool = True, docker_timeout_s: float = 120.0) -> bool:
    """Return True if NVIDIA GPUs are available to Docker (nvidia-smi + optional docker probe)."""
    if shutil.which("nvidia-smi") is None:
        return False
    try:
        subprocess.run(
            ["nvidia-smi"],
            check=True,
            capture_output=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return False

    if not probe_docker:
        return True

    if shutil.which("docker") is None:
        return False

    try:
        subprocess.run(
            ["docker", "run", "--rm", "--gpus", "all", "alpine:3.19", "true"],
            check=True,
            capture_output=True,
            timeout=docker_timeout_s,
        )
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Exit 0 if NVIDIA GPUs can be passed into Docker; exit 1 otherwise.",
    )
    parser.add_argument(
        "--no-docker-probe",
        action="store_true",
        help="Only check nvidia-smi (faster; may miss broken nvidia-container-toolkit).",
    )
    parser.add_argument(
        "--docker-timeout",
        type=float,
        default=120.0,
        metavar="SECS",
        help="Timeout for 'docker run --gpus all' probe (default: 120).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress output on success.",
    )
    args = parser.parse_args()

    ok = host_has_nvidia_docker(
        probe_docker=not args.no_docker_probe,
        docker_timeout_s=args.docker_timeout,
    )
    if ok and not args.quiet:
        print("nvidia")
    elif not ok and not args.quiet:
        print("intel", file=sys.stderr)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
