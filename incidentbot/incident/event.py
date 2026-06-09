from datetime import datetime

from incidentbot.configuration.settings import settings
from incidentbot.logging import logger
from incidentbot.models.database import engine, IncidentEvent
from incidentbot.util.gen import fetch_timestamp
from sqlmodel import Session, select, or_


class EventLogHandler:
    @staticmethod
    def _resolve_user_display_name(user: str | None) -> str:
        if not user:
            return "NotAvailable"

        if settings.IS_TEST_ENVIRONMENT:
            return user

        try:
            from incidentbot.platform import get_adapter

            return get_adapter().get_user_display_name(user)
        except Exception:
            return user

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
                    message_ts=(
                        message_ts
                        if message_ts
                        else fetch_timestamp(epoch=True)
                    ),
                    mimetype=mimetype,
                    parent=incident_id,
                    source=source,
                    text=event,
                    timestamp=timestamp,
                    title=title,
                    user=self._resolve_user_display_name(user),
                )

                session.add(event)
                session.commit()
            except Exception as error:
                logger.exception(
                    "event log creation failed", incident_id=incident_id, error=error
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

                logger.info("deleted incident event", event_id=id)
            except Exception as error:
                logger.exception(
                    "event log delete failed", event_id=id, error=error
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
                    select(IncidentEvent)
                    .filter(
                        or_(
                            IncidentEvent.incident_slug == incident_slug,
                            IncidentEvent.parent == incident_id,
                        )
                    )
                    .order_by(
                        IncidentEvent.message_ts, IncidentEvent.created_at
                    )
                ).all()

                return records
            except Exception as error:
                logger.exception(
                    "event log lookup failed", incident_id=incident_id, error=error
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
                    select(IncidentEvent)
                    .filter(
                        IncidentEvent.incident_slug == incident_slug,
                        IncidentEvent.id == id,
                    )
                    .order_by(
                        IncidentEvent.message_ts, IncidentEvent.created_at
                    )
                ).one()

                return records
            except Exception as error:
                logger.exception(
                    "event log lookup failed", incident_id=incident_id, error=error
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

                logger.info("edited event", event_id=request.id)
            except Exception as error:
                logger.exception("event log update failed", error=error)
