from __future__ import annotations

import hashlib
import json
import os
import re
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest

from .domain import AgentRun, SpanStatus, TraceSpan, utc_now

_SECRET_PATTERNS = (
    re.compile(r"(?i)(bearer\s+)[a-z0-9._~+/-]+"),
    re.compile(r"(?i)(api[_-]?key[=:]\s*)[^\s,;]+"),
    re.compile(r"(?i)(password[=:]\s*)[^\s,;]+"),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
)


def redact(value: str) -> str:
    result = value
    for pattern in _SECRET_PATTERNS:
        result = pattern.sub(lambda match: f"{match.group(1) if match.lastindex else ''}[REDACTED]", result)
    return result


def digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


class PlatformMetrics:
    """Low-cardinality metrics. IDs are intentionally never used as labels."""

    def __init__(self) -> None:
        self.registry = CollectorRegistry(auto_describe=True)
        self.http_requests = Counter(
            "http_requests_total", "HTTP requests", ("method", "route", "status"), registry=self.registry
        )
        self.http_duration = Histogram(
            "http_request_duration_seconds", "HTTP request duration", ("method", "route"), registry=self.registry
        )
        self.agent_runs = Counter(
            "agent_runs_total", "Agent runs", ("status",), registry=self.registry
        )
        self.agent_duration = Histogram(
            "agent_run_duration_seconds", "Agent run duration", registry=self.registry
        )
        self.agent_active = Gauge("agent_active_runs", "Active agent runs", registry=self.registry)
        self.model_requests = Counter(
            "model_requests_total", "Model requests", ("provider", "model", "status"), registry=self.registry
        )
        self.model_duration = Histogram(
            "model_request_duration_seconds", "Model request duration", ("provider", "model"), registry=self.registry
        )
        self.model_tokens = Counter(
            "model_tokens_total", "Model tokens", ("provider", "model", "type"), registry=self.registry
        )
        self.tool_calls = Counter(
            "tool_calls_total", "Tool calls", ("tool", "status"), registry=self.registry
        )
        self.tool_duration = Histogram(
            "tool_call_duration_seconds", "Tool call duration", ("tool",), registry=self.registry
        )
        self.evidence_failures = Counter(
            "evidence_validation_failures_total", "Invalid evidence references", registry=self.registry
        )
        self.sse_connections = Gauge("sse_connections", "Current SSE connections", registry=self.registry)
        self.sse_reconnects = Counter("sse_reconnects_total", "SSE reconnects", registry=self.registry)

    def render(self) -> bytes:
        return generate_latest(self.registry)


class TraceRecorder:
    def __init__(self, repository: Any) -> None:
        self.repository = repository
        if not isinstance(trace.get_tracer_provider(), TracerProvider):
            provider = TracerProvider(resource=Resource.create({
                "service.name": "experimentlens-control-plane",
                "service.version": "2.0.0",
            }))
            endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
            if endpoint:
                provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(
                    endpoint=endpoint,
                    insecure=os.environ.get("OTEL_EXPORTER_OTLP_INSECURE", "true") == "true",
                )))
            trace.set_tracer_provider(provider)
        self.otel = trace.get_tracer("experimentlens.agent", "2.0")

    @contextmanager
    def span(
        self,
        name: str,
        run: AgentRun,
        *,
        parent_span_id: str | None = None,
        input_value: Any = None,
        attributes: dict[str, Any] | None = None,
    ) -> Iterator[TraceSpan]:
        started = time.perf_counter()
        record = TraceSpan(
            id=f"span_{uuid.uuid4().hex[:16]}",
            trace_id=run.trace_id or f"trace_{uuid.uuid4().hex}",
            parent_span_id=parent_span_id,
            name=name,
            organization_id=run.organization_id,
            project_id=run.project_id,
            agent_run_id=run.id,
            input_digest=digest(input_value) if input_value is not None else None,
            attributes=attributes or {},
        )
        try:
            with self.otel.start_as_current_span(name) as otel_span:
                for key, value in record.attributes.items():
                    if isinstance(value, (str, bool, int, float)):
                        otel_span.set_attribute(key, value)
                yield record
        except Exception as error:
            record.status = SpanStatus.ERROR
            record.error_category = type(error).__name__
            raise
        finally:
            record.ended_at = utc_now()
            record.duration_ms = (time.perf_counter() - started) * 1000
            save_span = getattr(self.repository, "save_span", None)
            if save_span:
                save_span(record)
