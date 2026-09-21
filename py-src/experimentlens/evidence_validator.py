from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pandas as pd

from .domain import EvidenceRef, Finding, Hypothesis


class InvalidEvidenceError(ValueError):
    """Raised when an analysis cites evidence that is absent from normalized data."""


class EvidenceValidator:
    def __init__(
        self,
        runs: pd.DataFrame,
        metrics: pd.DataFrame,
        params: pd.DataFrame,
        logs: list[dict[str, Any]],
    ) -> None:
        run_ids = set(runs.get("run_id", pd.Series(dtype=str)).astype(str))
        self.valid_ids: dict[str, set[str]] = {
            "run": run_ids,
            "metric": {
                f"{row.run_id}:{row.key}" for row in metrics.itertuples()
            },
            "param": {
                f"{row.run_id}:{row.key}" for row in params.itertuples()
            },
            "log": {
                f"{record.get('source', 'log')}:{record.get('line', '?')}" for record in logs
            },
        }

    def validate_ref(self, ref: EvidenceRef) -> None:
        if ref.kind not in self.valid_ids:
            raise InvalidEvidenceError(f"unsupported evidence kind: {ref.kind}")
        if ref.id not in self.valid_ids[ref.kind]:
            raise InvalidEvidenceError(f"invalid evidence reference: {ref.kind}:{ref.id}")

    def validate_analysis(
        self,
        findings: Iterable[Finding],
        hypotheses: Iterable[Hypothesis],
    ) -> None:
        for finding in findings:
            for ref in finding.evidence_refs:
                self.validate_ref(ref)
        for hypothesis in hypotheses:
            for ref in [*hypothesis.supporting_evidence, *hypothesis.contradicting_evidence]:
                self.validate_ref(ref)
