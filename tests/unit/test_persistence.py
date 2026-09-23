import json

from alembic import command
from alembic.config import Config
from experimentlens.domain import AgentRun, TraceSpan
from experimentlens.persistence import Database, SQLAgentRunRepository
from experimentlens.persistence.models import (
    AgentEventRecord,
    OrganizationRecord,
    OutboxRecord,
    ToolCallRecord,
)
from sqlalchemy import func, inspect, select


def test_sql_repository_persists_events_outbox_tools_and_trace(tmp_path):
    database = Database(f"sqlite:///{tmp_path / 'control.db'}")
    database.create_schema()
    repository = SQLAgentRunRepository(database)
    run = AgentRun(id="ar-test", project_id="project-test", question="diagnose", trace_id="tr-test")

    repository.create(run)
    first = repository.append_event(run.id, "agent.created", {"value": 1})
    second = repository.append_event(run.id, "agent.started", {"value": 2})
    call = {
        "id": "tc-test",
        "agent_run_id": run.id,
        "tool_name": "list_runs",
        "status": "completed",
    }
    repository.append_tool_call(run.id, call)
    repository.append_tool_call(run.id, call)
    repository.save_span(TraceSpan(
        id="span-test",
        trace_id="tr-test",
        name="agent.run",
        project_id=run.project_id,
        agent_run_id=run.id,
    ))

    assert (first.id, second.id) == (1, 2)
    assert [item.type for item in repository.list_events(run.id)] == [
        "agent.created", "agent.started"
    ]
    assert repository.list_spans("tr-test")[0].name == "agent.run"
    with database.session() as session:
        assert session.get(OrganizationRecord, "org_local") is not None
        assert session.scalar(select(func.count(AgentEventRecord.id))) == 2
        assert session.scalar(select(func.count(OutboxRecord.id))) == 2
        assert session.scalar(select(func.count(ToolCallRecord.id))) == 1
        outbox = session.scalar(select(OutboxRecord).order_by(OutboxRecord.sequence))
        assert json.loads(outbox.payload)["type"] == "agent.created"


def test_database_readiness_requires_migrated_schema(tmp_path):
    database = Database(f"sqlite:///{tmp_path / 'readiness.db'}")
    assert database.ready() is False
    database.create_schema()
    assert database.ready() is True


def test_alembic_schema_migrates_forward_and_back(tmp_path):
    repository_root = __import__("pathlib").Path(__file__).parents[2]
    config = Config(str(repository_root / "alembic.ini"))
    database_path = tmp_path / "migration.db"
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")

    command.upgrade(config, "head")
    tables = set(inspect(Database(f"sqlite:///{database_path}").engine).get_table_names())
    assert {"agent_runs", "agent_events", "outbox_events", "trace_spans"} <= tables

    command.downgrade(config, "base")
    remaining = set(inspect(Database(f"sqlite:///{database_path}").engine).get_table_names())
    assert not ({"agent_runs", "agent_events", "outbox_events", "trace_spans"} & remaining)
