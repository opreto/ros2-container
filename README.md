# ros2-container

Generate a ROS 2 dev container for your project from one YAML file. It works on
Linux (X11, with Mesa or NVIDIA), macOS (a noVNC desktop in the browser) and
Windows (WSLg).

The host needs only Docker and `python3` (plus `python3-venv` on Ubuntu/Debian).
`generate.sh` sets up its own virtualenv in `tools/ros2-container/.venv` on first run.

## Quick start

```bash
cd my-new-repo
git submodule add git@github.com:opreto/ros2-container.git tools/ros2-container
tools/ros2-container/generate.sh init        # writes ./ros2-container.yaml
```

The new `ros2-container.yaml` lists every option with its value and a comment
(it is [examples/lyrical.yaml](examples/lyrical.yaml) merged over
[defaults.yaml](defaults.yaml)). Set the project name, ROS distro, dependencies
and so on, then:

```bash
tools/ros2-container/generate.sh             # writes Docker/, .devcontainer/, .vscode/
Docker/compose-up.sh up -d --build           # detects the host and starts the container
Docker/compose-up.sh exec ros2-dev bash
```

Or open the folder in VS Code, choose **Reopen in Container** and pick the
variant for your machine.

To shut the container down:

```bash
Docker/compose-up.sh stop                    # stop it; `compose-up.sh start` resumes it as it was
Docker/compose-up.sh down                    # stop and remove it (the image is kept)
```

Your workspace is bind-mounted from the host, so source and build output
survive both. `down` discards changes made inside the container itself, such as
packages `cb` installed through rosdep; the next `cb` reinstalls them. In VS
Code, closing the window stops the container.

## Changing the container

Edit `ros2-container.yaml`, re-run `generate.sh`, and rebuild. A hand-written
config only needs the settings it changes; the rest come from [defaults.yaml](defaults.yaml).

- **Merging:** maps (including the named dependency groups) merge over the defaults; lists replace them. Unknown keys are an error.
- **Dependencies:** each group in `dependencies.apt` and `dependencies.ros` becomes one cached `RUN` layer. ROS packages use short names (`robot_state_publisher` becomes `ros-<distro>-robot-state-publisher`).
- **Escape hatches:** `extra.volumes`, `extra.env`, `extra.devices`, `extra.run` (raw Dockerfile steps), `extra.dockerfile_env` and `rosdep.rules_file`.
- **Layered configs:** `generate.sh -c base.yaml -c robot.yaml` merges the files left to right, so projects can share a base config.
- **Relative paths** chain from the config file. Usually all three are `.`, meaning the config, the generated folders and the colcon workspace are all at the repo root.

  | Setting | Relative to |
  |---|---|
  | `output.root`, `rosdep.rules_file` | the directory of the config file (the last `-c` file) |
  | `workspace.host_path` (mounted at `workspace.container_path`) | `output.root` |
  | `workspace.ros_ws_subdir` (the colcon workspace with `src/`) | `workspace.host_path` |

The generator lists the files it owns in `Docker/.generated`. A re-run updates
them and deletes any it no longer produces. It won't overwrite files it didn't
create unless you pass `-f`/`--force`. `Docker/.env` and `Docker/.bash_aliases_personal`
are written once and then left alone. Run `generate.sh -h` for all options.

## Host variants

| Variant        | Compose files                        | GUI                                              |
|----------------|--------------------------------------|--------------------------------------------------|
| `linux`        | `compose.yml` + `compose.linux.yml`  | host X11 (`xhost +local:` is run for you)        |
| `linux-nvidia` | … + `compose.nvidia.yml`             | host X11, NVIDIA GPU (nvidia-container-toolkit)  |
| `mac-vnc`      | `compose.yml` + `compose.vnc.yml`    | Xfce desktop at http://localhost:6080/vnc.html   |
| `windows-wslg` | `compose.yml` + `compose.wslg.yml`   | WSLg (run from a WSL2 shell)                     |

`compose-up.sh` detects the variant each time it runs; `--variant <name>` forces one.
Each variant has its own `.devcontainer/<variant>/devcontainer.json`. Turn
variants off under `display:` in the config.

## Inside the container

- `cb` builds the workspace: `rosdep install`, then `colcon build --symlink-install`. Afterwards it merges `compile_commands.json` for clangd/IntelliSense and writes `pyrightconfig.json` so Pylance/Pyright can import your packages.
  - `cb -j N` limits compile jobs *per package*. colcon still builds several packages at once, so if the build runs out of memory, also pass `-- --parallel-workers 1`.
  - `cb --rosdep-update` refreshes the rosdep index first. It's only needed for rosdep keys released after the image was built.
  - Other arguments, and anything after `--`, go to colcon (e.g. `cb -- --packages-select my_pkg`).
- `cbs` runs `cb`, then sources the workspace. `cclean` deletes `build/`, `install/` and `log/`.
- `ct` runs `colcon test` and prints `colcon test-result --verbose`, exiting non-zero if a test fails. Arguments after `--` go to colcon (e.g. `ct -- --packages-select my_pkg`). `test.skip_paths` in the config skips packages you don't maintain.
- Put personal aliases in `Docker/.bash_aliases_personal`.

`pyrightconfig.json` is written at the workspace root inside the container, by
`cb` and when the dev container is created. It is not generated on the host.
Commit it or gitignore it, whichever suits your project. If an older version of
the generator created it, the next `generate.sh` deletes it and the next `cb`
recreates it.

## Extending the generator

- **Add a generated file:** add a template under `templates/` and a row to `OUTPUTS` in [ros2_container/outputs.py](ros2_container/outputs.py).
- **Add a host type:** add an entry to `VARIANTS` in [ros2_container/variants.py](ros2_container/variants.py), a `compose.<overlay>.yml.j2` if it needs a new overlay, and a line in `candidates()` in [compose-up.sh.j2](templates/Docker/compose-up.sh.j2) so it is auto-detected.
- **Add a derived template value:** compute it in [ros2_container/context.py](ros2_container/context.py). Templates only loop and branch.
- **Add a config option:** give it a default and a comment in [defaults.yaml](defaults.yaml), then use it in a template. `init` copies both into new configs.
- **Add an example:** add `examples/<name>.yaml` with only the settings that differ from the defaults; use it with `generate.sh init -d <name>`.
