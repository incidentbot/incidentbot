import config
import logging

from sqlalchemy import create_engine, inspect
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    LargeBinary,
    String,
    VARCHAR,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

logger = logging.getLogger(__name__)

engine = create_engine(
    config.database_url,
    isolation_level="REPEATABLE READ",
    echo_pool=True,
    pool_pre_ping=True,
)

Base = declarative_base()
session_factory = sessionmaker(engine, autocommit=False, autoflush=False)
Session = scoped_session(session_factory)


def db_verify():
    """
    Verify database is reachable
    """
    try:
        conn = engine.connect()
        conn.close()
        return True
    except:
        return False


"""
Models
"""


class Serializer(object):
    def serialize(self):
        return {c: getattr(self, c) for c in inspect(self).attrs.keys()}

    @staticmethod
    def serialize_list(l):
        return [m.serialize() for m in l]


class AuditLog(Base, Serializer):
    __tablename__ = "auditlog"

    incident_id = Column(String(100), primary_key=True, nullable=False)
    data = Column(JSON)

    def serialize(self):
        d = Serializer.serialize(self)
        return d


class Incident(Base, Serializer):
    __tablename__ = "incidents"

    incident_id = Column(VARCHAR(100), primary_key=True, nullable=False)
    channel_id = Column(VARCHAR(100), nullable=False)
    channel_name = Column(VARCHAR(100), nullable=False)
    status = Column(VARCHAR(50), nullable=False)
    severity = Column(VARCHAR(50), nullable=False)
    bp_message_ts = Column(VARCHAR(50), nullable=False)
    dig_message_ts = Column(VARCHAR(50), nullable=False)
    sp_message_ts = Column(VARCHAR(50))
    sp_incident_id = Column(VARCHAR(50))
    created_at = Column(VARCHAR(50))
    updated_at = Column(VARCHAR(50))
    last_update_sent = Column(VARCHAR(50))
    tags = Column(JSON)
    commander = Column(VARCHAR(50))
    technical_lead = Column(VARCHAR(50))
    communications_liaison = Column(VARCHAR(50))
    rca = Column(VARCHAR)
    is_security_incident = Column(Boolean)
    channel_description = Column(String())
    conference_bridge = Column(String())
    pagerduty_incidents = Column(JSON)

    def serialize(self):
        d = Serializer.serialize(self)
        return d


class IncidentLogging(Base, Serializer):
    __tablename__ = "incident_logging"

    id = Column(Integer, primary_key=True)
    incident_id = Column(String(100), nullable=False)
    title = Column(String)
    content = Column(String)
    img = Column(LargeBinary)
    mimetype = Column(String)
    ts = Column(String, nullable=False)
    user = Column(String, nullable=False)

    def serialize(self):
        d = Serializer.serialize(self)
        return d


class OperationalData(Base, Serializer):
    __tablename__ = "opdata"

    id = Column((String(30)), primary_key=True, nullable=False)
    data = Column(VARCHAR(250))
    json_data = Column(JSON)
    updated_at = Column(VARCHAR(50))

    def serialize(self):
        d = Serializer.serialize(self)
        return d


class PostmortemSettings(Base, Serializer):
    __tablename__ = "postmortem_settings"

    id = Column((String(30)), primary_key=True, nullable=False)
    data = Column(String)
    json_data = Column(JSON)
    updated_at = Column(VARCHAR(50))

    def serialize(self):
        d = Serializer.serialize(self)
        return d


class Setting(Base, Serializer):
    __tablename__ = "application_settings"

    name = Column(String(50), primary_key=True, nullable=False)
    value = Column(JSON)
    description = Column(VARCHAR(250))
    deletable = Column(Boolean)

    def serialize(self):
        d = Serializer.serialize(self)
        return d


class SlackData(Base, Serializer):
    __tablename__ = "slack_data"

    id = Column((String(30)), primary_key=True, nullable=False)
    data = Column(VARCHAR(250))
    json_data = Column(JSON)
    updated_at = Column(VARCHAR(50))

    def serialize(self):
        d = Serializer.serialize(self)
        return d


class TokenBlocklist(Base):
    __tablename__ = "jwt_blocklist"

    id = Column(Integer, primary_key=True)
    jti = Column(String(36), nullable=False, index=True)
    type = Column(String(16), nullable=False)
    user_id = Column(ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False)


class User(Base, Serializer):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(100), unique=True)
    password = Column(String(100))
    name = Column(String(100))
    role = Column(String(20))
    is_admin = Column(Boolean, default=False)
    is_disabled = Column(Boolean, default=False)


"""
Create Models
"""
Base.metadata.create_all(engine)
