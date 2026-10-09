from __future__ import annotations

import argparse
import os
import socket
import threading
import uuid
from collections.abc import Callable
from pathlib import Path

from ..domain import AgentRunStatus
from ..observability import PlatformMetrics
from ..persistence import Database, SQLAgentRunRepository
from ..repositories.local import LocalRepository
from .model_gateway import ModelGateway
from .orchestrator import AgentOrchestrator


class AgentWorker:
    """Database-backed worker with expiring leases and fencing-token heartbeats."""

    def __init__(
        self,
        database: Database,
        workspace: LocalRepository,
        *,
        owner: str | None = None,
        lease_seconds: float = 15.0,
        poll_seconds: float = 0.25,
        gateway: ModelGateway | None = None,
        metrics: PlatformMetrics | None = None,
        fault_hook: Callable | None = None,
    ) -> None:
        self.database = database
        self.repository = SQLAgentRunRepository(database)
        self.workspace = workspace
        self.owner = owner or (
            f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"
        )
        self.lease_seconds = lease_seconds
        self.poll_seconds = poll_seconds
        self.orchestrator = AgentOrchestrator(
            workspace,
            gateway,
            repository=self.repository,
            metrics=metrics,
            auto_execute=False,
            fault_hook=fault_hook,
        )

    def run_once(self) -> str | None:
        claimed = self.repository.claim_next(self.owner, self.lease_seconds)
        return self._execute_claim(claimed)

    def process_run(self, agent_run_id: str) -> str | None:
        """Claim a specific run, used by the isolated evaluation harness."""
        claimed = self.repository.claim_run(agent_run_id, self.owner, self.lease_seconds)
        return self._execute_claim(claimed)

    def _execute_claim(self, claimed) -> str | None:
        if claimed is None:
            return None
        run, fencing_token = claimed
        existing_steps = self.repository.list_steps(run.id)
        if run.status == AgentRunStatus.RUNNING or existing_steps:
            self.repository.append_event(run.id, "agent.recovered", {
                "worker": self.owner,
                "fencing_token": fencing_token,
                "completed_steps": sum(
                    step.status.value == "completed" for step in existing_steps
                ),
            })
        stopped = threading.Event()
        heartbeat = threading.Thread(
            target=self._heartbeat_loop,
            args=(run.id, fencing_token, stopped),
            name=f"lease-heartbeat-{run.id}",
            daemon=True,
        )
        heartbeat.start()
        try:
            self.orchestrator.execute_claimed(
                run.id,
                lease_guard=lambda: self.repository.owns_lease(
                    run.id, self.owner, fencing_token
                ),
            )
        finally:
            stopped.set()
            heartbeat.join(timeout=max(1.0, self.lease_seconds))
        self.repository.release_claim(run.id, self.owner, fencing_token)
        return run.id

    def run_forever(self, stop_event: threading.Event | None = None) -> None:
        stop = stop_event or threading.Event()
        while not stop.is_set():
            processed = self.run_once()
            if processed is None:
                stop.wait(self.poll_seconds)

    def _heartbeat_loop(
        self, agent_run_id: str, fencing_token: int, stopped: threading.Event
    ) -> None:
        interval = max(0.01, self.lease_seconds / 3)
        while not stopped.wait(interval):
            if not self.repository.heartbeat(
                agent_run_id, self.owner, fencing_token, self.lease_seconds
            ):
                return


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the ExperimentLens Agent worker")
    parser.add_argument("--once", action="store_true", help="Process at most one queued run")
    parser.add_argument("--lease-seconds", type=float, default=15.0)
    parser.add_argument("--poll-seconds", type=float, default=0.25)
    args = parser.parse_args()
    database = Database()
    if database.url.startswith("sqlite"):
        database.create_schema()
    workspace = LocalRepository(Path(os.environ.get(
        "EXPERIMENTLENS_WORKSPACE", ".experimentlens/workspace"
    )))
    worker = AgentWorker(
        database,
        workspace,
        lease_seconds=args.lease_seconds,
        poll_seconds=args.poll_seconds,
    )
    if args.once:
        worker.run_once()
    else:
        worker.run_forever()


if __name__ == "__main__":
    main()
