"""Bootstrap namespace for local profile and packaged-source setup."""

from ..org_framework_layout import bootstrap, install_packaged_sources, packaged_skill_path
from .starter import (
    STARTER_EXECUTION_PROFILE_ID,
    STARTER_RUNTIME_ADAPTERS,
    STARTER_TEAM_BLUEPRINT_ID,
    StarterConfigurationError,
    build_starter_team_instance,
)

__all__ = [
    "STARTER_EXECUTION_PROFILE_ID",
    "STARTER_RUNTIME_ADAPTERS",
    "STARTER_TEAM_BLUEPRINT_ID",
    "StarterConfigurationError",
    "bootstrap",
    "build_starter_team_instance",
    "install_packaged_sources",
    "packaged_skill_path",
]
