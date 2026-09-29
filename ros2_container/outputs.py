"""The template -> generated file table, and a pure renderer for it.

Adding a generated file = adding one row to OUTPUTS.
"""

from __future__ import annotations

import json
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import jinja2

from .config import REPO_DIR, flag

TEMPLATES_DIR = REPO_DIR / "templates"


@dataclass(frozen=True)
class Output:
    template: str  # path under templates/
    dest: str  # relative to output root; formatted with `docker` (ctx["docker_dir"]) and `item`
    when: Callable[[dict], bool] = lambda ctx: True
    each: Optional[str] = None  # render once per element of ctx[each], exposed to the template as `item`
    executable: bool = False
    seed: bool = False  # written only if missing, then left to the user; otherwise owned and regenerated


@dataclass(frozen=True)
class File:
    path: Path  # relative to output root
    content: str
    executable: bool
    seed: bool


def overlay(name: str) -> Callable[[dict], bool]:
    return lambda ctx: name in ctx["overlays"]


OUTPUTS = (
    Output("Docker/Dockerfile.j2", "{docker}/Dockerfile"),
    Output("Docker/compose.yml.j2", "{docker}/compose.yml"),
    Output("Docker/compose.linux.yml.j2", "{docker}/compose.linux.yml", when=overlay("linux")),
    Output("Docker/compose.nvidia.yml.j2", "{docker}/compose.nvidia.yml", when=overlay("nvidia")),
    Output("Docker/compose.vnc.yml.j2", "{docker}/compose.vnc.yml", when=overlay("vnc")),
    Output("Docker/compose.wslg.yml.j2", "{docker}/compose.wslg.yml", when=overlay("wslg")),
    Output("Docker/compose-up.sh.j2", "{docker}/compose-up.sh", executable=True),
    Output("Docker/entrypoint.sh.j2", "{docker}/entrypoint.sh", executable=True),
    Output("Docker/bash_aliases.j2", "{docker}/.bash_aliases"),
    Output("Docker/cyclonedds.xml.j2", "{docker}/cyclonedds.xml", when=flag("use_cyclonedds")),
    Output("Docker/python-requirements.txt.j2", "{docker}/python-requirements.txt", when=flag("dependencies.pip")),
    Output("Docker/rosdep-rules.yaml.j2", "{docker}/rosdep-rules.yaml", when=flag("rosdep_rules")),
    Output("Docker/dockerignore.j2", "{docker}/.dockerignore"),
    Output("Docker/gitignore.j2", "{docker}/.gitignore"),
    Output("Docker/env.example.j2", "{docker}/.env.example"),
    Output("Docker/env.example.j2", "{docker}/.env", seed=True),
    Output("Docker/bash_aliases_personal.j2", "{docker}/.bash_aliases_personal", seed=True),
    Output("Docker/scripts/colcon_build.sh.j2", "{docker}/scripts/colcon_build.sh", executable=True),
    Output("Docker/scripts/colcon_test.sh.j2", "{docker}/scripts/colcon_test.sh", executable=True),
    Output("Docker/scripts/merge_compile_commands.sh.j2", "{docker}/scripts/merge_compile_commands.sh", executable=True),
    Output("Docker/scripts/generate_ide_config.py.j2", "{docker}/scripts/generate_ide_config.py", when=flag("ide.pyright_config"), executable=True),
    Output("devcontainer/devcontainer.json.j2", ".devcontainer/{item[folder]}/devcontainer.json", each="devcontainers"),
    Output("vscode/settings.json.j2", ".vscode/settings.json", when=flag("editor.enabled")),
)


def render(outputs: tuple[Output, ...], ctx: dict) -> list[File]:
    env = _environment()
    files = []
    for out in outputs:
        if not out.when(ctx):
            continue
        for item in ctx[out.each] if out.each else [None]:
            dest = out.dest.format(docker=ctx["docker_dir"], item=item)
            content = env.get_template(out.template).render(ctx, item=item)
            files.append(File(Path(dest), content, out.executable, out.seed))
    return files


def _environment() -> jinja2.Environment:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(TEMPLATES_DIR),
        undefined=jinja2.StrictUndefined,  # a missing value is an error, not a blank
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        comment_start_string="{##",  # so bash's ${#array[@]} is not a Jinja comment
        comment_end_string="##}",
    )
    env.filters["json"] = lambda value: json.dumps(value, indent=2)
    env.filters["quote"] = lambda value: json.dumps(str(value))  # a JSON string is a valid YAML scalar
    env.filters["shquote"] = lambda value: shlex.quote(str(value))
    return env
