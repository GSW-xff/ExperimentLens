from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

import pandas as pd

from ..domain import Project


class ExperimentRepository(Protocol):
    """Storage boundary used by services; implementations may be local or remote."""

    def create_project(self, name: str, objective: str) -> Project: ...

    def save_project(self, project: Project) -> None: ...

    def get_project(self, project_id: str) -> Project: ...

    def list_projects(self) -> list[Project]: ...

    def project_dir(self, project_id: str) -> Path: ...

    def write_frame(self, project_id: str, name: str, frame: pd.DataFrame) -> None: ...

    def read_frame(self, project_id: str, name: str) -> pd.DataFrame: ...

    def write_json(self, project_id: str, relative_path: str, data: Any) -> Path: ...

    def read_json(self, project_id: str, relative_path: str, default: Any = None) -> Any: ...
