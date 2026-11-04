"""Validate Agent Caravan JSON artifacts against local JSON Schema contracts."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


FRAMEWORK_ARTIFACT_SCHEMAS = {
    "organization-catalog": "organization-catalog.schema.json",
    "role": "role.schema.json",
    "team-blueprint": "team-blueprint.schema.json",
    "team-instance": "team-instance.schema.json",
    "domain-pack": "domain-pack.schema.json",
    "specialization-pack": "specialization-pack.schema.json",
    "overlay": "overlay.schema.json",
    "runtime-adapter": "runtime-adapter.schema.json",
    "runtime-profile": "runtime-profile.schema.json",
    "execution-profile": "execution-profile.schema.json",
    "policy": "policy.schema.json",
}
_SCOPE_ORDER = {"shared": 0, "organization": 1, "team": 2, "local": 3, "session": 4}
_MARKDOWN_ARTIFACT_HEADINGS = {
    "Role Artifact": ("role", "id"),
    "Team Blueprint Artifact": ("team-blueprint", "id"),
    "Organization Catalog": ("organization-catalog", "id"),
    "Team Instance": ("team-instance", "id"),
    "Domain Pack": ("domain-pack", "id"),
    "Specialization Pack": ("specialization-pack", "id"),
    "Overlay": ("overlay", "id"),
    "Runtime Adapter": ("runtime-adapter", "adapter id"),
    "Runtime Profile": ("runtime-profile", "id"),
    "Responsibility Artifact": ("role", "id"),
    "Caravan Template Artifact": ("team-blueprint", "id"),
    "Caravan": ("team-instance", "id"),
    "Domain Knowledge": ("domain-pack", "id"),
    "Capability Knowledge": ("specialization-pack", "id"),
    "Configuration Override": ("overlay", "id"),
    "Runtime Integration": ("runtime-adapter", "adapter id"),
    "Runtime Mapping": ("runtime-profile", "id"),
}
_MARKDOWN_SCOPES = {"shared", "organization", "team", "local", "session"}

_FORMAT_CHECKER = FormatChecker()


@_FORMAT_CHECKER.checks("date-time")
def _is_datetime(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _local_registry(schema_path: Path) -> Registry[Any]:
    """Build a registry containing this schema directory's local schema files."""
    schema_directory = schema_path.parent.resolve()
    schema_files = sorted(schema_directory.glob("*.schema.json"))
    raw_schemas: dict[Path, dict[str, Any]] = {
        path.resolve(): json.loads(path.read_text(encoding="utf-8"))
        for path in schema_files
    }
    if schema_path.resolve() not in raw_schemas:
        raw_schemas[schema_path.resolve()] = json.loads(schema_path.read_text(encoding="utf-8"))

    schemas: dict[Path, dict[str, Any]] = {}
    for path, contents in raw_schemas.items():
        normalized = dict(contents)
        declared_id = contents.get("$id")
        if isinstance(declared_id, str):
            normalized["$id"] = urljoin(path.as_uri(), declared_id)
        schemas[path] = normalized

    resources = {
        path: Resource.from_contents(contents)
        for path, contents in schemas.items()
    }
    aliases: dict[str, Resource[Any]] = {}

    for path, contents in schemas.items():
        file_uri = path.as_uri()
        aliases[file_uri] = resources[path]
        effective_id = contents.get("$id", file_uri)
        aliases[effective_id] = resources[path]

    # A relative $id can create a logical directory that differs from the
    # schema files' physical directory. Register only aliases for known direct
    # siblings so normal relative $ref values still resolve without filesystem
    # traversal or network retrieval.
    for base_path, contents in schemas.items():
        file_uri = base_path.as_uri()
        effective_id = contents.get("$id", file_uri)
        base_parts = urlsplit(effective_id)
        if base_parts.scheme != "file" or base_parts.netloc:
            continue
        for sibling_path, sibling_resource in resources.items():
            alias = urljoin(effective_id, sibling_path.name)
            alias_parts = urlsplit(alias)
            if alias_parts.scheme == "file" and not alias_parts.netloc:
                aliases[alias] = sibling_resource

    registry: Registry[Any] = Registry()
    for uri, resource in aliases.items():
        registry = registry.with_resource(uri, resource)
    return registry


