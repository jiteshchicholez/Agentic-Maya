from __future__ import annotations

from pathlib import Path

import yaml

from maya.schemas import PipelineDefinition, PolicyDefinition, SkillDefinition


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a top-level mapping")
    return data


def load_pipeline(path: Path) -> PipelineDefinition:
    return PipelineDefinition.model_validate(_load_yaml(path))


def load_skill(path: Path) -> SkillDefinition:
    return SkillDefinition.model_validate(_load_yaml(path))


def load_policy(path: Path) -> PolicyDefinition:
    return PolicyDefinition.model_validate(_load_yaml(path))


def load_directory_models(directory: Path, loader):
    if not directory.exists():
        return []
    return [loader(path) for path in sorted(directory.glob("*.yml"))]
