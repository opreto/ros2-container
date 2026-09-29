"""Load, merge and validate the generator configuration."""

from __future__ import annotations

import copy
import io
import json
import re
from dataclasses import dataclass
from functools import reduce
from itertools import takewhile
from pathlib import Path
from typing import Callable, Iterable

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedBase, CommentedMap

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


def load(config_files: Iterable[str]) -> Config:
    """Merge defaults <- config files (left to right). The config is the only source of settings."""
    files = [Path(f) for f in config_files] or [_default_config_file()]
    defaults = _read(DEFAULTS_FILE)
    data = defaults
    for path in files:
        data = deep_merge(data, _read(path))
    _validate(data, defaults)

    config_dir = files[-1].resolve().parent
    root = (config_dir / data["output"]["root"]).resolve()
    if root == REPO_DIR or REPO_DIR in root.parents:
        raise ConfigError(f"Refusing to generate inside the generator itself ({root}); set output.root or move the config.")
    return Config(data, config_dir, root, files[-1].name)


def deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def scaffold(example: Path, name: str, display_name: str) -> str:
    """A complete starter config: defaults.yaml with `example` merged over it, keeping both files' comments.

    Every option appears with its value, documented by the comments in defaults.yaml,
    so users never need to look anything up there.
    """
    defaults = _read(DEFAULTS_FILE)
    data = copy.deepcopy(defaults)
    _merge_commented(data, _read(example))
    data["project"]["name"], data["project"]["display_name"] = name, display_name
    _validate(data, defaults)
    data.ca.comment = None  # defaults.yaml's header; replaced below
    out = io.StringIO()
    _yaml().dump(data, out)
    return _scaffold_header(example) + out.getvalue()


def flag(path: str) -> Callable[[dict], bool]:
    """Predicate that is true when the dotted `path` (e.g. "editor.enabled") is truthy in a dict."""
    return lambda data: bool(reduce(lambda d, key: d[key], path.split("."), data))


def _default_config_file() -> Path:
    path = Path.cwd() / DEFAULT_CONFIG_NAME
    if not path.exists():
        raise ConfigError(f"No {DEFAULT_CONFIG_NAME} here. Run `generate.sh init` first, or pass -c <config>.")
    return path


def _read(path: Path) -> dict:
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    text = path.read_text()
    data = json.loads(text) if path.suffix == ".json" else _yaml().load(text)
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must contain a mapping at the top level")
    return data


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


def _yaml() -> YAML:
    """Round-trip YAML: keeps comments, key order and quoting, so scaffold() can write them back out."""
    rt = YAML()
    rt.preserve_quotes = True
    rt.width = 4096  # don't wrap long lines
    rt.indent(mapping=2, sequence=4, offset=2)
    rt.representer.add_representer(type(None), lambda r, _: r.represent_scalar("tag:yaml.org,2002:null", "null"))
    return rt


def _merge_commented(base: CommentedMap, override: CommentedMap) -> None:
    """deep_merge in place. Comments on existing keys stay those of `base` (defaults.yaml documents
    every option); keys new to `base`, such as extra dependency groups, bring their own.

    New keys are appended to the end of a map. ruamel attaches a comment that follows a map to the
    end-of-line comment of its last entry, if it has one, so the last entry of a free-form map in
    defaults.yaml must not have an end-of-line comment, or the next key's comment would land above
    the appended entries.
    """
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge_commented(base[key], value)
        else:
            if key not in base and key in override.ca.items:
                base.ca.items[key] = override.ca.items[key]
            base[key] = value
            if isinstance(value, CommentedBase):
                _drop_blank_comments(value)


def _drop_blank_comments(node: CommentedBase) -> None:
    """Remove comment slots that only hold blank lines, e.g. the gap after a list in the example file."""
    for slots in node.ca.items.values():
        for i, token in enumerate(slots):
            if token is not None and not isinstance(token, list) and not token.value.strip():
                slots[i] = None


def _scaffold_header(example: Path) -> str:
    """Intro for a scaffolded config, followed by defaults.yaml's header minus its first paragraph."""
    header = list(takewhile(lambda line: line.startswith("#") or not line.strip(), DEFAULTS_FILE.read_text().splitlines(keepends=True)))
    rules = header[header.index("#\n") :] if "#\n" in header else []
    intro = (
        f"# ros2-container config, created by `generate.sh init` from examples/{example.name} merged over\n"
        "# the generator's defaults.yaml: every option is listed here with its value.\n"
        "# Edit anything, then regenerate:   tools/ros2-container/generate.sh\n"
    )
    return intro + "".join(rules)
