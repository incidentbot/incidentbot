"""
Prometheus metrics for incidentbot.

A scrape-time custom collector that queries the incident database on every
GET /metrics scrape and exposes gauges for open/closed incident counts,
per-incident open duration, and mean time to resolution (MTTR). The database
is the source of truth, so the metrics are always accurate and survive
restarts (no in-process counters to lose).

Exposed metrics:
  incidentbot_open_incidents{component,severity,status}   open incidents
  incidentbot_incidents_total{status,severity}            all incidents by status
  incidentbot_resolved_incidents{component,severity}      resolved incidents
  incidentbot_incident_open_seconds{slug,severity,components}
                                                          age of each open incident
  incidentbot_mttr_seconds{component}                     mean resolution time per component
  incidentbot_mttr_seconds_overall                        mean resolution time overall

Incidents with multiple components (the multi-select stores them as a
comma-separated string) are counted once per component.
"""

import datetime

import structlog
from prometheus_client import CollectorRegistry
from prometheus_client.core import GaugeMetricFamily

from incidentbot.configuration.settings import settings
from incidentbot.models.incident import IncidentDatabaseInterface

logger = structlog.get_logger(__name__)


def _final_statuses() -> set[str]:
    return {name for name, cfg in (settings.statuses or {}).items() if cfg.final}


def _components_of(incident) -> list[str]:
    """Split the comma-separated components string into a clean list."""
    raw = (incident.components or "").strip()
    if not raw:
        return ["unknown"]
    parts = [c.strip() for c in raw.split(",") if c.strip()]
    return parts or ["unknown"]


def _resolution_seconds(incident) -> float | None:
    """
    Time from creation to resolution. Prefers resolved_at; falls back to
    updated_at for incidents resolved before resolved_at was introduced.
    """
    if not incident.created_at:
        return None
    end = incident.resolved_at or incident.updated_at
    if not end:
        return None
    delta = (end - incident.created_at).total_seconds()
    return delta if delta >= 0 else None


class IncidentMetricsCollector:
    """Custom Prometheus collector backed by the incident database."""

    def collect(self):
        try:
            incidents = IncidentDatabaseInterface.list_all()
        except Exception as error:
            logger.exception("metrics: failed to list incidents", error=error)
            incidents = []

        final = _final_statuses()
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

        open_incidents = GaugeMetricFamily(
            "incidentbot_open_incidents",
            "Number of open (non-final-status) incidents.",
            labels=["component", "severity", "status"],
        )
        total_incidents = GaugeMetricFamily(
            "incidentbot_incidents_total",
            "Total number of incidents by status and severity.",
            labels=["status", "severity"],
        )
        resolved_incidents = GaugeMetricFamily(
            "incidentbot_resolved_incidents",
            "Number of resolved (final-status) incidents by component and severity.",
            labels=["component", "severity"],
        )
        open_seconds = GaugeMetricFamily(
            "incidentbot_incident_open_seconds",
            "Seconds each open incident has been open (now - created_at).",
            labels=["slug", "severity", "components"],
        )
        mttr_component = GaugeMetricFamily(
            "incidentbot_mttr_seconds",
            "Mean time to resolution in seconds, by component.",
            labels=["component"],
        )
        mttr_overall = GaugeMetricFamily(
            "incidentbot_mttr_seconds_overall",
            "Mean time to resolution in seconds across all resolved incidents.",
            labels=[],
        )

        open_counts: dict[tuple, int] = {}
        total_counts: dict[tuple, int] = {}
        resolved_counts: dict[tuple, int] = {}
        mttr_by_component: dict[str, list[float]] = {}
        mttr_all: list[float] = []

        for inc in incidents:
            status = inc.status or "unknown"
            severity = inc.severity or "unknown"
            components = _components_of(inc)

            total_counts[(status, severity)] = (
                total_counts.get((status, severity), 0) + 1
            )

            if status in final:
                duration = _resolution_seconds(inc)
                for component in components:
                    resolved_counts[(component, severity)] = (
                        resolved_counts.get((component, severity), 0) + 1
                    )
                    if duration is not None:
                        mttr_by_component.setdefault(component, []).append(duration)
                if duration is not None:
                    mttr_all.append(duration)
            else:
                for component in components:
                    key = (component, severity, status)
                    open_counts[key] = open_counts.get(key, 0) + 1
                if inc.created_at:
                    age = (now - inc.created_at).total_seconds()
                    if age >= 0:
                        open_seconds.add_metric(
                            [
                                inc.slug or str(inc.id),
                                severity,
                                inc.components or "unknown",
                            ],
                            age,
                        )

        for (component, severity, status), count in open_counts.items():
            open_incidents.add_metric([component, severity, status], count)
        for (status, severity), count in total_counts.items():
            total_incidents.add_metric([status, severity], count)
        for (component, severity), count in resolved_counts.items():
            resolved_incidents.add_metric([component, severity], count)
        for component, durations in mttr_by_component.items():
            if durations:
                mttr_component.add_metric(
                    [component], sum(durations) / len(durations)
                )
        if mttr_all:
            mttr_overall.add_metric([], sum(mttr_all) / len(mttr_all))

        yield open_incidents
        yield total_incidents
        yield resolved_incidents
        yield open_seconds
        yield mttr_component
        yield mttr_overall


# Dedicated registry so the endpoint exposes only incident metrics (not the
# default process/GC collectors).
REGISTRY = CollectorRegistry()
REGISTRY.register(IncidentMetricsCollector())
