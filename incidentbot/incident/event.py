from datetime import datetime

from incidentbot.logging import logger
from incidentbot.models.database import engine, IncidentEvent
from incidentbot.slack.client import get_slack_user
from sqlmodel import Session, select, or_


class EventLogHandler:
    @classmethod
    def create(
        self,
        incident_id: int,
        incident_slug: str,
        source: str,
        event: str | None = None,
        image: bytes | None = None,
        message_ts: str | None = None,
        mimetype: str | None = None,
        title: str | None = None,
        timestamp: datetime | None = None,
        user: str | None = None,
    ):
        """
        Create an event log for an incident
        """

        with Session(engine) as session:
            try:
                event = IncidentEvent(
                    image=image,
                    incident_slug=incident_slug,
                    message_ts=message_ts,
                    mimetype=mimetype,
                    parent=incident_id,
                    source=source,
                    text=event,
                    timestamp=timestamp,
                    title=title,
                    user=(
                        get_slack_user(user)["real_name"]
                        if user != ""
                        else None
                    ),
                )

                session.add(event)
                session.commit()
            except Exception as error:
                logger.error(
                    f"Event log creation failed for incident {incident_id}: {error}"
                )

    @classmethod
    def delete(
        self,
        id: str,
    ):
        """
        Delete from an incident's audit logs

        Parameters:
            id (str): The event's uuid
        """

        with Session(engine) as session:
            try:
                record = session.exec(
                    select(IncidentEvent).filter(IncidentEvent.id == id)
                ).one()

                session.delete(record)
                session.commit()

                logger.info(f"deleted incident event {id}")
            except Exception as error:
                logger.error(
                    f"Event log delete failed for record {id}: {error}"
                )

                return False, error

    @classmethod
    def read(
        self,
        incident_id: id = None,
        incident_slug: str = None,
    ) -> list[IncidentEvent]:
        """
        Read an incident's event logs

        Parameters:
            incident_id (int): The incident id
            incident_slug (str): The incident slug
        """

        with Session(engine) as session:
            try:
                records = session.exec(
                    select(IncidentEvent).filter(
                        or_(
                            IncidentEvent.incident_slug == incident_slug,
                            IncidentEvent.parent == incident_id,
                        )
                    )
                ).all()

                return records
            except Exception as error:
                logger.error(
                    f"Event log lookup failed for incident {incident_id}: {error}"
                )

    @classmethod
    def read_one(
        self,
        id: str,
        incident_id: id = None,
        incident_slug: str = None,
    ) -> list[IncidentEvent]:
        """
        Read a single event log from an incident

        Parameters:
            id (str): The event's uuid
            incident_id (int): The incident id
            incident_slug (str): The incident slug
        """

        with Session(engine) as session:
            try:
                records = session.exec(
                    select(IncidentEvent).filter(
                        IncidentEvent.incident_slug == incident_slug,
                        IncidentEvent.id == id,
                    )
                ).one()

                return records
            except Exception as error:
                logger.error(
                    f"Event log lookup failed for incident {incident_id}: {error}"
                )

    @classmethod
    def update(
        self,
        request: IncidentEvent,
    ):
        """
        Update an IncidentEvent

        Parameters:
            request (IncidentEvent): The record to be updated
        """

        with Session(engine) as session:
            try:
                record = session.exec(
                    select(IncidentEvent).filter(
                        IncidentEvent.id == request.id,
                    )
                ).one()

                # Compare existing record fields to new record fields
                # Update what has changed
                # Commit record

                if request.text != record.text:
                    record.text = request.text
                if request.timestamp != record.timestamp:
                    record.timestamp = request.timestamp
                if request.title != record.title:
                    record.title = request.title

                session.add(record)
                session.commit()

                logger.info(f"edited event {request.id}")
            except Exception as error:
                logger.error(f"Event log updated failed: {error}")