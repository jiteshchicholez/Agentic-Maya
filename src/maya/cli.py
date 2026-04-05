from __future__ import annotations

import json
import multiprocessing as mp
import shutil
from pathlib import Path

import typer

from maya.config import load_config
from maya.enums import AgentStatus
from maya.loader import load_pipeline, load_policy, load_skill
from maya.runtime import OfflineSessionAdmin, SessionRuntime
from maya.utils import ensure_dir

app = typer.Typer(add_completion=False, help="Agentic maya CLI")


def _project_root(root: str) -> Path:
    return Path(root).resolve()


def _session_dir(project_root: Path, session_id: str) -> Path:
    config = load_config(project_root)
    return config.session_root_path(project_root) / session_id


def _echo_json(payload) -> None:
    typer.echo(json.dumps(payload, indent=2, default=str))


@app.command()
def run(
    pipeline_path: str = typer.Argument(..., help="Path to a pipeline YAML file."),
    root: str = typer.Option(".", help="Project root."),
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", help="Keep an attached interactive runtime for approvals."),
    session_id: str | None = typer.Option(None, help="Optional session id override."),
) -> None:
    project_root = _project_root(root)
    config = load_config(project_root)
    pipeline = load_pipeline((project_root / pipeline_path).resolve() if not Path(pipeline_path).is_absolute() else Path(pipeline_path))
    runtime = SessionRuntime(project_root=project_root, config=config, session_id=session_id)
    report = runtime.run_pipeline(pipeline, interactive=interactive)
    _echo_json({"session_id": report.session_id, "status": report.status, "step_outputs": report.step_outputs})


@app.command()
def status(session_id: str, root: str = typer.Option(".", help="Project root.")) -> None:
    project_root = _project_root(root)
    admin = OfflineSessionAdmin(_session_dir(project_root, session_id))
    _echo_json(admin.status(session_id))


@app.command()
def audit(session_id: str, root: str = typer.Option(".", help="Project root.")) -> None:
    project_root = _project_root(root)
    admin = OfflineSessionAdmin(_session_dir(project_root, session_id))
    _echo_json(admin.audit())


@app.command()
def checkpoint(session_id: str, reason: str = typer.Argument("manual"), root: str = typer.Option(".", help="Project root.")) -> None:
    project_root = _project_root(root)
    admin = OfflineSessionAdmin(_session_dir(project_root, session_id))
    _echo_json(admin.checkpoint(session_id, reason).model_dump(mode="json"))


@app.command()
def rollback(session_id: str, checkpoint_id: str, root: str = typer.Option(".", help="Project root.")) -> None:
    project_root = _project_root(root)
    admin = OfflineSessionAdmin(_session_dir(project_root, session_id))
    _echo_json(admin.rollback(checkpoint_id))


@app.command()
def pause(session_id: str, agent_id: str, root: str = typer.Option(".", help="Project root.")) -> None:
    project_root = _project_root(root)
    admin = OfflineSessionAdmin(_session_dir(project_root, session_id))
    admin.update_agent_status(session_id, agent_id, AgentStatus.PAUSED)
    typer.echo(f"Paused {agent_id}")


@app.command()
def resume(session_id: str, agent_id: str, root: str = typer.Option(".", help="Project root.")) -> None:
    project_root = _project_root(root)
    admin = OfflineSessionAdmin(_session_dir(project_root, session_id))
    admin.update_agent_status(session_id, agent_id, AgentStatus.RUNNING)
    typer.echo(f"Resumed {agent_id}")


@app.command()
def terminate(session_id: str, agent_id: str, root: str = typer.Option(".", help="Project root.")) -> None:
    project_root = _project_root(root)
    admin = OfflineSessionAdmin(_session_dir(project_root, session_id))
    admin.update_agent_status(session_id, agent_id, AgentStatus.TERMINATED)
    typer.echo(f"Terminated {agent_id}")


@app.command()
def approve(
    session_id: str,
    request_id: str,
    confirmation: str | None = typer.Option(None, help="Typed confirmation for CRITICAL requests."),
    root: str = typer.Option(".", help="Project root."),
) -> None:
    project_root = _project_root(root)
    admin = OfflineSessionAdmin(_session_dir(project_root, session_id))
    _echo_json(admin.approve(request_id, confirmation))


@app.command()
def deny(
    session_id: str,
    request_id: str,
    reason: str | None = typer.Option(None, help="Optional denial reason."),
    root: str = typer.Option(".", help="Project root."),
) -> None:
    project_root = _project_root(root)
    admin = OfflineSessionAdmin(_session_dir(project_root, session_id))
    _echo_json(admin.deny(request_id, reason))


@app.command("register-skill")
def register_skill(path: str, root: str = typer.Option(".", help="Project root.")) -> None:
    project_root = _project_root(root)
    config = load_config(project_root)
    skill = load_skill(Path(path))
    target_dir = ensure_dir(project_root / config.paths.skill_dir)
    shutil.copy2(Path(path), target_dir / Path(path).name)
    _echo_json(skill.model_dump(mode="json"))


@app.command("register-policy")
def register_policy(path: str, root: str = typer.Option(".", help="Project root.")) -> None:
    project_root = _project_root(root)
    config = load_config(project_root)
    policy = load_policy(Path(path))
    target_dir = ensure_dir(project_root / config.paths.policy_dir)
    shutil.copy2(Path(path), target_dir / Path(path).name)
    _echo_json(policy.model_dump(mode="json"))


@app.command()
def help(topic: str | None = typer.Argument(None)) -> None:
    topics = {
        "commands": "run, status, audit, checkpoint, rollback, pause, resume, terminate, approve, deny, register-skill, register-policy",
        "governance": "Agentic maya enforces intent, permissions, budgets, sandboxing, HITL, audit, and rollback controls.",
        "pipelines": "Pipelines are YAML files under pipelines/ with agents, flow steps, and global budgets.",
    }
    if topic:
        typer.echo(topics.get(topic, "No help available for that topic."))
        return
    for key, value in topics.items():
        typer.echo(f"{key}: {value}")


def main() -> None:
    mp.freeze_support()
    app()
