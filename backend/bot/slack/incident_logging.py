import logging

from bot.models.pg import IncidentLogging, Session
from typing import Dict, List

logger = logging.getLogger(__name__)


def read(incident_id: str) -> List[Dict]:
    """
    Read pinned items
    """
    try:
        if Session.query(IncidentLogging).filter_by(incident_id=incident_id).all():
            try:
                all_objs = (
                    Session.query(IncidentLogging)
                    .filter_by(incident_id=incident_id)
                    .all()
                )
                all_objs_list = []
                for obj in all_objs:
                    if obj.img:
                        all_objs_list.append(
                            {
                                "id": obj.id,
                                "is_image": True,
                                "title": obj.title,
                                "ts": obj.ts,
                                "user": obj.user,
                            }
                        )
                    else:
                        all_objs_list.append(
                            {
                                "id": obj.id,
                                "is_image": False,
                                "content": obj.content,
                                "ts": obj.ts,
                                "user": obj.user,
                            }
                        )
                return all_objs_list
            except Exception as error:
                logger.error(
                    f"Audit log row lookup failed for incident {incident_id}: {error}"
                )
        else:
            logger.warning(f"No audit log record for {incident_id}")
    except Exception as error:
        logger.error(f"Audit log row lookup failed for incident {incident_id}: {error}")
    finally:
        Session.close()
        Session.remove()


def write(
    incident_id: str,
    ts: str,
    user: str,
    title: str = "",
    content: str = "",
    img: bytes = b"",
    mimetype: str = "",
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
        Session.add(obj)
        Session.commit()
    except Exception as error:
        logger.error(f"Audit log row create failed for incident {incident_id}: {error}")
        Session.rollback()
    finally:
        Session.close()
        Session.remove()