def validate_artifact(instance: Any, schema_path: str | Path) -> None:
    """Validate an instance with Draft 2020-12 and local sibling references.

    ``schema_path`` selects a schema file. Only schema files in that file's
    directory are registered for reference resolution. The registry has no
    retrieval callback, so unknown or remote references cannot be fetched.

    Raises ``jsonschema.exceptions.ValidationError`` for an invalid instance
    and ``jsonschema.exceptions.SchemaError`` for an invalid schema.
    """
    path = Path(schema_path).resolve(strict=True)
    schema = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(schema.get("$id"), str):
        schema["$id"] = urljoin(path.as_uri(), schema["$id"])
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(
        schema,
        registry=_local_registry(path),
        format_checker=_FORMAT_CHECKER,
    )
    validator.validate(instance)


def validate_schema_file(schema_path: str | Path) -> None:
    """Validate one packaged JSON Schema document without validating an instance."""
    path = Path(schema_path).resolve(strict=True)
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)


def validate_packaged_artifact(instance: Any, schema_name: str) -> None:
    """Validate with one of the schemas shipped in the Agent Caravan package."""
    from agentcaravan.org_framework_layout import _bundled_root

    if Path(schema_name).name != schema_name or not schema_name.endswith(".schema.json"):
        raise ValueError("schema_name must be a schema filename, not a path")
    schema_path = _bundled_root() / "resources" / "schemas" / schema_name
    validate_artifact(instance, schema_path)


def validate_markdown_artifact_metadata(markdown: str) -> dict[str, str]:
    """Validate only the identity metadata convention used by Markdown artifacts.

    Markdown artifacts are not parsed as YAML or prose. This check reads the
    first artifact heading and the identity/version/scope bullets in their
    existing structured metadata sections.
    """
    heading_match = re.search(r"^# ([^:\n]+): ([^\n]+)$", markdown, re.MULTILINE)
    if heading_match is None:
        raise ValueError("missing artifact title heading")
    heading_type, heading_id = heading_match.groups()
    try:
        artifact_type, id_key = _MARKDOWN_ARTIFACT_HEADINGS[heading_type]
    except KeyError as exc:
        raise ValueError(f"unsupported artifact heading {heading_type!r}") from exc

    def field_value(key: str) -> str:
        pattern = re.compile(r"^- `" + re.escape(key) + r"`: `([^`]+)`\s*$", re.MULTILINE)
        values = pattern.findall(markdown)
        if len(values) != 1:
            raise ValueError(f"expected exactly one {key!r} metadata field")
        return values[0]

    artifact_id = field_value(id_key)
    version = field_value("version")
    scope = field_value("scope")
    if artifact_id != heading_id:
        raise ValueError(f"heading id {heading_id!r} does not match metadata id {artifact_id!r}")
    if scope not in _MARKDOWN_SCOPES:
        raise ValueError(f"invalid artifact scope {scope!r}")
    declared_type = re.findall(r"^- `artifact_type`: `([^`]+)`\s*$", markdown, re.MULTILINE)
    if declared_type and (len(declared_type) != 1 or declared_type[0] != artifact_type):
        raise ValueError(f"artifact_type metadata must be {artifact_type!r}")
    return {"artifact_type": artifact_type, "id": artifact_id, "version": version, "scope": scope}


def validate_framework_artifact(instance: Any) -> None:
    """Validate a serialized portable framework artifact by its declared type."""
    if not isinstance(instance, dict):
        raise ValueError("framework artifact must be an object")
    artifact_type = instance.get("artifact_type")
    try:
        schema_name = FRAMEWORK_ARTIFACT_SCHEMAS[artifact_type]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"no portable artifact schema for type {artifact_type!r}") from exc
    validate_packaged_artifact(instance, schema_name)


