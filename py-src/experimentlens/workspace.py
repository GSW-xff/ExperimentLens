from __future__ import annotations

import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Any

import pandas as pd

from .domain import Project, utc_now
from .migrations import migrate_project_payload


class Workspace:
    def __init__(self, root: str | Path | None = None):
        configured = root or os.environ.get("EXPERIMENTLENS_WORKSPACE")
        self.root = Path(configured or ".experimentlens/workspace").resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def project_dir(self, project_id: str) -> Path:
        safe = "".join(ch for ch in project_id if ch.isalnum() or ch in "-_")
        if safe != project_id or not safe:
            raise ValueError("invalid project id")
        return self.root / safe

    def create_project(
        self, name: str, objective: str, experiment_type: str = "general"
    ) -> Project:
        project_id = f"prj_{uuid.uuid4().hex[:10]}"
        project = Project(
            id=project_id,
            name=name.strip(),
            objective=objective.strip(),
            experiment_type=experiment_type,
        )
        directory = self.project_dir(project_id)
        for child in (
            "sources/original",
            "normalized",
            "analysis",
            "reports",
            "scratch",
        ):
            (directory / child).mkdir(parents=True, exist_ok=True)
        self.save_project(project)
        return project

    def save_project(self, project: Project) -> None:
        project.updated_at = utc_now()
        path = self.project_dir(project.id) / "project.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(project.model_dump_json(indent=2), encoding="utf-8")

    def get_project(self, project_id: str) -> Project:
        path = self.project_dir(project_id) / "project.json"
        if not path.exists():
            raise FileNotFoundError(project_id)
        return self._load_project(path)

    def list_projects(self) -> list[Project]:
        projects: list[Project] = []
        for path in self.root.glob("*/project.json"):
            try:
                projects.append(self._load_project(path))
            except (OSError, ValueError):
                continue
        return sorted(projects, key=lambda item: item.updated_at, reverse=True)

    def _load_project(self, path: Path) -> Project:
        payload = json.loads(path.read_text(encoding="utf-8"))
        migrated, manifest = migrate_project_payload(payload)
        project = Project.model_validate(migrated)
        if manifest is not None:
            backup_dir = path.parent / "migration-backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup = backup_dir / "v1-project.json"
            if not backup.exists():
                backup.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
                )
            manifest_path = backup_dir / "v1-to-v2-manifest.json"
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            temporary = path.with_suffix(".json.tmp")
            temporary.write_text(project.model_dump_json(indent=2), encoding="utf-8")
            temporary.replace(path)
        return project

    def save_upload(self, project_id: str, filename: str, stream) -> tuple[Path, str]:
        import hashlib

        safe_name = Path(filename).name.replace("\x00", "")
        if not safe_name:
            raise ValueError("empty filename")
        destination = self.project_dir(project_id) / "sources/original" / safe_name
        digest = hashlib.sha256()
        with destination.open("wb") as handle:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
                handle.write(chunk)
        return destination, digest.hexdigest()

    def write_frame(self, project_id: str, name: str, frame: pd.DataFrame) -> None:
        path = self.project_dir(project_id) / "normalized" / f"{name}.parquet"
        frame.to_parquet(path, index=False)

    def read_frame(self, project_id: str, name: str) -> pd.DataFrame:
        path = self.project_dir(project_id) / "normalized" / f"{name}.parquet"
        if not path.exists():
            return pd.DataFrame()
        return pd.read_parquet(path)

    def write_json(self, project_id: str, relative_path: str, data: Any) -> Path:
        path = self.project_dir(project_id) / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def read_json(self, project_id: str, relative_path: str, default: Any = None) -> Any:
        path = self.project_dir(project_id) / relative_path
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def reset_project_data(self, project_id: str) -> None:
        directory = self.project_dir(project_id)
        for name in ("normalized", "analysis", "reports"):
            target = directory / name
            if target.exists():
                shutil.rmtree(target)
            target.mkdir(parents=True, exist_ok=True)
