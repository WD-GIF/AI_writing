# AGENTS.md

## Project overview

**AI_writing** (`WD-GIF/AI_writing`) is a greenfield repository. As of the initial commit, the only tracked file is `README.md` (title: `# AI_writing`). There is no application source, package manifests, Docker/Compose config, CI, or tests yet.

## Cursor Cloud specific instructions

### Services

| Service | Status |
|---------|--------|
| Application / API / UI | **Not present** — nothing to start |
| Database / cache / workers | **Not defined** |

When code is added, re-scan the repo for `package.json`, `pyproject.toml`, `docker-compose.yml`, or similar and update this section with how to run, lint, and test each service.

### VM toolchain (available on Cloud Agent VMs)

- **Git**: repo root is `/workspace`; default branch `main`.
- **Node.js**: v22.x via nvm (`/exec-daemon/node` or `~/.nvm`).
- **pnpm / npm**: available under nvm.
- **Python**: 3.12 (`python3`, `pip`).

### Lint / test / build / run

No scripts exist until dependency manifests and source are committed. After adding a stack, document commands here (e.g. `pnpm install`, `pnpm dev`, `pnpm test`, `pnpm lint`) and keep the VM **update script** limited to dependency refresh only (not service startup).

### Update script behavior

The registered update script is intentionally minimal (`true`) because there are no lockfiles or install steps. Once `package-lock.json`, `pnpm-lock.yaml`, `requirements.txt`, etc. exist, change the update script to the appropriate install command(s) only.
