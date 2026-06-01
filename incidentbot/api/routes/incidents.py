from datetime import datetime, timedelta, UTC
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi import status as http_status
from pydantic import BaseModel
from sqlalchemy import func
from sqlmodel import select, Session

from incidentbot.configuration.settings import settings
from incidentbot.models.database import engine, IncidentParticipant, IncidentRecord

router = APIRouter(prefix="/api/v1", tags=["Incidents"])


# ── Auth ──────────────────────────────────────────────────────────────────────


def _api_key_check(x_api_key: Annotated[str | None, Header()] = None) -> None:
    key = settings.API_KEY
    if key and x_api_key != key:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing X-Api-Key header",
        )


# ── Response models ───────────────────────────────────────────────────────────


class ParticipantResponse(BaseModel):
    role: str
    user_id: str
    user_name: str
    is_lead: bool


class IncidentResponse(BaseModel):
    id: int
    slug: str | None
    description: str | None
    severity: str | None
    status: str | None
    components: str | None
    impact: str | None
    is_security_incident: bool | None
    channel_id: str | None
    channel_name: str | None
    link: str | None
    meeting_link: str | None
    created_at: datetime
    updated_at: datetime | None
    participants: list[ParticipantResponse] = []


class IncidentListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    incidents: list[IncidentResponse]


class MetricsResponse(BaseModel):
    total: int
    open: int
    by_severity: dict[str, int]
    by_status: dict[str, int]
    mttr_hours: float | None
    last_7_days: int
    last_30_days: int


# ── Helpers ───────────────────────────────────────────────────────────────────


def _final_statuses() -> list[str]:
    return [s for s, cfg in settings.statuses.items() if cfg.final]


def _to_response(incident: IncidentRecord, session: Session) -> IncidentResponse:
    participants = session.exec(
        select(IncidentParticipant).where(IncidentParticipant.parent == incident.id)
    ).all()
    return IncidentResponse(
        id=incident.id,
        slug=incident.slug,
        description=incident.description,
        severity=incident.severity,
        status=incident.status,
        components=incident.components,
        impact=incident.impact,
        is_security_incident=incident.is_security_incident,
        channel_id=incident.channel_id,
        channel_name=incident.channel_name,
        link=incident.link,
        meeting_link=incident.meeting_link,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
        participants=[
            ParticipantResponse(
                role=p.role,
                user_id=p.user_id,
                user_name=p.user_name,
                is_lead=p.is_lead,
            )
            for p in participants
        ],
    )


# ── Routes ────────────────────────────────────────────────────────────────────


@router.get("/incidents")
def list_incidents(
    status: str | None = Query(default=None, description="Filter by status"),
    severity: str | None = Query(default=None, description="Filter by severity"),
    limit: int = Query(default=50, ge=1, le=500, description="Page size"),
    offset: int = Query(default=0, ge=0, description="Page offset"),
    _: None = Depends(_api_key_check),
) -> IncidentListResponse:
    with Session(engine) as session:
        count_stmt = select(func.count(IncidentRecord.id))
        data_stmt = select(IncidentRecord)
        if status:
            count_stmt = count_stmt.where(IncidentRecord.status == status)
            data_stmt = data_stmt.where(IncidentRecord.status == status)
        if severity:
            count_stmt = count_stmt.where(IncidentRecord.severity == severity)
            data_stmt = data_stmt.where(IncidentRecord.severity == severity)

        total: int = session.execute(count_stmt).scalar_one()
        incidents = session.exec(
            data_stmt.order_by(IncidentRecord.created_at.desc()).offset(offset).limit(limit)
        ).all()

        return IncidentListResponse(
            total=total,
            limit=limit,
            offset=offset,
            incidents=[_to_response(i, session) for i in incidents],
        )


@router.get("/incidents/{incident_id}")
def get_incident(
    incident_id: int,
    _: None = Depends(_api_key_check),
) -> IncidentResponse:
    with Session(engine) as session:
        incident = session.get(IncidentRecord, incident_id)
        if not incident:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Incident {incident_id} not found",
            )
        return _to_response(incident, session)


@router.get("/metrics")
def get_metrics(_: None = Depends(_api_key_check)) -> MetricsResponse:
    final = _final_statuses()
    now = datetime.now(tz=UTC)

    with Session(engine) as session:
        total: int = session.execute(
            select(func.count(IncidentRecord.id))
        ).scalar_one()

        open_stmt = select(func.count(IncidentRecord.id))
        if final:
            open_stmt = open_stmt.where(IncidentRecord.status.not_in(final))
        open_count: int = session.execute(open_stmt).scalar_one()

        severity_rows = session.execute(
            select(IncidentRecord.severity, func.count(IncidentRecord.id))
            .group_by(IncidentRecord.severity)
        ).all()
        by_severity = {(row[0] or "unknown"): row[1] for row in severity_rows}

        status_rows = session.execute(
            select(IncidentRecord.status, func.count(IncidentRecord.id))
            .group_by(IncidentRecord.status)
        ).all()
        by_status = {(row[0] or "unknown"): row[1] for row in status_rows}

        # MTTR: average seconds from created_at to updated_at for resolved incidents.
        # Uses updated_at as a proxy for resolution time (last write to a resolved
        # record is the resolution event in the normal workflow).
        mttr_hours: float | None = None
        if final:
            avg_seconds = session.execute(
                select(
                    func.avg(
                        func.extract(
                            "epoch",
                            IncidentRecord.updated_at - IncidentRecord.created_at,
                        )
                    )
                ).where(
                    IncidentRecord.status.in_(final),
                    IncidentRecord.updated_at.is_not(None),
                )
            ).scalar()
            if avg_seconds is not None:
                mttr_hours = round(float(avg_seconds) / 3600, 2)

        last_7: int = session.execute(
            select(func.count(IncidentRecord.id)).where(
                IncidentRecord.created_at >= now - timedelta(days=7)
            )
        ).scalar_one()

        last_30: int = session.execute(
            select(func.count(IncidentRecord.id)).where(
                IncidentRecord.created_at >= now - timedelta(days=30)
            )
        ).scalar_one()

    return MetricsResponse(
        total=total,
        open=open_count,
        by_severity=by_severity,
        by_status=by_status,
        mttr_hours=mttr_hours,
        last_7_days=last_7,
        last_30_days=last_30,
    )
