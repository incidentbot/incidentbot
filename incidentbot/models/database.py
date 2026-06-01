import uuid

from datetime import datetime
from incidentbot.configuration.settings import settings
from pydantic import BaseModel
from sqlalchemy import DateTime, func, text
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlmodel import (
    create_engine,
    Column,
    Field,
    ForeignKey,
    JSON,
    LargeBinary,
    Relationship,
    SQLModel,
)
from typing import Annotated

engine = create_engine(
    settings.DATABASE_URI,
    echo_pool=True,
    pool_pre_ping=True,
)


def db_verify():
    """
    Verify database is reachable
    """
    try:
        conn = engine.connect()
        conn.close()
        return True
    except Exception:
        return False


"""
Tables
"""


class ApplicationData(SQLModel, table=True):
    created_at: datetime = Field(
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
        }
    )
    data: str | None = None
    deletable: bool | None = None
    description: str | None = None
    id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    json_data: dict | None = Field(
        sa_column=Column(JSON), default_factory=dict
    )
    name: str
    updated_at: datetime | None = Field(
        sa_column=Column(
            DateTime(),
            onupdate=func.now(),
        )
    )


class IncidentRecord(SQLModel, table=True):
    __tablename__ = "incidentrecord"

    additional_comms_channel: bool | None = None
    additional_comms_channel_id: str | None = None
    additional_comms_channel_link: str | None = None
    boilerplate_message_ts: str | None = None
    channel_id: str | None = None
    channel_name: str | None = None
    components: str | None = None
    created_at: datetime = Field(
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
        }
    )
    description: str | None = None
    digest_message_ts: str | None = None
    events: list[IncidentEvent] = Relationship(
        back_populates="incident",
        sa_relationship_kwargs={
            "primaryjoin": "IncidentEvent.parent == IncidentRecord.id",
            "foreign_keys": "[IncidentEvent.parent]",
            "cascade": "all, delete-orphan",
        },
    )
    has_private_channel: bool | None = False
    id: int = Field(primary_key=True)
    impact: str | None = None
    is_security_incident: bool | None = None
    last_update_sent: datetime | None = Field(
        sa_column=Column(
            DateTime(),
        )
    )
    link: str | None = None
    meeting_link: str | None = None
    roles: dict | None = Field(
        sa_column=Column(MutableDict.as_mutable(JSON)), default_factory=dict
    )
    roles_all: list | None = Field(
        sa_column=Column(MutableList.as_mutable(JSON)), default_factory=list
    )
    severity: str | None = None
    severities: list | None = Field(
        sa_column=Column(MutableList.as_mutable(JSON)), default_factory=list
    )
    slug: str | None = None
    status: str | None = None
    statuses: list | None = Field(
        sa_column=Column(MutableList.as_mutable(JSON)), default_factory=list
    )
    tags: list | None = Field(
        sa_column=Column(MutableList.as_mutable(JSON)), default_factory=list
    )
    updated_at: datetime | None = Field(
        sa_column=Column(
            DateTime(),
            onupdate=func.now(),
        )
    )


class IncidentEventBase(BaseModel):
    """
    IncidentEvent base class, excludes image
    """

    created_at: datetime
    id: uuid.UUID
    incident_slug: str
    message_ts: str | None = None
    mimetype: str | None = None
    parent: Annotated[
        int,
        Field(
            foreign_key="incidentrecord.id",
            ondelete="CASCADE",
            exclude=True,
        ),
    ]
    source: str
    text: str | None = None
    timestamp: datetime | None
    title: str | None = None
    updated_at: datetime | None
    user: str | None = None


