# ros2-container

Generate a ROS 2 dev container for your project from one YAML file. It works on
Linux (X11, with Mesa or NVIDIA), macOS (a noVNC desktop in the browser) and
Windows (WSLg).

## Quick start

```bash
cd my-robot
git submodule add <this-repo-url> tools/ros2-container
tools/ros2-container/generate.sh init        # writes ./ros2-container.yaml (from examples/lyrical.yaml)
# edit ros2-container.yaml: project name, ROS distro, dependencies, ...
tools/ros2-container/generate.sh             # writes Docker/, .devcontainer/, .vscode/, pyrightconfig.json
Docker/compose-up.sh up -d --build           # detects the host and starts the container
Docker/compose-up.sh exec ros2-dev bash
```

Or open the folder in VS Code, choose **Reopen in Container** and pick the
variant for your machine.

Only `python3` is needed on the host. The first run of `generate.sh` sets up its
own virtualenv in `tools/ros2-container/.venv`.

## Changing the container

Edit `ros2-container.yaml`, then re-run `generate.sh` and rebuild. Every option
and its default is documented in [defaults.yaml](defaults.yaml). A few rules:

- **Merging:** maps merge over the defaults, and lists replace them. Unknown keys are an error.
- **Dependencies:** `dependencies.apt` and `dependencies.ros` are named groups. Each group becomes one cached `RUN` layer. ROS packages use short names (`robot_state_publisher` becomes `ros-<distro>-robot-state-publisher`).
- **Escape hatches:** `extra.volumes`, `extra.env`, `extra.devices`, `extra.run` (raw Dockerfile steps), `extra.dockerfile_env` and `rosdep.rules_file`.
- **One-off overrides:** `generate.sh --set ros.distro=kilted --set display.nvidia=false`. Use `-c a.yaml -c b.yaml` to merge several configs.

The generator owns the files it writes, and lists them in `Docker/.generated`.
Re-running it updates those files and deletes any it no longer produces. It
won't overwrite files it didn't create unless you pass `--force`.
`generate.sh --check` exits with status 1 when the generated files are out of
date, which is useful in CI. It writes `Docker/.env` and
`Docker/.bash_aliases_personal` once and then leaves them alone.

## Host variants

| Variant        | Compose files                        | GUI                                              |
|----------------|--------------------------------------|--------------------------------------------------|
| `linux`        | `compose.yml` + `compose.linux.yml`  | host X11 (`xhost +local:` is run for you)        |
| `linux-nvidia` | … + `compose.nvidia.yml`             | host X11, NVIDIA GPU (nvidia-container-toolkit)  |
| `mac-vnc`      | `compose.yml` + `compose.vnc.yml`    | Xfce desktop at http://localhost:6080/vnc.html   |
| `windows-wslg` | `compose.yml` + `compose.wslg.yml`   | WSLg (run from a WSL2 shell)                     |

`compose-up.sh` picks the variant at run time. Pass `--variant <name>` to force
one. Each variant also gets its own `.devcontainer/<variant>/devcontainer.json`.
Turn variants off under `display:` in the config.

## Inside the container

- `cb` runs rosdep install and `colcon build --symlink-install`. It then merges `compile_commands.json` for clangd and IntelliSense, and refreshes the Pylance `extraPaths` for your packages. Arguments after `--` go to colcon.
- `cbs` runs `cb` and then sources the workspace. `cclean` deletes `build/`, `install/` and `log/`.
- Put personal aliases in `Docker/.bash_aliases_personal`.

## Extending the generator

- **Add a generated file:** add a template under `templates/` and one row to `OUTPUTS` in [ros2_container/outputs.py](ros2_container/outputs.py).
- **Add a host type:** add one entry to `VARIANTS` in [ros2_container/variants.py](ros2_container/variants.py), plus its `compose.<overlay>.yml.j2` if it needs a new overlay.
- **Add a derived template value:** compute it in [ros2_container/context.py](ros2_container/context.py). Templates only loop and branch.
- **Add a config option:** give it a default in [defaults.yaml](defaults.yaml) and use it in a template.
