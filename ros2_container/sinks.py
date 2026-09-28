"""Where rendered files go: written to disk, or compared against it (--check)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from .outputs import File, Policy


class Sink(Protocol):
    def apply(self, files: list[File]) -> int:
        """Consume rendered files; return a process exit code."""


class _Manifest:
    """The list of files the generator owns, kept next to the generated Docker files."""

    def __init__(self, root: Path, rel_path: str):
        self.root, self.path = root, root / rel_path

    def read(self) -> set[Path]:
        return {Path(line) for line in self.path.read_text().splitlines() if line} if self.path.exists() else set()

    def write(self, owned: set[Path]) -> None:
        self.path.write_text("".join(f"{p.as_posix()}\n" for p in sorted(owned)))


def _owned(files: list[File]) -> set[Path]:
    return {f.path for f in files if f.policy is not Policy.SEED}


class DiskSink:
    def __init__(self, root: Path, manifest: str, force: bool = False):
        self.root, self.manifest, self.force = root, _Manifest(root, manifest), force

    def apply(self, files: list[File]) -> int:
        previously_owned = self.manifest.read()
        conflicts = sorted(p for p in _owned(files) - previously_owned if (self.root / p).exists())
        if conflicts and not self.force:
            print("Refusing to overwrite files the generator did not create (use --force):")
            print("".join(f"  {p}\n" for p in conflicts), end="")
            return 1

        written = 0
        for f in files:
            target = self.root / f.path
            if f.policy is Policy.SEED and target.exists():
                continue
            if not target.exists() or target.read_text() != f.content:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(f.content)
                written += 1
            if f.executable:
                target.chmod(target.stat().st_mode | 0o111)

        stale = previously_owned - _owned(files)
        for p in stale:
            self._remove(p)
        self.manifest.write(_owned(files))
        print(f"{self.root}: {written} file(s) written, {len(files) - written} unchanged, {len(stale)} stale removed.")
        return 0

    def _remove(self, rel: Path) -> None:
        (self.root / rel).unlink(missing_ok=True)
        for parent in (self.root / rel).parents:  # prune now-empty folders, e.g. a dropped variant
            if parent == self.root or any(parent.iterdir()):
                break
            parent.rmdir()


class CheckSink:
    def __init__(self, root: Path, manifest: str):
        self.root, self.manifest = root, _Manifest(root, manifest)

    def apply(self, files: list[File]) -> int:
        drift = [f"stale: {p}" for p in sorted(self.manifest.read() - _owned(files)) if (self.root / p).exists()]
        for f in files:
            target = self.root / f.path
            if f.policy is Policy.SEED:  # user-owned (often gitignored), never checked
                continue
            if not target.exists():
                drift.append(f"missing: {f.path}")
            elif f.policy is Policy.OWNED and target.read_text() != f.content:
                drift.append(f"changed: {f.path}")
        for line in drift:
            print(f"  {line}")
        print("Generated files are out of date; re-run generate.sh." if drift else "Generated files are up to date.")
        return 1 if drift else 0
