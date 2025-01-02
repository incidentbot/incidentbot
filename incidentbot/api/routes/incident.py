import asyncio
import base64

from fastapi import APIRouter, Depends, HTTPException, Response, status
from incidentbot.api.deps import get_current_active_superuser, SessionDep
from incidentbot.incident.actions import (
    set_description,
    set_severity,
    set_status,
)
from incidentbot.incident.core import Incident, IncidentRequestParameters
from incidentbot.incident.event import EventLogHandler
from incidentbot.models.database import (
    ApplicationData,
    IncidentEvent,
    IncidentEventBase,
    IncidentParticipant,
    IncidentRecord,
    JiraIssueRecord,
    OpsgenieIncidentRecord,
    PagerDutyIncidentRecord,
    PostmortemRecord,
    StatuspageIncidentRecord,
)
from incidentbot.models.response import SuccessResponse
from pydantic import BaseModel
from sqlalchemy.exc import NoResultFound
from sqlmodel import col, select
from typing import Any

router = APIRouter()


class Incidents(BaseModel):
    data: list[IncidentRecord]
    count: int


"""
/incident
"""


@router.get(
    "/incident",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=status.HTTP_200_OK,
)
async def get_incidents(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    filter: str = None,
) -> Incidents:
    try:
        if filter:
            incidents = session.exec(
                select(IncidentRecord)
                .where(col(IncidentRecord.description).contains(filter))
                .order_by(IncidentRecord.slug)
            ).all()

            return Incidents(data=incidents, count=len(incidents))

        incidents = session.exec(
            select(IncidentRecord).offset(skip).limit(limit).order_by("id")
        ).all()

        return Incidents(data=incidents, count=len(incidents))
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.get(
    "/incident/{slug}",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=status.HTTP_200_OK,
)
async def get_incident(session: SessionDep, slug: str) -> IncidentRecord:
    try:
        incident = session.exec(
            select(IncidentRecord).filter(IncidentRecord.slug == slug)
        ).one()

        return incident
    except NoResultFound:
        raise HTTPException(status_code=404, detail="incident not found")
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


# Artifacts


@router.get(
    "/incident/{slug}/jira",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=status.HTTP_200_OK,
)
async def get_incident_jira_issues(
    session: SessionDep, slug: str
) -> list[JiraIssueRecord]:
    try:
        incident = session.exec(
            select(IncidentRecord).filter(IncidentRecord.slug == slug)
        ).one()

        records = session.exec(
            select(JiraIssueRecord).filter(
                JiraIssueRecord.parent == incident.id
            )
        ).all()

        return records
    except NoResultFound:
        raise HTTPException(status_code=404, detail="incident not found")
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.get(
    "/incident/{slug}/opsgenie",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=status.HTTP_200_OK,
)
async def get_incident_opsgenie(
    session: SessionDep, slug: str
) -> list[OpsgenieIncidentRecord]:
    try:
        incident = session.exec(
            select(IncidentRecord).filter(IncidentRecord.slug == slug)
        ).one()

        records = session.exec(
            select(OpsgenieIncidentRecord).filter(
                OpsgenieIncidentRecord.parent == incident.id
            )
        ).all()

        return records
    except NoResultFound:
        raise HTTPException(status_code=404, detail="incident not found")
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.get(
    "/incident/{slug}/pagerduty",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=status.HTTP_200_OK,
)
async def get_incident_pagerduty(
    session: SessionDep, slug: str
) -> list[PagerDutyIncidentRecord]:
    try:
        incident = session.exec(
            select(IncidentRecord).filter(IncidentRecord.slug == slug)
        ).one()

        records = session.exec(
            select(PagerDutyIncidentRecord).filter(
                PagerDutyIncidentRecord.parent == incident.id
            )
        ).all()

        return records
    except NoResultFound:
        raise HTTPException(status_code=404, detail="incident not found")
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.get(
    "/incident/{slug}/postmortem",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=status.HTTP_200_OK,
)
async def get_incident_postmortems(
    session: SessionDep, slug: str
) -> list[PostmortemRecord]:
    try:
        incident = session.exec(
            select(IncidentRecord).filter(IncidentRecord.slug == slug)
        ).one()

        records = session.exec(
            select(PostmortemRecord).filter(
                PostmortemRecord.parent == incident.id
            )
        ).all()

        return records
    except NoResultFound:
        raise HTTPException(status_code=404, detail="incident not found")
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.get(
    "/incident/{slug}/statuspage",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=status.HTTP_200_OK,
)
async def get_incident_statuspage(
    session: SessionDep, slug: str
) -> list[StatuspageIncidentRecord]:
    try:
        incident = session.exec(
            select(IncidentRecord).filter(IncidentRecord.slug == slug)
        ).one()

        records = session.exec(
            select(StatuspageIncidentRecord).filter(
                StatuspageIncidentRecord.parent == incident.id
            )
        ).all()

        return records
    except NoResultFound:
        raise HTTPException(status_code=404, detail="incident not found")
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


# Participants


