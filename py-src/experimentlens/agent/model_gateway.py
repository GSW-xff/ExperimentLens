from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Iterable
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field


class ModelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    messages: list[dict[str, Any]]
    tools: list[dict[str, Any]] = Field(default_factory=list)
    max_tokens: int = Field(default=1024, ge=1)
    instructions: str | None = None
    model: str | None = None


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


class FallbackModelGateway:
    """Offline gateway that exercises the same tool loop without an external model."""

    model = "deterministic-fallback"

    def complete(self, request: ModelRequest) -> ModelResponse:
        tool_results = [
            message
            for message in request.messages
            if message.get("type") == "function_call_output"
        ]
        if not tool_results:
            return ModelResponse(
                content="",
                tool_calls=[{"id": "fallback-list", "name": "list_runs", "arguments": {}}],
                output_tokens=8,
                finish_reason="tool_call",
            )
        if len(tool_results) == 1:
            return ModelResponse(
                content="",
                tool_calls=[
                    {"id": "fallback-compare", "name": "compare_groups", "arguments": {}}
                ],
                input_tokens=8,
                output_tokens=8,
                finish_reason="tool_call",
            )
        return ModelResponse(
            content="已通过只读工具检查运行记录和组间统计。结论以当前项目的确定性分析结果为准，请结合所附证据查看具体 runs。",
            input_tokens=16,
            output_tokens=32,
        )


class OpenAIModelGateway:
    """Minimal OpenAI Responses API gateway with bounded retry and no response storage."""

    endpoint = "https://api.openai.com/v1/responses"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 30,
        max_retries: int = 2,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured")
        self.model = model or os.environ.get("EXPERIMENTLENS_MODEL", "gpt-5.6-luna")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def complete(self, request: ModelRequest) -> ModelResponse:
        payload = {
            "model": request.model or self.model,
            "input": request.messages,
            "instructions": request.instructions,
            "tools": request.tools,
            "tool_choice": "auto" if request.tools else "none",
            "parallel_tool_calls": False,
            "max_output_tokens": request.max_tokens,
            "store": False,
        }
        payload = {key: value for key, value in payload.items() if value is not None}
        encoded = json.dumps(payload).encode("utf-8")
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            http_request = urllib.request.Request(
                self.endpoint,
                data=encoded,
                method="POST",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
            try:
                with urllib.request.urlopen(
                    http_request, timeout=self.timeout_seconds
                ) as response:
                    return self._parse(json.loads(response.read().decode("utf-8")))
            except urllib.error.HTTPError as error:
                last_error = error
                if error.code not in {408, 409, 429, 500, 502, 503, 504}:
                    break
            except (TimeoutError, urllib.error.URLError) as error:
                last_error = error
            if attempt < self.max_retries:
                time.sleep(0.25 * (2**attempt))
        raise RuntimeError(f"OpenAI Responses API request failed: {last_error}") from last_error

    @staticmethod
    def _parse(payload: dict[str, Any]) -> ModelResponse:
        content_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        for item in payload.get("output", []):
            if item.get("type") == "function_call":
                arguments = item.get("arguments", "{}")
                tool_calls.append({
                    "id": item.get("call_id") or item.get("id"),
                    "name": item.get("name"),
                    "arguments": json.loads(arguments) if isinstance(arguments, str) else arguments,
                })
            if item.get("type") == "message":
                for block in item.get("content", []):
                    if block.get("type") == "output_text":
                        content_parts.append(block.get("text", ""))
        usage = payload.get("usage") or {}
        return ModelResponse(
            content="\n".join(part for part in content_parts if part),
            tool_calls=tool_calls,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            finish_reason="tool_call" if tool_calls else payload.get("status", "stop"),
        )
