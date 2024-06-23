import random
import string

from bot.models.incident import (
    db_write_incident,
)
from logger import logger


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

            db_write_incident(
                incident_id=identifier,
                channel_id=identifier.replace("-", ""),
                channel_name=identifier,
                status="investigating",
                severity="sev4",
                bp_message_ts="",
                dig_message_ts="",
                is_security_incident=False,
                channel_description=f"mock {identifier}",
                meeting_link="mock",
            )
        except Exception as error:
            logger.fatal(f"error writing mock entry to database: {error}")

        logger.info(f"added {identifier} to db")

        i += 1
