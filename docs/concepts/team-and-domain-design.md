---
type: Concept
title: Team and Domain Design
description: How Agent Caravan models team composition and domain specialization.
---

# Team and Domain Design

## Purpose

This page explains how the framework models team structure and domain specialization.

## Contents

- [Team design](#team-design)
- [Default core roles](#default-core-roles)
- [Organization and team scaling](#organization-and-team-scaling)
- [Role variants](#role-variants)
- [Specialist lanes](#specialist-lanes)
- [Domain design](#domain-design)
- [Domain knowledge](#domain-knowledge)
- [Persistent specialization](#persistent-specialization)
- [Team and domain composition](#team-and-domain-composition)
- [Team design guidance](#team-design-guidance)
- [Domain design guidance](#domain-design-guidance)
- [Specialization design guidance](#specialization-design-guidance)

## Team Design

The framework's team layer exists to answer:

- which roles make up a team
- how work moves through them
- where debates happen
- where blocking authority lives
- how documentation and governance are handled

The current default team shape is the `information-technology-core-team`.

That team shape is a reusable template, not a singleton team for one organization.

## Default Core Roles

The current core role set is:

- `program-manager`
- `product-owner`
- `tech-owner`
- `engineer`
- `quality-engineer`
- `software-architect`
- `release-manager`

This is the starting team, not the only allowed team.

The framework is intended to support:

- one organization with many teams using the same shape
- many organizations reusing the same role and team foundations
- one team shape applied repeatedly with different owned surfaces and persistent knowledge

## Organization And Team Scaling

The framework distinguishes between:

- a reusable `team-blueprint`
- a durable `team-instance`
- a broader `domain-pack`
- a narrower persistent `specialization-pack`

That separation matters because several teams may all use `information-technology-core-team` while still differing in:

- owned repositories or code boundaries
- trusted documentation sources
- operational workflows
- runtime defaults
- durable product-specific knowledge

This is especially important for large products like Sample Product where multiple teams can share the same role structure but own different slices of the product.

## Role Variants

The framework supports role variants.

Example:

- `engineer-ii` extending `engineer`

This allows teams or organizations to add maturity or specialization without redefining the whole role catalog from scratch.

## Specialist Lanes

The framework is designed to support specialist lanes later.

Examples:

- `data-engineer`
- `security-engineer`
- `integration-architect`
- `business-intelligence-engineer`

Specialist lanes are expected to be optional additions or substitutions, not forced requirements for every team.

## Domain Design

Domains are modeled separately from teams because domain knowledge changes more often than responsibility structure.

Examples of domains:

- a GitLab group like `sample-product`
- a segment of a larger system like `Sample Product`
- a capability area like enrollment
- an integration surface like ServiceNow

## Domain Knowledge

Domain knowledge artifacts define:

- domain identity
- trusted source hierarchy
- loading order
- workflow-specific context
- responsibility-specific guidance inside the domain

This lets the same responsibility adapt to different problem spaces without becoming a new base responsibility.

## Persistent Specialization

Some specialization is broader than one ticket but narrower than an entire product domain.

Examples:

- one Sample Product team owning customer workflows
- one Sample Product team owning integrations
- one platform team owning a shared integration slice

That kind of durable knowledge should be modeled as capability knowledge
(serialized as `specialization-pack`), not as:

- a brand new base role
- a forked caravan template
- temporary prompt text copied from task to task

The recommended layering is:

- `team-blueprint`
- plus `team-instance`
- plus `domain-pack`
- plus one or more `specialization-pack` artifacts

## Team and Domain Composition

The typical composition pattern is:

- select a caravan template
- attach one or more domain knowledge artifacts
- apply configuration overrides if needed
- select a runtime integration and mapping
- validate the resolved caravan

This makes the framework flexible enough to support:

- one team across many domains
- many teams across one domain
- many teams across one product with different persistent capability knowledge
- many organizations reusing the same shared base artifacts
- organization-shared defaults with local variants

## Team Design Guidance

When creating a new caravan template:

- keep roles meaningful and distinct
- preserve core coverage lanes explicitly
- use configuration overrides instead of duplicating whole catalogs when possible
- keep domain behavior in domain knowledge, not caravan templates

## Domain Design Guidance

When creating a new domain knowledge artifact:

- start from the smallest useful domain
- identify the trusted source hierarchy clearly
- keep the pack as a curated index, not a full mirror of the source systems
- adapt roles through domain guidance rather than role redefinition whenever possible

## Specialization Design Guidance

When creating a persistent capability knowledge artifact:

- keep it narrower than the parent domain knowledge
- tie it to durable ownership boundaries, not one-off work
- prefer team-owned code and docs as the highest-trust sources inside the pack
- avoid redefining base role semantics unless the change is truly organizational rather than knowledge-driven
