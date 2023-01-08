import logging

from bot.models.pg import Incident, Session
from sqlalchemy import or_
from typing import List

logger = logging.getLogger(__name__)

"""
Read
"""


def db_read_all_incidents(return_json: bool = False) -> List:
    """
    Return all rows from incidents table
    """
    try:
        all_incidents = Session.query(Incident)
        all_incidents_list = []
        for inc in all_incidents:
            if return_json:
                all_incidents_list.append(inc.serialize())
            else:
                all_incidents_list.append(inc)
        return all_incidents_list
    except Exception as error:
        logger.error(
            f"Incident lookup query failed when returning all incidents: {error}"
        )
    finally:
        Session.close()
        Session.remove()


def db_read_open_incidents() -> List:
    """
    Return all rows from incidents table for open (non-resolved) incidents
    """
    try:
        open_incidents = Session.query(Incident).filter(
            Incident.status != "resolved"
        )
        open_incidents_list = []
        for inc in open_incidents:
            open_incidents_list.append(inc)
        return open_incidents_list
    except Exception as error:
        logger.error(
            f"Incident lookup query failed when returning open incidents: {error}"
        )
    finally:
        Session.close()
        Session.remove()


def db_read_incident(
    incident_id: str = "", channel_id: str = "", return_json: bool = False
) -> Incident:
    """
    Read an incident from the database
    """
    try:
        incident = (
            Session.query(Incident)
            .filter(
                or_(
                    Incident.incident_id == incident_id,
                    Incident.channel_id == channel_id,
                )
            )
            .one()
        )
        if return_json:
            return incident.serialize()
        else:
            return incident
    except Exception as error:
        logger.error(
            f"Incident lookup query failed for {incident_id}: {error}"
        )
        raise error
    finally:
        Session.close()
        Session.remove()


def db_read_incident_channel_id(incident_id: str) -> str:
    """
    Read from database and return channel id
    """
    try:
        incident = (
            Session.query(Incident)
            .filter(Incident.incident_id == incident_id)
            .one()
        )
        return incident.channel_id
    except Exception as error:
        logger.error(
            f"Incident lookup query failed for {incident_id}: {error}"
        )
        raise error
    finally:
        Session.close()
        Session.remove()


"""
Update
"""


def db_update_incident_created_at_col(
    created_at: str,
    incident_id: str = "",
    channel_id: str = "",
):
    try:
        incident = (
            Session.query(Incident)
            .filter(
                or_(
                    Incident.incident_id == incident_id,
                    Incident.channel_id == channel_id,
                )
            )
            .one()
        )
        incident.created_at = created_at
        Session.commit()
    except Exception as error:
        logger.error(f"Incident update failed for {incident_id}: {error}")
        Session.rollback()
    finally:
        Session.close()
        Session.remove()


def db_update_incident_last_update_sent_col(
    last_update_sent: str,
    incident_id: str = "",
    channel_id: str = "",
):
    try:
        incident = (
            Session.query(Incident)
            .filter(
                or_(
                    Incident.incident_id == incident_id,
                    Incident.channel_id == channel_id,
                )
            )
            .one()
        )
        incident.last_update_sent = last_update_sent
        Session.commit()
    except Exception as error:
        incident = (
            Session.query(Incident)
            .filter(Incident.channel_id == channel_id)
            .one()
        )
        logger.error(
            f"Incident update failed for {incident.incident_id}: {error}"
        )
        Session.rollback()
    finally:
        Session.close()
        Session.remove()


def db_update_incident_role(
    role: str,
    user: str,
    incident_id: str = "",
    channel_id: str = "",
):
    try:
        incident = (
            Session.query(Incident)
            .filter(
                or_(
                    Incident.incident_id == incident_id,
                    Incident.channel_id == channel_id,
                )
            )
            .one()
        )
        if "incident_commander" in role:
            incident.commander = user
        elif "technical_lead" in role:
            incident.technical_lead = user
        elif "communications_liaison" in role:
            incident.communications_liaison = user
        else:
            logger.error(f"{role} is not a valid choice.")
        Session.commit()
    except Exception as error:
        logger.error(f"Incident update failed for {incident_id}: {error}")
        Session.rollback()
    finally:
        Session.close()
        Session.remove()


