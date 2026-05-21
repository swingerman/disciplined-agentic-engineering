# CLI probe — project signals → likely CLIs

When `onboard` (Step 2) runs the CLI probe, it walks the repo for these
signals and `which`-checks each suggested CLI. CLIs found on PATH go into
`manifest.validation.clis.available`; CLIs the project's signals call for but
that aren't installed go into `manifest.validation.clis.suggested`, with the
install command surfaced to the human.

**Inform-only — never blocks.** The user installs (or doesn't). The agent
can offer to run an install command if the user asks; the skill doesn't push.

## Project signal → CLI map

### Source / PR tooling

| Signal | CLI | Install |
|---|---|---|
| `.github/workflows/*.yml`, `.github/` present | `gh` (GitHub CLI) | `brew install gh` |
| `.gitlab-ci.yml`, `.gitlab/` | `glab` | `brew install glab` |

### Cloud

| Signal | CLI | Install |
|---|---|---|
| `aws-*.yaml`, `serverless.yml` with `provider: aws`, `samconfig.*`, `cdk.json` referencing `aws-cdk-lib` | `aws` (AWS CLI v2) | `brew install awscli` |
| `cloudbuild.yaml`, `app.yaml`, `.gcloudignore`, `*.gcp.yaml` | `gcloud` | `brew install --cask google-cloud-sdk` |
| `azure-pipelines.yml`, `.azure/`, `*.bicep`, `azure.yaml` (azd) | `az` (Azure CLI) | `brew install azure-cli` |
| `fly.toml` | `flyctl` | `brew install flyctl` |
| `vercel.json`, `.vercel/` | `vercel` | `npm install -g vercel` |
| `netlify.toml`, `.netlify/` | `netlify` (Netlify CLI) | `npm install -g netlify-cli` |

### Container / Kubernetes

| Signal | CLI | Install |
|---|---|---|
| `Dockerfile`, `docker-compose.yml`, `compose.yaml` | `docker` | install Docker Desktop (or `colima` on macOS) |
| `k8s/`, `kustomization.yaml`, `*-deployment.yaml`, `*-service.yaml` | `kubectl` | `brew install kubectl` |
| `Chart.yaml`, `helm/`, `charts/` | `helm` | `brew install helm` |
| `kind-*.yaml` (kind config), test runners using kind | `kind` | `brew install kind` |
| `k3d-*.yaml` | `k3d` | `brew install k3d` |

### IaC

| Signal | CLI | Install |
|---|---|---|
| `terraform/`, `*.tf`, `terragrunt.hcl` | `terraform` | `brew install terraform` |
| `cdk.json`, `cdk.context.json` | `cdk` (AWS CDK) | `npm install -g aws-cdk` |
| `Pulumi.yaml`, `Pulumi.*.yaml` | `pulumi` | `brew install pulumi` |

### Language ecosystem

| Signal | CLI | Install |
|---|---|---|
| `package.json` with `"packageManager": "pnpm@..."` or `pnpm-lock.yaml` | `pnpm` | `npm install -g pnpm` |
| `package.json` with `"packageManager": "yarn@..."` or `yarn.lock` | `yarn` | `npm install -g yarn` |
| `package.json` with `bun.lockb` | `bun` | `brew install bun` |
| `package.json` (default) | `npm` | bundled with Node |
| `Cargo.toml` | `cargo` (Rust toolchain) | `https://rustup.rs` |
| `go.mod` | `go` | `brew install go` |
| `pyproject.toml` with `[tool.poetry]` | `poetry` | `pipx install poetry` |
| `pyproject.toml` with `[tool.uv]` or `uv.lock` | `uv` | `pipx install uv` (or `brew install uv`) |
| `requirements.txt`, `setup.py`, no Python pkg manager file | `pip` | bundled with Python |
| `Gemfile`, `Gemfile.lock` | `bundle` (Bundler) | `gem install bundler` |
| `composer.json` | `composer` | `brew install composer` |
| `pom.xml`, `mvnw` | `mvn` (Maven) or use the wrapper | `brew install maven` |
| `build.gradle`, `gradlew` | `gradle` or use the wrapper | `brew install gradle` |

### Build / CI helpers

| Signal | CLI | Install |
|---|---|---|
| `Makefile` | `make` | bundled with Xcode CLI tools / distro |
| `justfile`, `.justfile` | `just` | `brew install just` |
| `BUILD.bazel`, `WORKSPACE`, `MODULE.bazel` | `bazel` | `brew install bazel` (or `bazelisk`) |

### Generic utilities worth flagging if absent

Always useful to have on PATH for repo work; if absent, suggest:

| CLI | When to suggest | Install |
|---|---|---|
| `jq` | any JSON-heavy project (API responses, configs) | `brew install jq` |
| `yq` | YAML-heavy project (k8s, GH Actions, configs) | `brew install yq` |
| `rg` (ripgrep) | always — faster grep | `brew install ripgrep` |

## How to use this in `onboard`

1. **Walk the repo** for the signals above (lightweight `Read` + `Grep`).
   Build a *candidate set* of CLIs the project suggests.
2. **`which`-check** each candidate (`Bash`: `which <cli>`).
3. **Split into two lists:**
   - **available** — present on PATH.
   - **suggested** — project signals indicate it'd be useful but absent;
     surface the standard install command from this reference.
4. **Record** in `manifest.validation.clis.available` and
   `manifest.validation.clis.suggested` (both optional lists of strings).
5. **Don't ask about CLIs without project signals.** Don't suggest `aws`
   when there's no AWS smell in the repo.

The follow-up env interview can ask whether to use any *available* CLIs to
discover env details (deploy workflows via `gh`, GCP envs via `gcloud`,
namespaces via `kubectl`, …). Consent-gated — always ask before running.

## Install philosophy

The skill **suggests, doesn't auto-install**. CLI install commands are
ecosystem-specific and sometimes interactive (Docker Desktop, Rust toolchain),
so the agent doesn't run them by default. If the user explicitly asks
("install `gh` for me"), the agent can run the standard command shown above,
but the default flow is suggest + show command + let the human paste it.

Authentication (`gh auth login`, `aws configure`, `gcloud auth login`, …) is
*out of scope* for `onboard` — the user handles it.
