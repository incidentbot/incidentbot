from incidentbot.configuration.settings import settings
from incidentbot.logging import logger
from incidentbot.models.database import (
    engine,
    IncidentParticipant,
    IncidentRecord,
    PagerDutyIncidentRecord,
    PhareIncidentRecord,
    PostmortemRecord,
    StatuspageIncidentRecord,
    GitlabIssueRecord,
)
from incidentbot.models.slack import User
from sqlalchemy.exc import NoResultFound
from sqlmodel import or_, Session, select

"""
API Models
"""


"""
Database Interface
"""


class IncidentDatabaseInterface:
    """
    An interface for managing incident related database records
    """

    """
    Get
    """

    @staticmethod
    def get_one(
        channel_id: str | None = None,
        channel_name: str | None = None,
        id: int | None = None,
        slug: str | None = None,
    ) -> IncidentRecord | None:
        """
        Read a single incident from the database

        Parameters:
            channel_id (str): Filter by channel_id
            channel_name (str): Filter by channel_name
            id (int): Filter by incident id
            slug (str): Filter by slug
        """

        try:
            with Session(engine) as session:
                # Build conditions only for non-None params — passing None would
                # generate "col IS NULL" via SQLAlchemy's == operator, which would
                # match orphaned records and cause MultipleResultsFound.
                conditions = []
                if channel_id is not None:
                    conditions.append(IncidentRecord.channel_id == channel_id)
                if channel_name is not None:
                    conditions.append(IncidentRecord.channel_name == channel_name)
                if id is not None:
                    conditions.append(IncidentRecord.id == id)
                if slug is not None:
                    conditions.append(IncidentRecord.slug == slug)

                if not conditions:
                    raise ValueError("get_one called with no filter parameters")

                incident = session.exec(
                    select(IncidentRecord).filter(or_(*conditions))
                ).one()

                return incident
        except NoResultFound:
            logger.warning("incident not found in database", channel_id=channel_id)
        except Exception as error:
            logger.exception("incident lookup (single) query failed", error=error)

    @staticmethod
    def get_statuspage_incident_record(
        id: int | None = None,
    ) -> StatuspageIncidentRecord | None:
        """
        Read a single Statuspage incident record from the database

        Parameters:
            id (int): Filter by incident id
        """

        try:
            with Session(engine) as session:
                return session.exec(
                    select(StatuspageIncidentRecord).filter(
                        StatuspageIncidentRecord.parent == id,
                    )
                ).one()
        except NoResultFound:
            logger.warning("statuspage incident not found for incident", id=id)
        except Exception as error:
            logger.exception("lookup failed", error=error)

    @staticmethod
    def get_phare_incident_record(
        id: int | None = None,
    ) -> PhareIncidentRecord | None:
        """
        Read a single Phare incident record from the database

        Parameters:
            id (int): Filter by incident id
        """

        try:
            with Session(engine) as session:
                return session.exec(
                    select(PhareIncidentRecord).filter(
                        PhareIncidentRecord.parent == id,
                    )
                ).one()
        except NoResultFound:
            logger.warning("phare incident not found for incident", id=id)
        except Exception as error:
            logger.exception("lookup failed", error=error)

    @staticmethod
    def get_gitlab_incident_record(
        id: int | None = None,
    ) -> GitlabIssueRecord | None:
        """
        Read a single GitLab issue record from the database

        Parameters:
            id (int): Filter by incident id
        """

        try:
            with Session(engine) as session:
                return session.exec(
                    select(GitlabIssueRecord).filter(
                        GitlabIssueRecord.parent == id,
                    )
                ).one()
        except NoResultFound:
            logger.warning("gitlab issue not found for incident", id=id)
        except Exception as error:
            logger.exception("lookup failed", error=error)

    """
    List
    """

    @staticmethod
    def list_all() -> list[IncidentRecord]:
        """
        Return all incidents
        """

        try:
            with Session(engine) as session:
                return session.exec(select(IncidentRecord)).all()
        except Exception as error:
            logger.exception("incident lookup (all) query failed", error=error)
            return []

    @staticmethod
    def list_open() -> list[IncidentRecord]:
        """
        Return all open (non-final-status) incidents
        """

        try:
            with Session(engine) as session:
                final_statuses = [
                    status
                    for status, config in settings.statuses.items()
                    if config.final
                ]

                if final_statuses:
                    incidents = session.exec(
                        select(IncidentRecord).filter(
                            IncidentRecord.status.not_in(final_statuses)
                        )
                    ).all()
                else:
                    incidents = session.exec(select(IncidentRecord)).all()

            return incidents
        except Exception as error:
            logger.exception("incident lookup query failed", error=error)
            return []

    @staticmethod
    def list_pagerduty_incident_records(
        id: int | None = None,
    ) -> list[PagerDutyIncidentRecord]:
        """
        Read all PagerDuty incidents associated with an incident

        Parameters:
            id (int): Filter by incident id
        """

        try:
            with Session(engine) as session:
                return session.exec(
                    select(PagerDutyIncidentRecord).filter(
                        PagerDutyIncidentRecord.parent == id,
                    )
                ).all()
        except NoResultFound:
            logger.warning("pagerduty incidents not found for incident", id=id)
            return []
        except Exception as error:
            logger.exception("lookup failed", error=error)
            return []

    @staticmethod
    def list_recent(limit: int = 5) -> list[IncidentRecord]:
        """
        Return most recent open incidents

        Parameters:
            limit (int): How many incidents to return (default 5)
        """

        final_statuses = [
            status
            for status, config in settings.statuses.items()
            if config.final
        ]

        try:
            with Session(engine) as session:
                stmt = select(IncidentRecord).order_by(
                    IncidentRecord.created_at.desc()
                )
                if final_statuses:
                    stmt = stmt.filter(
                        IncidentRecord.status.not_in(final_statuses)
                    )
                return session.exec(stmt.limit(limit)).all()
        except Exception as error:
            logger.exception("incident lookup (recent) query failed", error=error)
            return []

    """
    Update
    """

    @staticmethod
    def update_col(
        col_name: str,
        value: str,
        channel_id: str | None = None,
        id: int | None = None,
    ):
        """
        Updates the value of a column for an incident.

        Parameters:
            col_name (str): Column name
            value (str): New value for field
            channel_id (str): Filter by channel_id
            id (int): Filter by incident id
        """

        try:
            with Session(engine) as session:
                conditions = []
                if channel_id is not None:
                    conditions.append(IncidentRecord.channel_id == channel_id)
                if id is not None:
                    conditions.append(IncidentRecord.id == id)
                if not conditions:
                    raise ValueError("update_col called with no filter parameters")

                incident = session.exec(
                    select(IncidentRecord).filter(or_(*conditions))
                ).one()

                match col_name:
                    case "channel_name":
                        incident.channel_name = value
                    case "description":
                        incident.description = value
                    case "last_update_sent":
                        incident.last_update_sent = value
                    case "resolved_at":
                        incident.resolved_at = value
                    case "severity":
                        incident.severity = value
                    case "status":
                        incident.status = value
                session.add(incident)
                session.commit()
        except Exception as error:
            logger.exception(
                f"incident col update failed for col {col_name} in row {id}: {error}"
            )

    """
    Role management
    """

    @staticmethod
    def associate_role(
        incident: IncidentRecord,
        is_lead: bool,
        role: str,
        user: User,
    ):
        """
        Associates a user with an incident as a participant

        Parameters:
            incident (IncidentRecord): The IncidentRecord for the incident
            is_lead (bool): Whether or not this role is the lead role
            role (str): The role to associate the user with
            user (User): The user to associate with the role
        """

        try:
            with Session(engine) as session:
                participant = IncidentParticipant(
                    is_lead=is_lead,
                    parent=incident.id,
                    role=role,
                    user_id=user.id,
                    user_name=user.name,
                )

                session.add(participant)
                session.commit()
        except Exception as error:
            logger.exception(
                f"adding user {user.name} to incident {incident.slug} failed: {error}"
            )

    @staticmethod
    def check_role_assigned_to_user(
        incident: IncidentRecord,
        role: str,
        user: User,
    ) -> bool:
        """
        Checks whether or not a user has claimed a role for an incident

        Parameters:
            incident (IncidentRecord): The IncidentRecord for the incident
            role (str): The role
            user (User): The user
        """

        try:
            with Session(engine) as session:
                participant = session.exec(
                    select(IncidentParticipant).filter(
                        IncidentParticipant.parent == incident.id,
                        IncidentParticipant.role == role,
                        IncidentParticipant.user_id == user.id,
                    )
                ).first()

                return participant is not None
        except Exception as error:
            logger.exception(
                f"checking user {user.name} for {incident.slug} failed: {error}"
            )
            return False

    @staticmethod
    def list_participants(
        incident: IncidentRecord,
    ) -> list[IncidentParticipant]:
        """
        Returns any participants associated with an incident
        """

        try:
            with Session(engine) as session:
                participants = session.exec(
                    select(IncidentParticipant).filter(
                        IncidentParticipant.parent == incident.id,
                    )
                ).all()

            return participants
        except Exception as error:
            logger.exception(
                f"error getting participants for incident {incident.slug}: {error}"
            )
            return []

    @staticmethod
    def remove_role(
        incident: IncidentRecord,
        role: str,
        user: User,
    ):
        """
        Removes a user from an incident as a participant

        Parameters:
            incident (IncidentRecord): The IncidentRecord for the incident
            role (str): The role the user was associated with
            user (User): The user the role was associated with
        """

        try:
            with Session(engine) as session:
                participant = session.exec(
                    select(IncidentParticipant).filter(
                        IncidentParticipant.parent == incident.id,
                        IncidentParticipant.role == role,
                        IncidentParticipant.user_id == user.id,
                    )
                ).one()

                session.delete(participant)
                session.commit()
        except Exception as error:
            logger.exception(
                f"removing user {user.name} from incident {incident.slug} failed: {error}"
            )

    """
    Postmortem
    """

    @staticmethod
    def add_postmortem(
        parent: int,
        url: str,
    ):
        """
        Associates a postmortem with an incident

        Parameters:
            parent (int): ID of associated incident
            url (str): URL of the postmortem
        """

        try:
            with Session(engine) as session:
                postmortem = PostmortemRecord(
                    parent=parent,
                    url=url,
                )

                session.add(postmortem)
                session.commit()
        except Exception as error:
            logger.exception("creating postmortem record failed", error=error)

    @staticmethod
    def get_postmortem(
        parent: int,
    ) -> PostmortemRecord | None:
        """
        Return an incident postmortem if it exists

        Parameters:
            parent (int): ID of associated incident
        """

        with Session(engine) as session:
            return session.exec(
                select(PostmortemRecord).filter(
                    PostmortemRecord.parent == parent,
                )
            ).first()
