---
type: Reference
title: Releasing Agent Caravan
description: Maintainer guide for tagged builds and GitHub Releases.
---

# Releasing Agent Caravan

Releases use Git tags as their version source. The `setuptools-scm`
configuration derives the Python package version from the tag; do not add a
release version to `catalog-manifest.json`.

## Publish a release from GitHub

1. Merge the intended release state to `main` and confirm its CI run passes.
2. Open the repository's **Releases** page and choose **Draft a new release**.
3. In **Choose a tag**, enter a semantic version such as `v0.1.0`, choose
   **Create new tag**, and set the target to `main`.
4. Add or generate the release notes, then choose **Save draft**. Saving the
   draft creates the tag and starts the release workflow.
5. The tag-creation event starts the release workflow, which runs the
   verification matrix on Python 3.10 and 3.14.
   When it passes, the workflow builds and validates the wheel and source
   distribution, attaches both files to the draft, and publishes the release.

GitHub's release form supports creating a new tag and saving the release as a
draft. Saving as a draft lets CI attach the package files before the release is
made public. See [GitHub's release instructions](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository).

Pushing a new semantic version tag directly also starts the workflow. In that case,
the workflow creates a draft release with generated notes before attaching the
package files and publishing it.

The release workflow uses the repository's `GITHUB_TOKEN` with `contents: write`
only in the release job. It does not require a GitHub CLI installation on the
maintainer's computer, a personal access token, or PyPI credentials.

If verification or package validation fails, a UI-created draft remains
unpublished. For a tag pushed directly, no release is created until checks pass.
For a code fix, merge the fix and create a new version tag. For a transient
workflow failure, rerun that workflow run. Do not move a tag that identifies a
published release.

## Distribution scope

GitHub Releases are the current distribution channel. Publishing to PyPI is
not configured. If PyPI distribution is added, configure PyPI Trusted
Publishing for a separate workflow rather than storing a long-lived upload
token in repository secrets.
