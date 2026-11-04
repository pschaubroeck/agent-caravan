---
type: Concept
title: Overview
description: Purpose, scope, and boundaries of the reusable Agent Caravan operating model for AI delivery teams.
---

# Overview

## Purpose

The AI team framework is a reusable operating model for building, sharing, and customizing AI-based delivery teams.

It is designed to support:

- a single local AI team
- shared team definitions across a broader organization
- domain-specialized teams
- multiple AI runtime implementations
- controlled local overrides without breaking the shared model

The framework is intentionally:

- runtime-agnostic
- storage-agnostic
- VCS-agnostic

It defines the logical structure of an AI team system rather than forcing one toolchain, one vendor, or one repository strategy.

## Contents

- [Why this exists](#why-this-exists)
- [What the framework provides](#what-the-framework-provides)
- [Current default team shape](#current-default-team-shape)
- [Key design principles](#key-design-principles)
- [Documentation map](#documentation-map)
- [Implementation today](#implementation-today)

## Why This Exists

Most AI usage patterns start as prompts, scripts, or one-off agents. That works for experimentation, but it does not scale well when you need:

- explicit role boundaries
- repeatable team behavior
- reusable domain knowledge
- quality gates for the framework itself
- multiple runtime implementations
- organization-wide sharing plus local customization

This framework addresses that gap by separating:

- organizational meaning
- scoped knowledge
- runtime implementation
- validation

## What The Framework Provides

At a high level, the framework defines:

- reusable responsibility artifacts
- reusable caravan templates
- reusable domain knowledge artifacts
- a logical artifact and configuration override model
- a runtime capability and integration model
- a runtime mapping model
- a framework validation model

These pieces together make it possible to define AI teams in a portable way and then map them onto one or more AI runtimes later.

## Current Default Team Shape

The current default organizational team is the `information-technology-core-team`.

Its core roles are:

- `program-manager`
- `product-owner`
- `tech-owner`
- `engineer`
- `quality-engineer`
- `software-architect`
- `release-manager`

This team shape is only the starting point. The framework is designed to support variants, replacements, specialist lanes, and local overlays.

## Key Design Principles

- Keep the core role model stable.
- Treat domains as a separate specialization layer.
- Treat runtime implementation as a separate mapping layer.
- Validate resolved configurations, not only raw artifacts.
- Allow shared catalogs and local overlays to coexist.
- Avoid forcing storage, Git, or one vendor runtime into the framework contract.

## Documentation Map

The local source tree is organized by reader intent:

- [Getting Started](../getting-started.md) — contributor setup and a first source-tree example
- [Framework Concepts](framework-concepts.md) — mental model, terminology, and layering
- [Artifact Model](artifact-model.md) — artifact types and configuration override behavior
- [Team and Domain Design](team-and-domain-design.md) — roles, teams, and domain knowledge
- [Runtime Integration](../reference/runtime-integration.md) — adapters, capabilities, and bindings
- [Validation Model](../reference/validation-model.md) — quality gates and validation expectations
- [Packaging and Distribution](../reference/packaging-and-distribution.md) — publishing and sharing

## Implementation Today

This repository contains a Python reference implementation, a JSON artifact
catalog, runtime-specific bridge code, shareable skills, examples, and
conformance tests. The implementation consumes artifacts from the source paths
explicitly listed in a local profile; it does not make the framework contract
dependent on Git, GitLab, or the local JSON storage convention.

The runnable behavior has clear boundaries:

- `agent-caravan resolve` builds and validates the selected configuration.
- `agent-caravan run --dry-run` exercises the simulated Codex surface and
  records validated session evidence; it does not call a model or execute a
  live task.
- `agent-caravan handoff` exports and stores a runtime-neutral handoff; it does
  not launch or execute a runtime.
- Live execution is provided through runtime-specific integration surfaces and
  harness workflows, not by the CLI `run` command.

For the current adapter and profile examples, evidence levels, and limits, see
[Runtime Integration](../reference/runtime-integration.md). For the
repository's default team behavior, see the
[Core Team Operating Model](core-team-operating-model.md).
