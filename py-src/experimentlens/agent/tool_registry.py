from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ValidationError

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


@dataclass(frozen=True)
class RegisteredTool(Generic[InputT, OutputT]):
    name: str
    description: str
    input_model: type[InputT]
    output_model: type[OutputT]
    handler: Callable[[InputT], OutputT | dict[str, Any]]
    read_only: bool = True
    has_external_side_effects: bool = False
    requires_approval: bool = False


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool[Any, Any]] = {}

    def register(self, tool: RegisteredTool[Any, Any]) -> None:
        if tool.name in self._tools:
            raise ValueError(f"tool already registered: {tool.name}")
        if tool.has_external_side_effects and not tool.requires_approval:
            raise ValueError("tools with external side effects must require approval")
        self._tools[tool.name] = tool

    def get(self, name: str) -> RegisteredTool[Any, Any]:
        try:
            return self._tools[name]
        except KeyError as error:
            raise ValueError(f"unregistered tool: {name}") from error

    def invoke(self, name: str, arguments: dict[str, Any], *, approved: bool = False) -> BaseModel:
        tool = self.get(name)
        if tool.requires_approval and not approved:
            raise PermissionError(f"tool requires approval: {name}")
        extras = set(arguments) - set(tool.input_model.model_fields)
        if extras:
            raise ValueError(f"unexpected arguments for {name}: {', '.join(sorted(extras))}")
        try:
            validated = tool.input_model.model_validate(arguments)
        except ValidationError as error:
            raise ValueError(f"invalid arguments for {name}: {error}") from error
        return tool.output_model.model_validate(tool.handler(validated))

    def schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_model.model_json_schema(),
                "output_schema": tool.output_model.model_json_schema(),
                "read_only": tool.read_only,
                "requires_approval": tool.requires_approval,
            }
            for tool in self._tools.values()
        ]

    def model_tools(self) -> list[dict[str, Any]]:
        """Return OpenAI Responses API function tool declarations."""
        return [
            {
                "type": "function",
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_model.model_json_schema(),
            }
            for tool in self._tools.values()
        ]