class IncidentEvent(SQLModel, table=True):
    __tablename__ = "incidentevent"

    created_at: datetime = Field(
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
        }
    )
    id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    image: bytes | None = Field(sa_column=Column(LargeBinary))
    incident: IncidentRecord | None = Relationship(
        back_populates="events",
        sa_relationship_kwargs={
            "primaryjoin": "IncidentEvent.parent == IncidentRecord.id",
            "foreign_keys": "[IncidentEvent.parent]",
        },
    )
    incident_slug: str | None = None
    message_ts: str | None = None
    mimetype: str | None = None
    parent: int = Field(
        sa_column=Column(
            "parent",
            ForeignKey("incidentrecord.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    source: str
    text: str | None = None
    timestamp: datetime | None = Field(
        sa_column=Column(
            DateTime(),
        )
    )
    title: str | None = None
    updated_at: datetime | None = Field(
        sa_column=Column(
            DateTime(),
            onupdate=func.now(),
        )
    )
    user: str | None = None


class IncidentParticipant(SQLModel, table=True):
    created_at: datetime = Field(
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
        }
    )
    id: int = Field(primary_key=True)
    is_lead: bool
    parent: Annotated[
        int,
        Field(
            foreign_key="incidentrecord.id",
            ondelete="CASCADE",
            exclude=True,
        ),
    ]
    role: str
    updated_at: datetime | None = Field(
        sa_column=Column(
            DateTime(),
            onupdate=func.now(),
        )
    )
    user_id: str
    user_name: str


class JiraIssueRecord(SQLModel, table=True):
    key: str = Field(default=None, primary_key=True)
    parent: Annotated[
        int,
        Field(
            foreign_key="incidentrecord.id",
            ondelete="CASCADE",
            exclude=True,
        ),
    ]
    status: str | None = None
    team: str | None = None
    url: str | None = None


class GitlabIssueRecord(SQLModel, table=True):
    id: str = Field(
        default=None, primary_key=True
    )  # GitLab Issue ID (globally unique)
    parent: Annotated[
        int,
        Field(
            foreign_key="incidentrecord.id",
            ondelete="CASCADE",
            exclude=True,
        ),
    ]
    iid: str | None = None  # GitLab Issue IID (project-scoped unique)
    status: str | None = None
    url: str | None = None


class PagerDutyIncidentRecord(SQLModel, table=True):
    created_at: datetime = Field(
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
        }
    )
    id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    parent: Annotated[
        int,
        Field(
            foreign_key="incidentrecord.id",
            ondelete="CASCADE",
            exclude=True,
        ),
    ]
    updated_at: datetime | None = Field(
        sa_column=Column(
            DateTime(),
            onupdate=func.now(),
        )
    )
    url: str | None = None


class PostmortemRecord(SQLModel, table=True):
    id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    parent: Annotated[
        int,
        Field(
            foreign_key="incidentrecord.id",
            ondelete="CASCADE",
            exclude=True,
        ),
    ]
    url: str | None = None


class StatuspageIncidentRecord(SQLModel, table=True):
    channel_id: str | None = None
    id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    message_ts: str | None = None
    name: str | None = None
    parent: Annotated[
        int,
        Field(
            foreign_key="incidentrecord.id",
            ondelete="CASCADE",
            exclude=True,
        ),
    ]
    shortlink: str | None = None
    status: str | None = None
    updated_at: datetime | None = Field(
        sa_column=Column(
            DateTime(),
            onupdate=func.now(),
        )
    )
    updates: list | None = Field(
        sa_column=Column(MutableList.as_mutable(JSON)), default_factory=list
    )
    upstream_id: str


class PhareIncidentRecord(SQLModel, table=True):
    channel_id: str | None = None
    id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    message_ts: str | None = None
    name: str | None = None
    parent: Annotated[
        int,
        Field(
            foreign_key="incidentrecord.id",
            ondelete="CASCADE",
            exclude=True,
        ),
    ]
    state: str | None = None
    updated_at: datetime | None = Field(
        sa_column=Column(
            DateTime(),
            onupdate=func.now(),
        )
    )
    updates: list | None = Field(
        sa_column=Column(MutableList.as_mutable(JSON)), default_factory=list
    )
    upstream_id: int
    url: str | None = None


def create_models():
    """
    Create Models
    """

    SQLModel.metadata.create_all(engine)
