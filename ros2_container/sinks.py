"""Write rendered files to disk, tracking which ones the generator owns."""

from __future__ import annotations

from pathlib import Path

from .outputs import File, Policy


class _Manifest:
    """The list of files the generator owns, kept next to the generated Docker files."""

    def __init__(self, root: Path, rel_path: str):
        self.path = root / rel_path

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
        owned = _owned(files)
        conflicts = sorted(p for p in owned - previously_owned if (self.root / p).exists())
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

        stale = previously_owned - owned
        for p in stale:
            self._remove(p)
        self.manifest.write(owned)
        print(f"{self.root}: {written} file(s) written, {len(files) - written} unchanged, {len(stale)} stale removed.")
        return 0

    def _remove(self, rel: Path) -> None:
        (self.root / rel).unlink(missing_ok=True)
        for parent in (self.root / rel).parents:  # prune now-empty folders, e.g. a dropped variant
            if parent == self.root or any(parent.iterdir()):
                break
            parent.rmdir()

