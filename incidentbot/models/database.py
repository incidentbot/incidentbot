import uuid

from datetime import datetime
from incidentbot.configuration.settings import settings
from incidentbot.util.security import get_password_hash
from pydantic import BaseModel, EmailStr
from sqlalchemy import DateTime, func, text
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlmodel import (
    create_engine,
    Column,
    Field,
    JSON,
    LargeBinary,
    Relationship,
    select,
    Session,
    SQLModel,
)
from typing import Annotated, Optional

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
Models
"""


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=40)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=40)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=40)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=40)
    new_password: str = Field(min_length=8, max_length=40)


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=40)


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
    updated_at: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(),
            onupdate=func.now(),
        )
    )


class IncidentRecord(SQLModel, table=True):
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
    events: list["IncidentEvent"] = Relationship(
        back_populates="incident", cascade_delete=True
    )
    has_private_channel: bool | None = False
    id: int = Field(primary_key=True)
    impact: str | None = None
    is_security_incident: bool | None = None
    last_update_sent: Optional[datetime] = Field(
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
    updated_at: Optional[datetime] = Field(
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
    timestamp: Optional[datetime]
    title: str | None = None
    updated_at: Optional[datetime]
    user: str | None = None


class IncidentEvent(SQLModel, table=True):
    created_at: datetime = Field(
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
        }
    )
    id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    image: bytes | None = Field(sa_column=Column(LargeBinary))
    incident: IncidentRecord | None = Relationship(back_populates="events")
    incident_slug: str | None = None
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
    timestamp: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(),
        )
    )
    title: str | None = None
    updated_at: Optional[datetime] = Field(
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
    updated_at: Optional[datetime] = Field(
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


class MaintenanceWindowRecord(SQLModel, table=True):
    channels: list = Field(
        sa_column=Column(MutableList.as_mutable(JSON)), default_factory=list
    )
    components: list = Field(
        sa_column=Column(MutableList.as_mutable(JSON)), default_factory=list
    )
    contact: str | None = None
    created_at: datetime = Field(
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
        }
    )
    description: str
    end_timestamp: datetime = Field(
        sa_column=Column(
            DateTime(),
        )
    )
    id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    start_timestamp: datetime = Field(
        sa_column=Column(
            DateTime(),
        )
    )
    status: str
    title: str
    updated_at: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(),
            onupdate=func.now(),
        )
    )


class OpsgenieIncidentRecord(SQLModel, table=True):
    id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    parent: Annotated[
        int,
        Field(
            foreign_key="incidentrecord.id",
            ondelete="CASCADE",
            exclude=True,
        ),
    ]


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
    updated_at: Optional[datetime] = Field(
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
    updated_at: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(),
            onupdate=func.now(),
        )
    )
    updates: list | None = Field(
        sa_column=Column(MutableList.as_mutable(JSON)), default_factory=list
    )
    upstream_id: str


class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str


def create_models():
    """
    Create Models
    """

    SQLModel.metadata.create_all(engine)


def create_default_admin_user():
    """
    Create default admin user
    """

    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()

    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
        )

        db_obj = User.model_validate(
            user_in,
            update={"hashed_password": get_password_hash(user_in.password)},
        )
        session.add(db_obj)
        session.commit()
        session.refresh(db_obj)


session = Session(engine)
