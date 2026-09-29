"""Host variants: which compose overlays to stack on top of compose.yml for each host type.

Adding a host type = adding one entry to VARIANTS (plus its overlay template if new),
and a line in candidates() in templates/Docker/compose-up.sh.j2 so it can be auto-detected.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .config import flag


@dataclass(frozen=True)
class Variant:
    name: str  # used by compose-up.sh --variant and as the .devcontainer/<name>/ folder
    label: str  # shown in the VS Code dev container picker
    overlays: tuple[str, ...]  # Docker/compose.<overlay>.yml files, in order
    enabled: Callable[[dict], bool]  # whether the merged config turns this variant on

    @property
    def compose_files(self) -> list[str]:
        return ["compose.yml"] + [f"compose.{o}.yml" for o in self.overlays]


VARIANTS = (
    Variant("linux", "Linux, X11", ("linux",), flag("display.x11")),
    Variant("linux-nvidia", "Linux, X11 + NVIDIA", ("linux", "nvidia"), lambda d: flag("display.x11")(d) and flag("display.nvidia")(d)),
    Variant("mac-vnc", "macOS, noVNC desktop", ("vnc",), flag("display.vnc.enabled")),
    Variant("windows-wslg", "Windows, WSLg", ("wslg",), flag("display.wslg")),
)


def enabled(data: dict) -> list[Variant]:
    return [v for v in VARIANTS if v.enabled(data)]
