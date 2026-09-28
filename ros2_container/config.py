"""Load, merge and validate the generator configuration."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

REPO_DIR = Path(__file__).resolve().parent.parent
DEFAULTS_FILE = REPO_DIR / "defaults.yaml"
DEFAULT_CONFIG_NAME = "ros2-container.yaml"

# Maps whose keys the user chooses, so they are not checked against defaults.yaml.
FREEFORM_KEYS = {
    "dependencies.apt",
    "dependencies.ros",
    "extra.env",
    "extra.dockerfile_env",
    "bash.aliases",
    "editor.settings",
}
EDITORS = {"vscode", "cursor"}
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    data: dict
    config_dir: Path  # user paths in `data` are resolved against this
    output_root: Path
    config_name: str  # for the "generated from" header


def load(config_files: Iterable[str], overrides: Iterable[str], output_root: str | None = None) -> Config:
    """Merge defaults <- config files (left to right) <- `key.path=value` overrides."""
    files = [Path(f) for f in config_files] or [_default_config_file()]
    data = _read(DEFAULTS_FILE)
    for path in files:
        data = deep_merge(data, _read(path))
    for item in overrides:
        key, sep, value = item.partition("=")
        if not sep:
            raise ConfigError(f"--set expects key.path=value, got {item!r}")
        _set_dotted(data, key, yaml.safe_load(value))
    _validate(data, _read(DEFAULTS_FILE))

    config_dir = files[-1].resolve().parent
    root = Path(output_root).resolve() if output_root else (config_dir / data["output"]["root"]).resolve()
    if root == REPO_DIR or REPO_DIR in root.parents:
        raise ConfigError(f"Refusing to generate inside the generator itself ({root}); pass -o or move the config.")
    return Config(data, config_dir, root, files[-1].name)


def deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _default_config_file() -> Path:
    path = Path.cwd() / DEFAULT_CONFIG_NAME
    if not path.exists():
        raise ConfigError(f"No {DEFAULT_CONFIG_NAME} here. Run `generate.sh init` first, or pass -c <config>.")
    return path


def _read(path: Path) -> dict:
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    text = path.read_text()
    data = json.loads(text) if path.suffix == ".json" else yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must contain a mapping at the top level")
    return data


def _set_dotted(data: dict, dotted: str, value: Any) -> None:
    *parents, leaf = dotted.split(".")
    for key in parents:
        data = data.setdefault(key, {})
    data[leaf] = value


def _validate(data: dict, defaults: dict) -> None:
    _check_known_keys(data, defaults, prefix="")
    if not SLUG_RE.match(str(data["project"]["name"])):
        raise ConfigError(f"project.name must be a lowercase slug, got {data['project']['name']!r}")
    unknown = set(data["editor"]["editors"]) - EDITORS
    if unknown:
        raise ConfigError(f"Unknown editor(s) {sorted(unknown)}; choose from {sorted(EDITORS)}")


def _check_known_keys(data: dict, defaults: dict, prefix: str) -> None:
    for key, value in data.items():
        path = f"{prefix}{key}"
        if key not in defaults:
            raise ConfigError(f"Unknown config key: {path}")
        if isinstance(value, dict) and isinstance(defaults[key], dict) and path not in FREEFORM_KEYS:
            _check_known_keys(value, defaults[key], prefix=f"{path}.")
