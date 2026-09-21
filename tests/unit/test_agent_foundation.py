import pandas as pd
import pytest
from experimentlens.agent import MockModelGateway, ModelRequest, RegisteredTool, ToolRegistry
from experimentlens.domain import AgentRun, EvaluationCase, ToolCall, TraceSpan
from experimentlens.evidence_validator import EvidenceValidator, InvalidEvidenceError
from pydantic import BaseModel


class EchoInput(BaseModel):
    value: int


class EchoOutput(BaseModel):
    doubled: int


def test_agent_trace_and_evaluation_models_validate_core_state():
    tool_call = ToolCall(id="tc-1", agent_run_id="ar-1", tool_name="echo")
    run = AgentRun(id="ar-1", project_id="p-1", question="compare groups", tool_calls=[tool_call])
    span = TraceSpan(id="s-1", trace_id="t-1", name="agent.run", duration_ms=12.5)
    case = EvaluationCase(id="e-1", project_fixture="fixture.json", question="why failed?")
    assert run.token_budget == 8000
    assert span.status == "ok"
    assert case.expected_findings == []


def test_tool_registry_rejects_unknown_tools_extra_arguments_and_unapproved_effects():
    registry = ToolRegistry()
    registry.register(RegisteredTool(
        name="echo", description="double a number", input_model=EchoInput,
        output_model=EchoOutput, handler=lambda value: {"doubled": value.value * 2},
    ))
    assert registry.invoke("echo", {"value": 3}).doubled == 6
    with pytest.raises(ValueError, match="unregistered"):
        registry.invoke("missing", {})
    with pytest.raises(ValueError, match="unexpected arguments"):
        registry.invoke("echo", {"value": 3, "hidden": True})
    with pytest.raises(ValueError, match="must require approval"):
        registry.register(RegisteredTool(
            name="write", description="write", input_model=EchoInput,
            output_model=EchoOutput, handler=lambda value: {"doubled": value.value},
            read_only=False, has_external_side_effects=True,
        ))


def test_mock_model_gateway_is_deterministic_and_fails_when_exhausted():
    gateway = MockModelGateway([{"content": "ok", "input_tokens": 4, "output_tokens": 1}])
    request = ModelRequest(messages=[{"role": "user", "content": "hello"}])
    assert gateway.complete(request).content == "ok"
    assert gateway.requests == [request]
    with pytest.raises(RuntimeError, match="exhausted"):
        gateway.complete(request)


def test_evidence_validator_accepts_real_refs_and_rejects_fabricated_refs():
    validator = EvidenceValidator(
        pd.DataFrame([{"run_id": "r1"}]),
        pd.DataFrame([{"run_id": "r1", "key": "accuracy", "value": 0.9}]),
        pd.DataFrame([{"run_id": "r1", "key": "batch_size", "value": "32"}]),
        [{"source": "r1.log", "line": 2, "text": "ok"}],
    )
    from experimentlens.domain import EvidenceRef

    validator.validate_ref(EvidenceRef(id="r1:accuracy", kind="metric", label="accuracy"))
    with pytest.raises(InvalidEvidenceError, match="invalid evidence"):
        validator.validate_ref(EvidenceRef(id="r2:accuracy", kind="metric", label="invented"))
