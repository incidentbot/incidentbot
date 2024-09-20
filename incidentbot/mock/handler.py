import random
import string

from incidentbot.logging import logger
from incidentbot.models.database import engine, IncidentRecord
from sqlmodel import Session


def create_mock_incident_data(amount: int):
    """
    Load dummy data into database.
    """

    i = 0

    while i < amount:
        try:
            suffix = "".join(
                random.choices(string.ascii_letters + string.digits, k=8)
            )
            identifier = f"mock-{suffix}"

            with Session(engine) as session:
                incident = IncidentRecord(
                    id=identifier,
                    boilerplate_message_ts="",
                    description=f"mock {identifier}",
                    channel_id=identifier.replace("-", ""),
                    channel_name=identifier,
                    digest_message_ts="",
                    is_security_incident=False,
                    meeting_link="mock",
                    severity="sev4",
                    status="investigating",
                )
                session.add(incident)
                session.commit()
        except Exception as error:
            logger.fatal(f"error writing mock entry to database: {error}")

        logger.info(f"added {identifier} to db")

        i += 1
