"""Write rendered files to disk, tracking which ones the generator owns."""

from __future__ import annotations

from pathlib import Path

from .config import ConfigError
from .outputs import File

MANIFEST = ".ros2-container.generated"  # under the output root, so it survives output.docker_dir changes


def write_files(root: Path, files: list[File], force: bool = False) -> int:
    """Write `files` under `root`, delete owned files no longer produced, and return an exit code."""
    previously_owned = _read_manifest(root)
    owned = {f.path for f in files if not f.seed}
    conflicts = sorted(p for p in owned - previously_owned if (root / p).exists())
    if conflicts and not force:
        print("Refusing to overwrite files the generator did not create (use --force):")
        print("".join(f"  {p}\n" for p in conflicts), end="")
        return 1

    written = 0
    for f in files:
        target = root / f.path
        if f.seed and target.exists():
            continue
        if not target.exists() or target.read_text() != f.content:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f.content)
            written += 1
        if f.executable:
            target.chmod(target.stat().st_mode | 0o111)

    stale = previously_owned - owned
    for p in stale:
        _remove(root, p)
    (root / MANIFEST).write_text("".join(f"{p.as_posix()}\n" for p in sorted(owned)))
    print(f"{root}: {written} file(s) written, {len(files) - written} unchanged, {len(stale)} stale removed.")
    return 0


def _read_manifest(root: Path) -> set[Path]:
    """Owned paths, relative to the root. The file is committed, so it is untrusted: stale entries
    get deleted, and an absolute or `..` path would otherwise point outside the output root."""
    path = root / MANIFEST
    if not path.exists():
        return set()
    entries = {Path(line) for line in path.read_text().splitlines() if line}
    resolved_root = root.resolve()
    for entry in entries:
        if entry.is_absolute() or not (resolved_root / entry).resolve().is_relative_to(resolved_root):
            raise ConfigError(f"{path} lists {entry}, which is outside {resolved_root}; fix or delete that line.")
    return entries


def _remove(root: Path, rel: Path) -> None:
    (root / rel).unlink(missing_ok=True)
    for parent in (root / rel).parents:  # prune now-empty folders, e.g. a dropped variant
        if parent == root or any(parent.iterdir()):
            break
        parent.rmdir()