@router.get(
    "/incident/{slug}/participants",
    # dependencies=[Depends(get_current_active_superuser)],
    status_code=status.HTTP_200_OK,
)
async def get_incident_participants(
    session: SessionDep, slug: str
) -> list[IncidentParticipant]:
    try:
        incident = session.exec(
            select(IncidentRecord).filter(IncidentRecord.slug == slug)
        ).one()

        records = session.exec(
            select(IncidentParticipant).filter(
                IncidentParticipant.parent == incident.id
            )
        ).all()

        return records
    except NoResultFound:
        raise HTTPException(status_code=404, detail="incident not found")
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


# Create an incident


@router.post(
    "/incident",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=status.HTTP_200_OK,
)
async def post_incident(request: IncidentRecord):
    try:
        incident = Incident(
            params=IncidentRequestParameters(
                channel="web",
                created_from_web=True,
                description=request.description,
                is_security_incident=request.is_security_incident,
                private_channel=False,
                severity=request.severity,
                user="api",
            )
        )

        incident.start()

        return SuccessResponse(result="success", message="incident created")
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


# Delete an incident


@router.delete(
    "/incident/{id}",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=status.HTTP_200_OK,
)
async def delete_incident(
    id: str,
) -> SuccessResponse:
    try:
        Incident().delete(id)

        return SuccessResponse(result="success", message="incident deleted")
    except NoResultFound:
        raise HTTPException(status_code=404, detail="incident not found")
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


# Edit an incident


@router.patch(
    "/incident/{field}",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=status.HTTP_200_OK,
)
def patch_incident(incident: IncidentRecord, field: str):
    """
    Field is the value being changed: severity, status
    The incident value sent over from the frontend is the IncidentRecord with updated fields
    In this case, the API accepts the record and parses whatever field was changed and references
    its value to pass to the methods that handle the changes
    """

    match field:
        case "description":
            asyncio.run(
                set_description(
                    channel_id=incident.channel_id,
                    description=incident.description,
                )
            )

        case "severity":
            asyncio.run(
                set_severity(
                    channel_id=incident.channel_id,
                    severity=incident.severity,
                    user="api",
                )
            )
        case "status":
            asyncio.run(
                set_status(
                    channel_id=incident.channel_id,
                    status=incident.status,
                    user="api",
                )
            )


"""
/incident/:slug/events
"""


@router.get(
    "/incident/{slug}/events",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=status.HTTP_200_OK,
)
def get_incident_events(
    slug: str,
) -> list[IncidentEventBase]:
    """
    Return events excluding the image field

    If there is an image present, an additional request will have to be made
    against the following endpoint to get the iamge specifically
    """
    try:
        records = EventLogHandler.read(incident_slug=slug)

        return [
            IncidentEventBase(
                created_at=record.created_at,
                id=record.id,
                incident_slug=record.incident_slug,
                message_ts=record.message_ts,
                mimetype=record.mimetype,
                parent=record.parent,
                source=record.source,
                text=record.text,
                timestamp=record.timestamp,
                title=record.title,
                updated_at=record.updated_at,
                user=record.user,
            )
            for record in records
        ]
    except NoResultFound:
        raise HTTPException(status_code=404, detail="incident not found")
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.get(
    "/incident/{slug}/events/image/{id}",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=status.HTTP_200_OK,
    response_model=None,
)
def get_incident_event_image(
    slug: str,
    id: str,
):
    """
    Returns only the image content and mimetype when an event contains an image
    """

    try:
        event = EventLogHandler.read_one(id=id, incident_slug=slug)

        return Response(
            content=base64.b64encode(event.image).decode("utf-8"),
            media_type=event.mimetype,
        )
    except NoResultFound:
        raise HTTPException(status_code=404, detail="incident not found")
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.delete(
    "/incident/{slug}/events/{id}",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=status.HTTP_200_OK,
)
def delete_incident_event(
    id: str,
) -> SuccessResponse:
    try:
        EventLogHandler.delete(id=id)

        return SuccessResponse(result="success", message="item deleted")
    except NoResultFound:
        raise HTTPException(status_code=404, detail="incident not found")
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.patch(
    "/incident/{slug}/events/{id}",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=status.HTTP_200_OK,
)
def patch_incident_event(
    request: IncidentEvent,
) -> SuccessResponse:
    try:
        EventLogHandler.update(request)

        return SuccessResponse(result="success", message="item updated")
    except NoResultFound:
        raise HTTPException(status_code=404, detail="incident not found")
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


"""
/incident/config/:parameter
"""


class ConfigurationResponse(BaseModel):
    data: list[Any]


@router.get(
    "/incident/config/{parameter}",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=status.HTTP_200_OK,
)
async def get_incident_config(
    session: SessionDep, parameter: str
) -> ConfigurationResponse:
    try:
        match parameter:
            case "users":
                record = session.exec(
                    select(ApplicationData).filter(
                        ApplicationData.name == "slack_users"
                    )
                ).one()

                return ConfigurationResponse(data=record.json_data)
            case _:
                raise HTTPException(status_code=404, detail="not found")
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))
