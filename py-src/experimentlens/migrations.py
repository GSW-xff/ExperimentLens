from __future__ import annotations

from copy import deepcopy
from typing import Any

from .domain import MetricDefinition, MetricDirection, MetricRole, utc_now

CURRENT_SCHEMA_VERSION = 2


def migrate_project_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Return a V2 payload and a manifest without mutating the input."""
    version = int(payload.get("schema_version", 1))
    if version == CURRENT_SCHEMA_VERSION:
        return deepcopy(payload), None
    if version != 1:
        raise ValueError(f"unsupported project schema version: {version}")

    migrated = deepcopy(payload)
    mapping = migrated.get("mapping")
    metric_definitions: list[dict[str, Any]] = []
    if mapping:
        primary = mapping["primary_metric"]
        keys = list(dict.fromkeys([primary, *mapping.get("metric_columns", [])]))
        for key in keys:
            definition = MetricDefinition(
                key=key,
                display_name=key,
                role=MetricRole.PRIMARY if key == primary else MetricRole.SECONDARY,
                direction=(
                    MetricDirection(mapping.get("metric_direction", "maximize"))
                    if key == primary
                    else MetricDirection.MAXIMIZE
                ),
            ).model_dump(mode="json")
            metric_definitions.append(definition)
        mapping["metric_definitions"] = metric_definitions

    migrated.update({
        "schema_version": CURRENT_SCHEMA_VERSION,
        "experiment_type": migrated.get("experiment_type", "general"),
        "domain_tags": migrated.get("domain_tags", []),
        "owner_id": migrated.get("owner_id"),
        "metric_definitions": metric_definitions,
    })
    manifest = {
        "from_version": 1,
        "to_version": CURRENT_SCHEMA_VERSION,
        "migrated_at": utc_now(),
        "project_id": migrated.get("id"),
    }
    return migrated, manifest