def db_update_incident_updated_at_col(
    updated_at: str,
    incident_id: str = "",
    channel_id: str = "",
):
    try:
        incident = (
            Session.query(Incident)
            .filter(
                or_(
                    Incident.incident_id == incident_id,
                    Incident.channel_id == channel_id,
                )
            )
            .one()
        )
        incident.updated_at = updated_at
        Session.commit()
    except Exception as error:
        logger.error(f"Incident update failed for {incident_id}: {error}")
        Session.rollback()
    finally:
        Session.close()
        Session.remove()


def db_update_incident_rca_col(
    rca: str,
    incident_id: str = "",
    channel_id: str = "",
):
    try:
        incident = (
            Session.query(Incident)
            .filter(
                or_(
                    Incident.incident_id == incident_id,
                    Incident.channel_id == channel_id,
                )
            )
            .one()
        )
        incident.rca = rca
        Session.commit()
    except Exception as error:
        logger.error(f"Incident update failed for {incident_id}: {error}")
        Session.rollback()
    finally:
        Session.close()
        Session.remove()


def db_update_incident_severity_col(
    severity: str,
    incident_id: str = "",
    channel_id: str = "",
):
    try:
        incident = (
            Session.query(Incident)
            .filter(
                or_(
                    Incident.incident_id == incident_id,
                    Incident.channel_id == channel_id,
                )
            )
            .one()
        )
        incident.severity = severity
        Session.commit()
    except Exception as error:
        logger.error(f"Incident update failed for {incident_id}: {error}")
        Session.rollback()
    finally:
        Session.close()
        Session.remove()


def db_update_incident_sp_id_col(
    sp_incident_id: str,
    incident_id: str = "",
    channel_id: str = "",
):
    try:
        incident = (
            Session.query(Incident)
            .filter(
                or_(
                    Incident.incident_id == incident_id,
                    Incident.channel_id == channel_id,
                )
            )
            .one()
        )
        incident.sp_incident_id = sp_incident_id
        Session.commit()
    except Exception as error:
        logger.error(f"Incident update failed for {incident_id}: {error}")
        Session.rollback()
    finally:
        Session.close()
        Session.remove()


def db_update_incident_sp_ts_col(
    ts: str,
    incident_id: str = "",
    channel_id: str = "",
):
    try:
        incident = (
            Session.query(Incident)
            .filter(
                or_(
                    Incident.incident_id == incident_id,
                    Incident.channel_id == channel_id,
                )
            )
            .one()
        )
        incident.sp_message_ts = ts
        Session.commit()
    except Exception as error:
        logger.error(f"Incident update failed for {incident_id}: {error}")
        Session.rollback()
    finally:
        Session.close()
        Session.remove()


def db_update_incident_status_col(
    status: str,
    incident_id: str = "",
    channel_id: str = "",
):
    try:
        incident = (
            Session.query(Incident)
            .filter(
                or_(
                    Incident.incident_id == incident_id,
                    Incident.channel_id == channel_id,
                )
            )
            .one()
        )
        incident.status = status
        Session.commit()
    except Exception as error:
        logger.error(f"Incident update failed for {incident_id}: {error}")
        Session.rollback()
    finally:
        Session.close()
        Session.remove()


"""
Write
"""


def db_write_incident(
    incident_id,
    channel_id,
    channel_name,
    status,
    severity,
    bp_message_ts,
    dig_message_ts,
    is_security_incident,
    channel_description,
    conference_bridge,
):
    """
    Write incident entry to database

    Args:
        incident_id - The formatted channel name (title) for the incident (primary key)
        channel_id - ID of the incident channel
        channel_name - Slack channel name
        status - Status of the incident
        severity - Severity of the incident
        bp_message_ts - Boilerplate message creation timestamp
        dig_message_ts - Digest channel message creation timestamp
        is_security_incident - Whether or not the incident is security-focused
        channel_description - Unformatted original description
        conference_bridge - Link to conference bridge
    """
    try:
        incident = Incident(
            incident_id=incident_id,
            channel_id=channel_id,
            channel_name=channel_name,
            status=status,
            severity=severity,
            bp_message_ts=bp_message_ts,
            dig_message_ts=dig_message_ts,
            tags=[],
            is_security_incident=is_security_incident,
            channel_description=channel_description,
            conference_bridge=conference_bridge,
            pagerduty_incidents=[],
        )
        Session.add(incident)
        Session.commit()
    except Exception as error:
        logger.error(f"Incident row create failed for {incident_id}: {error}")
        Session.rollback()
    finally:
        Session.close()
        Session.remove()
