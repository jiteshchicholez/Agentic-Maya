from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import BaseModel, Field

from myna.enums import LocalOrCloud
from myna.utils import ensure_dir


class ProviderConfig(BaseModel):
    name: str = "openai_compatible"
    base_url: str = "http://localhost:11434/v1"
    api_key: str = "not-needed"
    chat_model: str = "gpt-4.1-mini"
    fallback_model: str = "gpt-4.1-mini"
    embedding_model: str = "text-embedding-3-small"
    local_or_cloud: LocalOrCloud = LocalOrCloud.LOCAL


class PathsConfig(BaseModel):
    session_root: str = ".myna/sessions"
    skill_dir: str = "skills"
    policy_dir: str = "policies"
    pipeline_dir: str = "pipelines"


class LimitsConfig(BaseModel):
    default_max_subagents: int = 3
    default_timeout_sec: int = 300


class AppConfig(BaseModel):
    provider: ProviderConfig = Field(default_factory=ProviderConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    limits: LimitsConfig = Field(default_factory=LimitsConfig)

    def session_root_path(self, project_root: Path) -> Path:
        return ensure_dir(project_root / self.paths.session_root)


def load_config(project_root: Path, config_name: str = "myna.toml") -> AppConfig:
    config_path = project_root / config_name
    if not config_path.exists():
        return AppConfig()
    with config_path.open("rb") as handle:
        payload = tomllib.load(handle)
    return AppConfig.model_validate(payload)