def validate_framework_artifacts(artifacts: list[dict[str, Any]]) -> dict[str, int]:
    """Validate artifact schemas and references within one complete artifact set."""
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    for artifact in artifacts:
        validate_framework_artifact(artifact)
        key = (artifact["artifact_type"], artifact["id"])
        if key in indexed:
            raise ValueError(f"duplicate artifact: {key[0]}:{key[1]}")
        indexed[key] = artifact

    def require_ref(source: dict[str, Any], artifact_type: str, artifact_id: Any, field: str) -> None:
        if not isinstance(artifact_id, str) or (artifact_type, artifact_id) not in indexed:
            raise ValueError(
                f"{source['artifact_type']}:{source['id']} has unresolved {field} "
                f"reference {artifact_type}:{artifact_id}"
            )

    for artifact in artifacts:
        artifact_type = artifact["artifact_type"]
        if artifact_type == "organization-catalog":
            for published_type, identifiers in artifact["published_artifacts"].items():
                for identifier in identifiers:
                    require_ref(artifact, published_type, identifier, "published_artifacts")
        elif artifact_type == "team-blueprint":
            for role_id in artifact["core_roles"] + artifact.get("optional_roles", []):
                require_ref(artifact, "role", role_id, "role")
            for participants in artifact.get("debate_participants", {}).values():
                for role_id in participants:
                    require_ref(artifact, "role", role_id, "debate participant")
            for role_id in artifact.get("blocking_lanes", []):
                require_ref(artifact, "role", role_id, "blocking lane")
        elif artifact_type == "team-instance":
            if artifact.get("organization_catalog_id"):
                require_ref(artifact, "organization-catalog", artifact["organization_catalog_id"], "organization_catalog_id")
            require_ref(artifact, "team-blueprint", artifact["team_blueprint_id"], "team_blueprint_id")
            for field, ref_type in (("role_overlays", "overlay"), ("domain_packs", "domain-pack"), ("specialization_packs", "specialization-pack"), ("runtime_defaults", "runtime-adapter")):
                for identifier in artifact.get(field, []):
                    require_ref(artifact, ref_type, identifier, field)
        elif artifact_type == "runtime-profile":
            require_ref(artifact, "runtime-adapter", artifact["target_adapter_id"], "target_adapter_id")
            if artifact.get("target_team_blueprint_id"):
                require_ref(artifact, "team-blueprint", artifact["target_team_blueprint_id"], "target_team_blueprint_id")
            for profile_id in artifact.get("execution_profile_ids", []):
                require_ref(artifact, "execution-profile", profile_id, "execution_profile_ids")
        elif artifact_type == "execution-profile":
            if artifact.get("team_blueprint_id"):
                require_ref(artifact, "team-blueprint", artifact["team_blueprint_id"], "team_blueprint_id")
            for role_id in artifact.get("entry_roles", []):
                require_ref(artifact, "role", role_id, "entry_roles")
            for stage in artifact.get("stages", []):
                for role_id in stage.get("roles", []):
                    require_ref(artifact, "role", role_id, "stage roles")
            for policy_id in artifact.get("policy_ids", []):
                require_ref(artifact, "policy", policy_id, "policy_ids")
        elif artifact_type == "domain-pack":
            for role_id in artifact.get("base_role_ids", []):
                require_ref(artifact, "role", role_id, "base_role_ids")
            if artifact.get("parent_domain_id"):
                require_ref(artifact, "domain-pack", artifact["parent_domain_id"], "parent_domain_id")
        elif artifact_type == "specialization-pack":
            require_ref(artifact, "team-instance", artifact["owner_team_instance_id"], "owner_team_instance_id")
            require_ref(artifact, "domain-pack", artifact["parent_domain_id"], "parent_domain_id")
        elif artifact_type == "overlay":
            operation = artifact["operation"]
            if operation in {"extend", "replace", "suppress"}:
                require_ref(artifact, artifact["target_artifact_type"], artifact["target_artifact_id"], "target")
                target = indexed[(artifact["target_artifact_type"], artifact["target_artifact_id"])]
                if _SCOPE_ORDER[target["scope"]] > _SCOPE_ORDER[artifact["scope"]]:
                    raise ValueError(f"overlay {artifact['id']} is broader than its target scope")
            if operation == "replace":
                require_ref(artifact, artifact["replacement_artifact_type"], artifact["replacement_artifact_id"], "replacement")
                if artifact["replacement_artifact_type"] != artifact["target_artifact_type"]:
                    raise ValueError(f"overlay {artifact['id']} replacement type must match target type")
                replacement = indexed[(artifact["replacement_artifact_type"], artifact["replacement_artifact_id"])]
                if _SCOPE_ORDER[replacement["scope"]] > _SCOPE_ORDER[artifact["scope"]]:
                    raise ValueError(f"overlay {artifact['id']} is broader than its replacement scope")
            if operation == "add":
                require_ref(artifact, artifact["added_artifact_type"], artifact["added_artifact_id"], "added artifact")

    # A publication list must resolve by type and ID. Catalog entries may omit
    # artifacts outside this bundle, so references are checked only when a
    # catalog declares them here; the complete-set caller owns bundle scope.
    return {"artifacts": len(artifacts), "types": len({item["artifact_type"] for item in artifacts})}
