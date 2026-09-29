"""Command line: `generate.sh init` scaffolds a config; `generate.sh` renders it."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from . import config, context, outputs, sinks


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.command == "init":
            return init_config(args.distro, args.name)
        cfg = config.load(args.config)
        ctx = context.build(cfg)
        files = outputs.render(outputs.OUTPUTS, ctx)
        manifest = f"{ctx['dirs']['docker']}/.generated"
        code = sinks.DiskSink(cfg.output_root, manifest, args.force).apply(files)
    except config.ConfigError as err:
        print(f"error: {err}", file=sys.stderr)
        return 2
    if code == 0:
        print(f"Next: {ctx['dirs']['docker']}/compose-up.sh up -d --build   (variants: {', '.join(v.name for v in ctx['variants'])})")
    return code


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="generate.sh", description="Generate a ROS 2 dev container from a YAML/JSON config (the only source of settings).")
    parser.add_argument("-c", "--config", action="append", default=[], help=f"config file(s), merged in order (default: ./{config.DEFAULT_CONFIG_NAME})")
    parser.add_argument("-f", "--force", action="store_true", help="overwrite existing files the generator did not create")
    sub = parser.add_subparsers(dest="command")
    init = sub.add_parser("init", help=f"write a starter ./{config.DEFAULT_CONFIG_NAME}")
    init.add_argument("-d", "--distro", default="lyrical", help="example to start from (examples/<distro>.yaml)")
    init.add_argument("-n", "--name", help="project slug (default: current folder name)")
    return parser.parse_args(argv)


def init_config(distro: str, name: str | None) -> int:
    example = config.REPO_DIR / "examples" / f"{distro}.yaml"
    dest = Path.cwd() / config.DEFAULT_CONFIG_NAME
    if not example.exists():
        available = ", ".join(p.stem for p in (config.REPO_DIR / "examples").glob("*.yaml"))
        raise config.ConfigError(f"No example for {distro!r}; available: {available}")
    if dest.exists():
        raise config.ConfigError(f"{dest} already exists")
    name = name or re.sub(r"[^a-z0-9_-]+", "-", Path.cwd().name.lower()).strip("-")
    text = re.sub(r"(?m)^(  name: ).*$", rf"\g<1>{name}", example.read_text(), count=1)
    text = re.sub(r"(?m)^(  display_name: ).*$", rf"\g<1>{name.replace('-', ' ').title()}", text, count=1)
    dest.write_text(text)
    print(f"Wrote {dest}. Edit it, then run generate.sh.")
    return 0
