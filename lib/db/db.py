import logging

from __main__ import config
from flask_login import UserMixin
from sqlalchemy import create_engine
from sqlalchemy import Boolean, Column, Integer, String, VARCHAR
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import List

logger = logging.getLogger(__name__)

"""
Database Setup
"""

db = create_engine(config.database_url, pool_pre_ping=True)
base = declarative_base()

# Tables
class Incident(base):
    __tablename__ = "incidents"

    incident_id = Column(VARCHAR(50), primary_key=True, nullable=False)
    channel_id = Column(VARCHAR(50), nullable=False)
    channel_name = Column(VARCHAR(50), nullable=False)
    status = Column(VARCHAR(50), nullable=False)
    severity = Column(VARCHAR(50), nullable=False)
    bp_message_ts = Column(VARCHAR(50), nullable=False)
    dig_message_ts = Column(VARCHAR(50), nullable=False)
    dig_message_ts = Column(VARCHAR(50), nullable=False)
    sp_message_ts = Column(VARCHAR(50))
    sp_incident_id = Column(VARCHAR(50))


class User(UserMixin, base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(100), unique=True)
    password = Column(String(100))
    name = Column(String(100))
    role = Column(String(20))
    is_admin = Column(Boolean, default=False)
    is_disabled = Column(Boolean, default=False)


# Create session
Session = sessionmaker(db)
session = Session()
base.metadata.create_all(db)

"""
Helper Methods
"""


def db_verify():
    """
    Verify database is reachable
    """
    try:
        conn = db.connect()
        conn.close()
        return True
    except:
        return False


"""
Incident Management
"""


def db_read_all_incidents() -> List:
    """
    Return all rows from incidents table
    """
    try:
        all_incidents = session.query(Incident)
        all_incidents_list = []
        for inc in all_incidents:
            all_incidents_list.append(inc)
        return all_incidents_list
    except Exception as error:
        logger.error(
            f"Incident lookup query failed when returning all incidents: {error}"
        )


def db_read_incident(incident_id: str) -> Incident:
    """
    Read from database
    """
    try:
        incident = (
            session.query(Incident).filter(Incident.incident_id == incident_id).one()
        )
        return incident
    except Exception as error:
        logger.error(f"Incident lookup query failed for {incident_id}: {error}")


def db_update_incident_severity_col(incident_id: str, severity: str):
    try:
        incident = db_read_incident(incident_id=incident_id)
        incident.severity = severity
        session.commit()
    except Exception as error:
        logger.error(f"Incident update failed for {incident_id}: {error}")


def db_update_incident_sp_id_col(incident_id: str, sp_incident_id: str):
    try:
        incident = db_read_incident(incident_id=incident_id)
        incident.sp_incident_id = sp_incident_id
        session.commit()
    except Exception as error:
        logger.error(f"Incident update failed for {incident_id}: {error}")


def db_update_incident_sp_ts_col(incident_id: str, ts: str):
    try:
        incident = db_read_incident(incident_id=incident_id)
        incident.sp_message_ts = ts
        session.commit()
    except Exception as error:
        logger.error(f"Incident update failed for {incident_id}: {error}")


def db_update_incident_status_col(incident_id: str, status: str):
    try:
        incident = db_read_incident(incident_id=incident_id)
        incident.status = status
        session.commit()
    except Exception as error:
        logger.error(f"Incident update failed for {incident_id}: {error}")


def db_write_incident(
    incident_id,
    channel_id,
    channel_name,
    status,
    severity,
    bp_message_ts,
    dig_message_ts,
):
    """
    Write incident entry to database

    Args:
        incident_id - The formatted channel name (title) for the incident (primary key)
        channel_id - ID of the incident channel
        channel_name - Slack channel name
        status - Status of the incident
        severity - Severeity of the incident
        bp_message_id - Boilerplate message ID
        bp_message_ts - Boilerplate message creation timestamp
        dig_message_id - Digest channel message ID
        dig_message_ts - Digest channel message creation timestamp
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
        )
        session.add(incident)
        session.commit()
    except Exception as error:
        logger.error(f"Incident row create failed for {incident_id}: {error}")


"""
User Management
"""


def db_user_lookup(email: str = None, id: int = None, all: bool = False):
    if all:
        try:
            logger.debug(f"Attempting to return all users...")
            user = session.query(User)
            return user
        except Exception as error:
            logger.error(f"User lookup failed: {error}")
    elif not all and email != None:
        try:
            logger.debug(f"Attempting to lookup user {email}...")
            user = session.query(User).filter(User.email == email).first()
            return user
        except Exception as error:
            logger.error(f"User lookup failed for {email}: {error}")
    elif not all and id != None:
        try:
            logger.debug(f"Attempting to lookup user id {id}...")
            user = session.query(User).filter(User.id == id).first()
            return user
        except Exception as error:
            logger.error(f"User lookup failed for {email}: {error}")


def db_user_create(
    email: str,
    name: str,
    password: str,
    role: str,
    is_admin: bool = False,
):
    try:
        new_user = User(
            email=email,
            name=name,
            password=password,
            role=role,
            is_admin=is_admin,
        )
        session.add(new_user)
        session.commit()
    except Exception as error:
        logger.error(f"User creation failed for {email}: {error}")


def db_user_delete(email: str):
    try:
        session.query(User).filter(User.email == email).delete()
        session.commit()
    except Exception as error:
        logger.error(f"User deletion failed for {email}: {error}")


def db_user_disable(email: str):
    try:
        user = session.query(User).filter(User.email == email).one()
        user.is_disabled = True
        session.commit()
    except Exception as error:
        logger.error(f"User disable failed for {email}: {error}")


def db_user_enable(email: str):
    try:
        user = session.query(User).filter(User.email == email).one()
        user.is_disabled = False
        session.commit()
    except Exception as error:
        logger.error(f"User enable failed for {email}: {error}")
