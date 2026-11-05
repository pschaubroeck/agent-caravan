---
type: Reference
title: Releasing Agent Caravan
description: Maintainer guide for tagged builds and GitHub Releases.
---

# Releasing Agent Caravan

Releases use Git tags as their version source. The `setuptools-scm`
configuration derives the Python package version from the tag; do not add a
release version to `catalog-manifest.json`.

## Publish a release from GitHub Actions

1. Merge the intended release state to `main` and confirm its CI run passes.
2. Open the repository's **Actions** tab, select the **CI** workflow, and click
   **Run workflow**.
3. Select `main` and enter a new version such as `v0.1.0`.
4. The workflow validates the request, runs checks on Python 3.10 and 3.14,
   builds and validates the wheel and source distribution, then creates the tag
   and publishes the GitHub Release with both package files attached.

The tag and release are created only after verification and package validation
pass. The version input must use `vMAJOR.MINOR.PATCH` and must not already exist.

The release workflow uses the repository's `GITHUB_TOKEN` with `contents: write`
only in the release job. It does not require a GitHub CLI installation on the
maintainer's computer, a personal access token, or PyPI credentials.

If verification or package validation fails, no tag or release is created.
Fix the issue on `main` and run the workflow again. Do not reuse a published
version number.

## Distribution scope

GitHub Releases are the current distribution channel. Publishing to PyPI is
not configured. If PyPI distribution is added, configure PyPI Trusted
Publishing for a separate workflow rather than storing a long-lived upload
token in repository secrets.
