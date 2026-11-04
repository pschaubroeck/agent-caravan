"""Runtime-neutral human-facing team configuration helpers."""

from __future__ import annotations

from pathlib import Path
from pathlib import PureWindowsPath
import re
from typing import Any


TEAM_DOCUMENTS = (
    ("caravan.md", "Team mission and practical scope"),
    ("repositories.md", "Relevant repositories, services, and workspaces"),
    ("knowledge.md", "Trusted documentation and instruction sources"),
    ("working-agreements.md", "Team-specific working agreements"),
    ("instructions.md", "Durable team-specific AI instructions"),
    ("responsibilities.md", "Preferred roles and participation guidance"),
)
_SAFE_TEAM_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$")
_PROMPT_PLACEHOLDER_TEXT = {
    "relevant repositories",
    "services",
    "or workspaces?",
    "relevant repositories, services, or workspaces?",
}


def _is_prompt_placeholder(value: str) -> bool:
    normalized = " ".join(value.strip().casefold().split())
    return (
        not normalized
        or normalized in _PROMPT_PLACEHOLDER_TEXT
        or normalized.startswith("add ")
        or normalized.startswith("[") and "enter" in normalized
        or "press enter" in normalized
    )


def _clean_text(value: Any) -> str:
    if not isinstance(value, str) or _is_prompt_placeholder(value):
        return ""
    return value.strip()


def _is_local_path(value: str) -> bool:
    """Return whether a work-surface value is an absolute machine path."""
    return Path(value).expanduser().is_absolute() or PureWindowsPath(value).is_absolute()


def portable_work_surfaces(values: list[str]) -> list[str]:
    """Keep repository identities and relative surfaces, excluding local paths."""
    return [value for value in values if not _is_local_path(value)]


def _remove_prompt_placeholder_lines(value: str) -> str:
    """Remove starter prompt lines without discarding adjacent user content."""
    return "\n".join(
        line
        for line in value.splitlines()
        if not _is_prompt_placeholder(
            line.strip()[2:].strip() if line.strip().startswith("- ") else line.strip()
        )
    ).strip()


def team_workspace(root: str | Path, team_id: str) -> Path:
    """Return the local authoring workspace for one team."""
    if not isinstance(team_id, str) or not _SAFE_TEAM_ID.fullmatch(team_id):
        raise ValueError("team_id must be a filesystem-safe identifier")
    profile_root = Path(root).expanduser().resolve()
    teams_root = profile_root / "caravans"
    if teams_root.is_symlink():
        raise ValueError("team workspace root must not be a symlink")
    return teams_root / team_id


def split_entries(value: str) -> list[str]:
    """Parse a simple comma-separated guided input into clean entries."""
    return [
        entry.strip()
        for entry in value.split(",")
        if entry.strip() and not _is_prompt_placeholder(entry)
    ]


def build_team_context(
    *,
    mission: str,
    repositories: str,
    knowledge: str,
    working_agreements: str,
    workspace: Path,
) -> dict[str, Any]:
    """Build the runtime-neutral context stored on a configured team."""
    return {
        "mission": mission.strip(),
        "work_surfaces": split_entries(repositories),
        "knowledge_sources": split_entries(knowledge),
        "working_agreements": _clean_text(working_agreements),
        "instructions": "",
        "preferred_roles": [],
        "role_guidance": "",
        "authoring_workspace": str(workspace),
    }


def render_team_documents(team_name: str, context: dict[str, Any]) -> dict[str, str]:
    """Render the four approachable Markdown files for a configured team."""
    work_surfaces = context.get("work_surfaces", [])
    knowledge_sources = context.get("knowledge_sources", [])
    repositories = "\n".join(f"- {item}" for item in work_surfaces) or "- Add repositories, services, or workspaces here."
    knowledge = "\n".join(f"- {item}" for item in knowledge_sources) or "- Add trusted documentation or instruction sources here."
    agreements = context.get("working_agreements") or "Add team-specific testing, review, escalation, or delivery agreements here."
    preferred_roles = context.get("preferred_roles", [])
    roles = "\n".join(f"- {item}" for item in preferred_roles) or "- Add preferred role IDs here."
    instructions = context.get("instructions") or "Add durable team-specific AI instructions here."
    role_guidance = context.get("role_guidance") or "Add guidance for how preferred roles should participate here."
    return {
        "caravan.md": f"# {team_name}\n\n## Mission\n\n{context.get('mission', '').strip()}\n",
        "repositories.md": (
            f"# {team_name} Work Surfaces\n\n"
            "List repositories, services, workspaces, or monorepo paths this team commonly works in.\n\n"
            f"{repositories}\n"
        ),
        "knowledge.md": (
            f"# {team_name} Knowledge Sources\n\n"
            "List trusted documentation and repository instruction sources, one entry per line.\n\n"
            f"{knowledge}\n"
        ),
        "working-agreements.md": (
            f"# {team_name} Working Agreements\n\n"
            "Record durable team-specific expectations that should guide implementation and review.\n\n"
            f"{agreements}\n"
        ),
        "instructions.md": (
            f"# {team_name} AI Instructions\n\n"
            "Record durable instructions that should guide this team’s AI-assisted work.\n\n"
            f"{instructions}\n"
        ),
        "responsibilities.md": (
            f"# {team_name} Role Guidance\n\n"
            "## Preferred roles\n\n"
            "List preferred Agent Caravan role IDs, one per line.\n\n"
            f"{roles}\n\n"
            "## Participation guidance\n\n"
            f"{role_guidance}\n"
        ),
    }


