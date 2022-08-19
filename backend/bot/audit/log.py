import logging

from bot.models.pg import AuditLog, Session
from bot.shared import tools
from bot.slack.client import get_user_name
from sqlalchemy import update
from typing import Dict, List

logger = logging.getLogger(__name__)


def delete(incident_id: str, log: str, ts: str) -> tuple[bool, str]:
    """
    Delete from audit log
    """
    try:
        if Session.query(AuditLog).filter_by(incident_id=incident_id).all():
            try:
                existing_row = (
                    Session.query(AuditLog).filter_by(incident_id=incident_id).one()
                )
                for log_obj in existing_row.data:
                    if log in log_obj.values() and ts in log_obj.values():
                        found = True
                        break
                    else:
                        found = False
                if found:
                    Session.execute(
                        update(AuditLog)
                        .where(AuditLog.incident_id == incident_id)
                        .values(
                            data=[
                                i
                                for i in existing_row.data
                                if not (log in i.values() and ts in i.values())
                            ]
                        )
                    )
                    Session.commit()
                    return True, "removed log entry"
                else:
                    return False, "log entry not found"
            except Exception as error:
                logger.error(
                    f"Audit log row lookup failed for incident {incident_id}: {error}"
                )
        else:
            logger.warning(f"No audit log record for {incident_id}")
            return False, "no incident found with that id"
    except Exception as error:
        logger.error(f"Audit log row lookup failed for incident {incident_id}: {error}")
        return False, error
    finally:
        Session.close()
        Session.remove()


def read(incident_id: str) -> List[Dict]:
    """
    Read audit log
    """
    try:
        if Session.query(AuditLog).filter_by(incident_id=incident_id).all():
            try:
                existing_row = (
                    Session.query(AuditLog).filter_by(incident_id=incident_id).one()
                )
                return existing_row.data
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
    incident_id: str, event: str, content: str = "", user: str = "", ts: str = ""
):
    """
    Write an audit log for an incident

    Logs are appended to a JSON list
    """
    try:
        # Create the row if it doesn't exist
        if not Session.query(AuditLog).filter_by(incident_id=incident_id).all():
            try:
                row = AuditLog(incident_id=incident_id, data=[])
                Session.add(row)
                Session.commit()
            except Exception as error:
                logger.error(
                    f"Audit log row create failed for incident {incident_id}: {error}"
                )
        existing_row = Session.query(AuditLog).filter_by(incident_id=incident_id).one()
        data = existing_row.data
        data.append(
            {
                "log": event,
                "user": get_user_name(user),
                "content": content,
                "ts": ts if ts != "" else tools.fetch_timestamp(),
            }
        )
        Session.execute(
            update(AuditLog)
            .where(AuditLog.incident_id == incident_id)
            .values(data=data)
        )
        Session.commit()
    except Exception as error:
        logger.error(f"Audit log row create failed for incident {incident_id}: {error}")
        Session.rollback()
    finally:
        Session.close()
        Session.remove()
