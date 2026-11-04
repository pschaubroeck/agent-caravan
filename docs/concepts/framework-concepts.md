---
type: Concept
title: Framework Concepts
description: Core mental model and artifact layers of the Agent Caravan framework.
---

# Framework Concepts

## Purpose

This page explains the core mental model of the AI team framework.

## Contents

- [Core idea](#core-idea)
- [Responsibility and domain composition](#responsibility-and-domain-composition)
- [Shared versus local](#shared-versus-local)
- [Storage independence](#storage-independence)
- [Runtime independence](#runtime-independence)
- [Configuration overrides](#configuration-overrides)
- [Canonical versus reference documentation](#canonical-versus-reference-documentation)

## Core Idea

The framework is based on a simple separation:

- **responsibilities** define accountable lanes of work
- **caravans** define operating structure
- **domain and capability knowledge** define scoped knowledge
- **runtime integrations and mappings** describe the implementation
- **validation** defines quality expectations

This separation is what keeps the framework portable and scalable.

## Responsibility and Domain Composition

The framework does not create a new responsibility for every product area.

Instead, specialization is created through composition:

- a base responsibility
- domain knowledge
- a runtime mapping

Examples:

- `engineer` + `sample-product`
- `tech-owner` + `Sample Product`
- `software-architect` + `ServiceNow integration`

This keeps the responsibility model stable while still allowing specialization.

## Shared Versus Local

The framework is designed for multiple sharing levels to coexist.

### Shared

Reusable across a wider organization or community.

Examples:

- responsibility catalogs
- caravan templates
- domain knowledge templates

### Organization

Published for one company or organization boundary.

Examples:

- official team definitions
- standard domain knowledge
- approved runtime mappings

### Team

Published for one subgroup or team.

Examples:

- team-specific role variants
- team-specific domain segments
- team-specific operating tweaks

### Local

Private or user-specific.

Examples:

- experimentation
- local configuration overrides
- temporary derived variants

## Storage Independence

The framework does not require:

- Git
- GitHub
- GitLab
- local files
- a database
- a single repository

It only requires that the logical artifacts can be loaded, resolved, and validated.

That means the same framework could be implemented through:

- files
- APIs
- registries
- document stores
- generated bundles
- mixed systems

## Runtime Independence

The framework also does not assume one AI runtime.

It is designed to support:

- direct model usage
- agent SDKs
- managed agent platforms
- broker/gateway products
- orchestration frameworks

The framework does this by defining capabilities generically and then using runtime mappings to map those capabilities to a specific implementation.

## Configuration Overrides

Configuration overrides allow customization without breaking the shared base model.
The serialized artifact type remains `overlay`.

The main override operations are:

- `add`
- `extend`
- `replace`
- `suppress`

This allows changes such as:

- adding `engineer-ii`
- replacing a role locally
- suppressing a role in a minimal team
- extending a shared caravan template with local additions

## Canonical Versus Reference Documentation

The framework separates:

- **canonical artifacts**
  - formal role, team, domain, runtime, and validation artifacts
- **reference documentation**
  - human-friendly overview and guides

This avoids duplicating the most detailed definitions in multiple places.