def update_team_documents(
    team_name: str,
    context: dict[str, Any],
    existing_documents: dict[str, str],
) -> dict[str, str]:
    """Render prompted team fields while retaining unprompted team guidance."""
    documents = render_team_documents(team_name, context)
    for filename in ("instructions.md", "responsibilities.md"):
        if filename in existing_documents:
            documents[filename] = existing_documents[filename]

    existing_team = existing_documents.get("caravan.md")
    if existing_team:
        lines = existing_team.splitlines()
        try:
            section_start = lines.index("## Mission")
        except ValueError:
            pass
        else:
            section_end = next(
                (index for index in range(section_start + 1, len(lines)) if lines[index].startswith("## ")),
                len(lines),
            )
            rendered_lines = documents["caravan.md"].splitlines()
            mission_start = rendered_lines.index("## Mission")
            mission_end = next(
                (index for index in range(mission_start + 1, len(rendered_lines)) if rendered_lines[index].startswith("## ")),
                len(rendered_lines),
            )
            documents["caravan.md"] = "\n".join(
                lines[:section_start]
                + rendered_lines[mission_start:mission_end]
                + lines[section_end:]
            ) + "\n"
    return documents


def load_team_context(workspace: str | Path, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    """Read the standard team Markdown files into portable team context."""
    workspace = Path(workspace)
    fallback = fallback or {}
    documents: dict[str, str] = {}
    for filename, _ in TEAM_DOCUMENTS:
        path = workspace / filename
        if path.is_symlink():
            raise ValueError(f"team workspace document must not be a symlink: {path}")
        if path.is_file():
            documents[filename] = path.read_text(encoding="utf-8")

    team_document = documents.get("caravan.md", "")
    mission_match = re.search(r"## Mission\s+(.+?)(?:\n## |\Z)", team_document, re.DOTALL)
    mission = mission_match.group(1).strip() if mission_match else fallback.get("mission", "")

    def list_document(filename: str, fallback_key: str) -> list[str]:
        values = []
        for line in documents.get(filename, "").splitlines():
            if line.startswith("- "):
                value = line[2:].strip()
                if value and not _is_prompt_placeholder(value):
                    values.append(value)
        cleaned_fallback = [
            item for item in fallback.get(fallback_key, [])
            if isinstance(item, str) and not _is_prompt_placeholder(item)
        ]
        if filename == "repositories.md":
            # The profile-local repository list may add checkout paths, while
            # shared repository identities remain authoritative on the artifact.
            combined = cleaned_fallback + values
            return list(dict.fromkeys(combined))
        return values or cleaned_fallback

    agreements_document = documents.get("working-agreements.md", "")
    agreement_parts = agreements_document.split("\n\n", 2)
    working_agreements = (
        agreement_parts[2].strip()
        if len(agreement_parts) == 3 and agreement_parts[2].strip()
        else _clean_text(fallback.get("working_agreements", ""))
    )
    working_agreements = _remove_prompt_placeholder_lines(working_agreements)
    if not working_agreements:
        working_agreements = _clean_text(fallback.get("working_agreements", ""))
    instructions_document = documents.get("instructions.md", "")
    instructions = "\n\n".join(instructions_document.split("\n\n")[1:]).strip()
    generated_intro = "Record durable instructions that should guide this team’s AI-assisted work."
    if instructions.startswith(generated_intro):
        instructions = instructions[len(generated_intro):].strip()
    instructions = _remove_prompt_placeholder_lines(instructions)
    if not instructions:
        instructions = _clean_text(fallback.get("instructions", ""))
    roles_document = documents.get("responsibilities.md", "")
    preferred_roles_match = re.search(r"## Preferred roles\s+(.+?)(?:\n## |\Z)", roles_document, re.DOTALL)
    preferred_roles = []
    if preferred_roles_match:
        preferred_roles = [
            line[2:].strip()
            for line in preferred_roles_match.group(1).splitlines()
            if line.startswith("- ") and line[2:].strip() and not line[2:].strip().startswith("Add ")
        ]
    participation_match = re.search(r"## Participation guidance\s+(.+?)\Z", roles_document, re.DOTALL)
    role_guidance = (
        participation_match.group(1).strip()
        if participation_match and participation_match.group(1).strip()
        else _clean_text(fallback.get("role_guidance", ""))
    )
    role_guidance = _remove_prompt_placeholder_lines(role_guidance)
    if not role_guidance:
        role_guidance = _clean_text(fallback.get("role_guidance", ""))
    return {
        "mission": mission,
        "work_surfaces": list_document("repositories.md", "work_surfaces"),
        "knowledge_sources": list_document("knowledge.md", "knowledge_sources"),
        "working_agreements": working_agreements,
        "instructions": instructions,
        "preferred_roles": preferred_roles or list(fallback.get("preferred_roles", [])),
        "role_guidance": role_guidance,
        "authoring_workspace": str(workspace),
        "documents": documents,
    }


__all__ = [
    "TEAM_DOCUMENTS",
    "build_team_context",
    "load_team_context",
    "render_team_documents",
    "update_team_documents",
    "split_entries",
    "team_workspace",
]
