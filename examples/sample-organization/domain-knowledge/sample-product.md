# Domain Knowledge: sample-product

## Identity

- `artifact_type`: `domain-pack`
- `id`: `sample-product`
- `name`: `Example Product Domain`
- `version`: `1.0.0`
- `scope`: `organization`

## Purpose

Provide shared terminology and product context for a fictional product with customer workflows and external integrations. Team specializations add narrower ownership and implementation guidance.

## Domain Intent

Example Product supports customer-facing workflows and exchanges data with external partner systems. Product behavior, workflow state, API contracts, and integration reliability are shared concerns. The two sample teams own different parts of this surface.

## Source Categories

- product and architecture documentation (`https://docs.example.org/sample-product/architecture`)
- repository instructions, source code, and tests
- work-item requirements and acceptance criteria
- support and operational guidance (`https://docs.example.org/sample-product/operations`)
- environment evidence when durable sources do not answer a material question

## Loading Guidance

1. identify the team that owns the requested surface
2. load that team's specialization
3. use this pack for shared product terminology and cross-team boundaries
4. inspect repository instructions and implementation sources
5. add request-specific context after durable sources

## Composition Rules

- team specializations narrow this shared domain; they do not replace it
- shared product contracts belong here
- team-specific ownership and conventions belong in that team's specialization
- surface unresolved ownership questions instead of guessing

## Validation Hints

- keep this pack broad enough to support both sample teams
- avoid team-specific ownership assumptions that conflict with their specializations
- each specialization identifies this domain as its parent
