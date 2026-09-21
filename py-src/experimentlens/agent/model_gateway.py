from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field


class ModelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    messages: list[dict[str, str]]
    tools: list[dict[str, Any]] = Field(default_factory=list)
    max_tokens: int = Field(default=1024, ge=1)


class ModelResponse(BaseModel):
    content: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    finish_reason: str = "stop"


class ModelGateway(Protocol):
    def complete(self, request: ModelRequest) -> ModelResponse: ...


class MockModelGateway:
    """Deterministic offline gateway for orchestrator and CI tests."""

    def __init__(self, responses: Iterable[ModelResponse | dict[str, Any]]) -> None:
        self._responses = iter(
            response if isinstance(response, ModelResponse) else ModelResponse.model_validate(response)
            for response in responses
        )
        self.requests: list[ModelRequest] = []

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        try:
            return next(self._responses)
        except StopIteration as error:
            raise RuntimeError("mock model responses exhausted") from error
