from __future__ import annotations

from ..domain import Project
from ..repositories.interfaces import ExperimentRepository


class ProjectService:
    def __init__(self, repository: ExperimentRepository) -> None:
        self.repository = repository

    def create_project(
        self, name: str, objective: str, experiment_type: str = "general"
    ) -> Project:
        if not name.strip():
            raise ValueError("项目名称不能为空")
        return self.repository.create_project(name, objective, experiment_type)

    def list_projects(self) -> list[Project]:
        return self.repository.list_projects()

    def get_project(self, project_id: str) -> Project:
        return self.repository.get_project(project_id)
