"""Normalize and compose external knowledge access policy."""

from __future__ import annotations

from typing import Any


KNOWLEDGE_ACCESS_MODES = {"enabled", "approved_sources", "disabled"}
DEFAULT_KNOWLEDGE_ACCESS = {
    "external_sources": "enabled",
    "approved_sources": [],
}


class KnowledgeAccessError(ValueError):
    """Raised when an external knowledge access policy is malformed."""


def normalize_knowledge_access(value: Any = None) -> dict[str, Any]:
    """Return the canonical knowledge access shape, defaulting to enabled."""
    if value is None:
        value = {}
    if not isinstance(value, dict):
        raise KnowledgeAccessError("knowledge_access must be an object")

    mode = value.get("external_sources", DEFAULT_KNOWLEDGE_ACCESS["external_sources"])
    if mode not in KNOWLEDGE_ACCESS_MODES:
        raise KnowledgeAccessError(f"invalid external_sources mode: {mode}")

    approved_sources = value.get("approved_sources", [])
    if not isinstance(approved_sources, list):
        raise KnowledgeAccessError("approved_sources must be a list")

    normalized_sources = []
    for entry in approved_sources:
        if isinstance(entry, str):
            source = entry
            normalized = {"source": source}
        elif isinstance(entry, dict):
            source = entry.get("source")
            if "id" in entry and (not isinstance(entry["id"], str) or not entry["id"]):
                raise KnowledgeAccessError("approved source id must be a non-empty string")
            normalized = {"source": source}
            if "id" in entry:
                normalized["id"] = entry["id"]
        else:
            raise KnowledgeAccessError("approved source entries must be strings or objects")

        if not isinstance(source, str) or not source:
            raise KnowledgeAccessError("approved source source must be a non-empty string")
        normalized_sources.append(normalized)

    return {
        "external_sources": mode,
        "approved_sources": normalized_sources,
    }


def merge_knowledge_access(policies: list[dict[str, Any]]) -> dict[str, Any]:
    """Compose policy settings conservatively; disabled and approved sources win."""
    normalized = [normalize_knowledge_access(policy.get("knowledge_access")) for policy in policies]
    if not normalized:
        return normalize_knowledge_access()
    if any(item["external_sources"] == "disabled" for item in normalized):
        return {"external_sources": "disabled", "approved_sources": []}

    approved = [item["approved_sources"] for item in normalized if item["external_sources"] == "approved_sources"]
    if not approved:
        return {"external_sources": "enabled", "approved_sources": []}

    allowed_by_source = {
        entry["source"]: entry
        for entry in approved[0]
    }
    for entries in approved[1:]:
        sources = {entry["source"] for entry in entries}
        allowed_by_source = {
            source: entry for source, entry in allowed_by_source.items() if source in sources
        }
    return {
        "external_sources": "approved_sources",
        "approved_sources": list(allowed_by_source.values()),
    }
