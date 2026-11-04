---
type: Concept
title: Artifact Model
description: Overview of Agent Caravan artifact types and how they relate to each other.
---

# Artifact Model

## Purpose

This page explains the first-class artifact types in the framework and how they relate to each other.

## Contents

- [Primary artifact types](#primary-artifact-types)
- [Responsibilities](#responsibilities)
- [Caravan templates](#caravan-templates)
- [Caravans](#caravans)
- [Domain knowledge](#domain-knowledge)
- [Capability knowledge](#capability-knowledge)
- [Runtime integrations](#runtime-integrations)
- [Runtime mappings](#runtime-mappings)
- [Configuration overrides](#configuration-overrides)
- [Resolved caravans](#resolved-caravans)

## Primary Artifact Types

The serialized framework contracts retain these primary artifact type identifiers:

- `role`
- `team-blueprint`
- `domain-pack`
- `runtime-adapter`
- `runtime-profile`

Supporting artifact concepts include:

- `organization-catalog`
- `team-instance`
- `specialization-pack`
- `overlay`
- `validation-profile`

See the [vocabulary](vocabulary.md) for the user-facing terminology and its
relationship to these identifiers.

## Responsibilities

A responsibility defines one stable lane of work. Its serialized artifact type
is `role`.

Examples:

- `program-manager`
- `tech-owner`
- `engineer`

Responsibilities define:

- mission
- ownership boundaries
- decision rights
- operating model
- runtime expectations

Responsibilities do not define prompts, tools, or vendors.

## Caravan Templates

A caravan template assembles responsibilities into an operating group shape.

It defines:

- included responsibilities
- stage flow
- debate model
- blocking model
- documentation ownership
- governance expectations

The current default organizational example is:

- `information-technology-core-team`

One template may be reused by many concrete teams across one or more organizations.

## Caravans

A caravan is a durable team built from a caravan template inside a specific organizational context.

It defines:

- which caravan template it uses
- which organization or catalog context it belongs to
- which domains or owned surfaces it carries by default
- which configuration overrides, responsibility variants, or runtime defaults it keeps persistently

This is how the framework supports one to many teams without forcing every team to fork its base template.

Team ownership is separate from task repository scope. A caravan may own
one or more repositories or code boundaries as durable routing context, while a
task selects its own bounded repository or work boundary for execution. Working
in a task repository does not by itself change the team's durable ownership.

## Domain Knowledge

Domain knowledge is a scoped knowledge attachment.

It defines:

- what the domain is
- where trusted knowledge lives
- how context should be loaded
- how base roles adapt in that domain

The current example is:

- `sample-product`

One domain knowledge artifact may be shared by many caravans at once.

## Capability Knowledge

Capability knowledge is a persistent scoped knowledge layer narrower than general domain knowledge.

It defines:

- team-owned slices of a larger product
- subdomain-specific source hierarchies
- durable conventions for one owned subsystem
- persistent team/domain guidance

This is the recommended pattern for products like Sample Product where several teams share one product but own different code surfaces and need different durable knowledge.

## Runtime Integrations

A runtime integration describes one implementation environment in capability terms.

It does not define the mapping for a specific role or team. It defines what the runtime can and cannot do.

Repository guidance uses `AGENTS.md` as Agent Caravan's portable entry point by
default. An adapter's optional `repository_guidance` declaration names the
runtime-native files, whether they are loaded automatically, and whether
guidance readers should follow explicit links. A binding maps the canonical
guidance when a harness uses a different native file. Resolution exposes this
declaration under `runtime.repository_guidance`; it does not create or rewrite
repository files. The local profile's `config.json` can override those fields
in one place, keyed by adapter ID.

Examples of runtime classes:

- direct model runtime
- agent SDK or native agent runtime
- low-code or managed agent platform
- broker or gateway agent platform
- orchestration framework

## Runtime Mappings

A runtime mapping maps already-defined framework artifacts to one runtime integration.

It defines:

- which artifacts it targets
- which runtime-native constructs represent them
- required capabilities
- fallback behavior
- permission and observability assumptions

## Configuration Overrides

Configuration overrides change artifacts across scopes. Their serialized artifact
type remains `overlay`.

Supported operations include:

- `add`
- `extend`
- `replace`
- `suppress`

These operations are resolved through deterministic precedence rules.

## Resolved Caravans

The framework does not execute directly from raw artifact catalogs.

Instead, a resolved caravan is produced by:

1. loading applicable artifacts
2. selecting organization and team context
3. attaching domain and specialization layers
4. applying configuration overrides
5. resolving references
6. selecting runtime integrations and bindings
7. validating the result

That resolved caravan is what a runtime implementation consumes.
