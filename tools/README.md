# Tools

Repository maintenance and publication helpers live here. These tools are not part of the runtime-neutral framework contract.

## Local Initialization

From the repository root, run:

```text
make init
```

The target invokes `init_agentcaravan.py`, which interactively creates or
selects an organization and creates its starter Information Technology Core
Team. It uses the same starter setup and resolution path as the package CLI,
installs the managed Codex skills, and prints the next `configure` and dry-run
commands. Existing user-owned sources and non-symlink skill paths are
preserved.

For package installs, use `agent-caravan init --runtime codex` to install the
supported skill set. Managed skill copies carry a marker and are refreshed
through a staged replacement. Unmarked directories are preserved unless they
exactly match the packaged copy, which permits safe adoption of legacy
Agent Caravan installs. The marker must identify the package, skill, format,
and SHA-256 content fingerprint. Malformed or mismatched markers, changed
unmarked directories, and unexpected symlinks are preserved as unmanaged
content. Replacement is prepared beside the destination and rolled back if
the final rename fails.

## Offline Package Smoke Test

From the repository root, run:

```text
make package-smoke
```

The target builds and installs a temporary wheel into an isolated target
directory without contacting package registries, then runs the
installed-distribution integration test. It is a local distribution check and
also runs in GitHub Actions.
Run it from Python 3.10+ with the pinned `setuptools`, `setuptools-scm`, and
`wheel` build tools already installed.
