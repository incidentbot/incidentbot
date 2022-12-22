import logging

from bot.models.pg import IncidentLogging, Session
from sqlalchemy.orm import scoped_session
from typing import Dict, List

logger = logging.getLogger(__name__)


def read(
    incident_id: str, database_session: scoped_session = Session
) -> List[IncidentLogging]:
    """
    Read pinned items
    """
    try:
        if (
            database_session.query(IncidentLogging)
            .filter_by(incident_id=incident_id)
            .all()
        ):
            try:
                all_objs = (
                    database_session.query(IncidentLogging)
                    .filter_by(incident_id=incident_id)
                    .all()
                )
                return all_objs
            except Exception as error:
                logger.error(
                    f"Audit log row lookup failed for incident {incident_id}: {error}"
                )
        else:
            logger.warning(f"No audit log record for {incident_id}")
    except Exception as error:
        logger.error(
            f"Audit log row lookup failed for incident {incident_id}: {error}"
        )
    finally:
        database_session.close()
        database_session.remove()


def write(
    incident_id: str,
    ts: str,
    user: str,
    title: str = "",
    content: str = "",
    img: bytes = b"",
    mimetype: str = "",
    database_session: scoped_session = Session,
):
    """
    Write a pinned item
    """
    try:
        obj = IncidentLogging(
            incident_id=incident_id,
            title=title,
            content=content,
            img=img,
            mimetype=mimetype,
            ts=ts,
            user=user,
        )
        database_session.add(obj)
        database_session.commit()
    except Exception as error:
        logger.error(
            f"Audit log row create failed for incident {incident_id}: {error}"
        )
        database_session.rollback()
    finally:
        database_session.close()
        database_session.remove()
