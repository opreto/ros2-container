# ros2-container CI

CI builds a dev container image from this generator, `ghcr.io/<owner>/ros2-container`, and runs
the image's build and test scripts in it. The image is what [`defaults.yaml`](../../defaults.yaml)
describes: [`build-dev-image`](../actions/build-dev-image/action.yml) generates a project named
`ros2-container` with no other settings, outside the checkout, and builds its `Docker/` folder.

## Workflows

| Workflow | Runs on | What it does |
| --- | --- | --- |
| [`validate-pr.yml`](validate-pr.yml) | Every PR update | Checks that the title starts with `OPR-<number>: ` and the description isn't empty. |
| [`build.yml`](build.yml) | Every PR update; manual | Runs `colcon_build.sh` and `colcon_test.sh` (what `cb` and `ct` call) on an empty workspace inside the dev image. |
| [`publish-dev-image.yml`](publish-dev-image.yml) | Generator changes merged to `main`; manual | Rebuilds the image as `latest-stable`, then deletes the image it replaced. |
| [`cleanup-pr-image.yml`](cleanup-pr-image.yml) | PR closed; after publishing; manual | Deletes the PR's image and any untagged (replaced) images. |

"Generator changes" means edits to `ros2_container/`, `templates/`, `defaults.yaml`,
`requirements.txt`, `generate.sh` or the image build (`build-dev-image`, shared by `build.yml` and
`publish-dev-image.yml`). `publish-dev-image.yml` also runs when it changes itself. Edits to
`examples/` or other dotfiles don't build an image.

## Which image a PR uses

- **No generator changes:** the PR runs in `latest-stable`.
- **Generator changes:** `build.yml` builds the PR's own image, `pr-<number>`, and runs in that
  instead. The image is rebuilt on every push and deleted when the PR closes.

Only the newest image is kept under each tag. To get an older commit's image, check out that
commit and rebuild it locally.

## First-time setup

`latest-stable` doesn't exist until `publish-dev-image.yml` first runs on `main`. Until then, PRs
without generator changes have no image to run in, so run **Publish Dev Image** manually once.

## Adding tests

`build.yml` has a commented-out `tests` job for generator tests (`pytest`). It runs on the runner,
not in the dev image. Uncomment it when the first tests are added.
