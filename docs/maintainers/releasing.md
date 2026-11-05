---
type: Reference
title: Releasing Agent Caravan
description: Maintainer guide for tagged builds and GitHub Releases.
---

# Releasing Agent Caravan

Releases use Git tags as their version source. The `setuptools-scm`
configuration derives the Python package version from the tag; do not add a
release version to `catalog-manifest.json`.

## Publish a release

1. Merge the intended release state to `main` and confirm its CI run passes.
2. Create and push a semantic version tag, for example:

   ```text
   git switch main
   git pull --ff-only
   git tag -a v0.1.0 -m "Agent Caravan 0.1.0"
   git push origin v0.1.0
   ```

3. The release workflow runs the verification matrix on Python 3.10 and 3.14.
   When it passes, the workflow builds and validates the wheel and source
   distribution, then creates a GitHub Release with generated notes and both
   package files attached.

The release workflow uses the repository's `GITHUB_TOKEN` with `contents: write`
only in the release job. It does not require a GitHub CLI installation on the
maintainer's computer, a personal access token, or PyPI credentials.

If verification or package validation fails, no release is created. If release
publication itself fails, inspect the Releases page before retrying. Correct the
issue and use a new version tag for the next release attempt; do not reuse a
published version number.

## Distribution scope

GitHub Releases are the current distribution channel. Publishing to PyPI is
not configured. If PyPI distribution is added, configure PyPI Trusted
Publishing for a separate workflow rather than storing a long-lived upload
token in repository secrets.
