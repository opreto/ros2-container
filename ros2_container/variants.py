"""Host variants: which compose overlays to stack on top of compose.yml for each host type.

Adding a host type = adding one entry to VARIANTS (plus its overlay template if new).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import reduce


@dataclass(frozen=True)
class Variant:
    name: str  # used by compose-up.sh --variant and as the .devcontainer/<name>/ folder
    label: str  # shown in the VS Code dev container picker
    overlays: tuple[str, ...]  # Docker/compose.<overlay>.yml files, in order
    requires: tuple[str, ...]  # dotted config flags that must all be true

    @property
    def compose_files(self) -> list[str]:
        return ["compose.yml"] + [f"compose.{o}.yml" for o in self.overlays]

    def is_enabled(self, data: dict) -> bool:
        return all(reduce(lambda d, key: d[key], flag.split("."), data) for flag in self.requires)


VARIANTS = (
    Variant("linux", "Linux, X11", ("linux",), ("display.x11",)),
    Variant("linux-nvidia", "Linux, X11 + NVIDIA", ("linux", "nvidia"), ("display.x11", "display.nvidia")),
    Variant("mac-vnc", "macOS, noVNC desktop", ("vnc",), ("display.vnc.enabled",)),
    Variant("windows-wslg", "Windows, WSLg", ("wslg",), ("display.wslg",)),
)


def enabled(data: dict) -> list[Variant]:
    return [v for v in VARIANTS if v.is_enabled(data)]
