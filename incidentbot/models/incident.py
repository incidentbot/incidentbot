from incidentbot.configuration.settings import settings
from incidentbot.logging import logger
from incidentbot.models.database import (
    engine,
    IncidentParticipant,
    IncidentRecord,
    PagerDutyIncidentRecord,
    PostmortemRecord,
    StatuspageIncidentRecord,
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

    @classmethod
    def get_one(
        self,
        channel_id: str = None,
        channel_name: str = None,
        id: int = None,
        slug: str = None,
    ) -> IncidentRecord:
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
                incident = session.exec(
                    select(IncidentRecord).filter(
                        or_(
                            IncidentRecord.channel_id == channel_id,
                            IncidentRecord.channel_name == channel_name,
                            IncidentRecord.id == id,
                            IncidentRecord.slug == slug,
                        )
                    )
                ).one()

                return incident
        except NoResultFound:
            logger.error(f"incident {channel_id} not found in database")
        except Exception as error:
            logger.error(f"incident lookup (single) query failed: {error}")

    @classmethod
    def get_statuspage_incident_record(
        self,
        id: int = None,
    ) -> StatuspageIncidentRecord:
        """
        Read a single incident from the database

        Parameters:
            id (int): Filter by incident id
        """

        try:
            with Session(engine) as session:
                return session.exec(
                    select(StatuspageIncidentRecord).filter(
                        or_(
                            StatuspageIncidentRecord.parent == id,
                        )
                    )
                ).one()
        except NoResultFound:
            logger.error(f"Statuspage incident not found for incident {id}")
        except Exception as error:
            logger.error(f"Lookup failed: {error}")

    """
    List
    """

    @classmethod
    def list_all(self) -> list[IncidentRecord]:
        """
        Return all incidents
        """

        try:
            with Session(engine) as session:
                incidents = session.exec(select(IncidentRecord)).all()

                return incidents
        except Exception as error:
            logger.error(f"incident lookup (all) query failed: {error}")

    @classmethod
    def list_open(self) -> list[IncidentRecord]:
        """
        Return all open (non-resolved) incidents
        """

        try:
            with Session(engine) as session:
                incidents = session.exec(
                    select(IncidentRecord).filter(
                        IncidentRecord.status
                        != [
                            status
                            for status, config in settings.statuses.items()
                            if config.final
                        ][0]
                    )
                ).all()

            return incidents
        except Exception as error:
            logger.error(f"incident lookup query failed: {error}")

    @classmethod
    def list_pagerduty_incident_records(
        self,
        id: int = None,
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
                        or_(
                            PagerDutyIncidentRecord.parent == id,
                        )
                    )
                ).all()
        except NoResultFound:
            logger.error(f"PagerDuty incidents not found for incident {id}")
        except Exception as error:
            logger.error(f"Lookup failed: {error}")

    @classmethod
    def list_recent(self, limit: int = 5) -> list[IncidentRecord]:
        """
        Return most recent incidents, limit defaults to 5

        Parameters:
            limit (int): How many incidents to return
        """

        final_status = [
            status
            for status, config in settings.statuses.items()
            if config.final
        ][0]

        try:
            with Session(engine) as session:
                incidents = session.exec(
                    select(IncidentRecord)
                    .filter(IncidentRecord.status != final_status)
                    .order_by(IncidentRecord.created_at)
                ).all()

            return incidents[-limit:]
        except Exception as error:
            logger.error(f"incident lookup (recent) query failed: {error}")

    """
    Update
    """

    @classmethod
    def update_col(
        self,
        col_name: str,
        value: str,
        channel_id: str = "",
        id: int = None,
    ):
        """
        Updates the value of a column for an incident - don't forget to specify all
        required parameters for this method

        Parameters:
            col_name (str): Column name
            value (str): New value for field
            channel_id (str): Filter by channel_id
            id (str): Filter by incident id
        """

        try:
            with Session(engine) as session:
                incident = session.exec(
                    select(IncidentRecord).filter(
                        or_(
                            IncidentRecord.channel_id == channel_id,
                            IncidentRecord.id == id,
                        )
                    )
                ).one()

                match col_name:
                    case "channel_name":
                        incident.channel_name = value
                    case "description":
                        incident.description = value
                    case "last_update_sent":
                        incident.last_update_sent = value
                    case "severity":
                        incident.severity = value
                    case "status":
                        incident.status = value
                session.add(incident)
                session.commit()
        except Exception as error:
            logger.error(
                f"incident col update failed for col {col_name} in row {id}: {error}"
            )

    """
    Role management
    """

    @classmethod
    def associate_role(
        self,
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
            role (dict): The role to associate the user with
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
            logger.error(
                f"adding user {user.name} to incident {incident.slug} failed: {error}"
            )

    @classmethod
    def check_role_assigned_to_user(
        self,
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

                if participant:
                    return True
                return False
        except Exception as error:
            logger.error(
                f"checking user {user.name} for {incident.slug} failed: {error}"
            )

    @classmethod
    def list_participants(
        self,
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
            logger.error(
                f"error getting participants for incidnet {incident.slug}: {error}"
            )

    @classmethod
    def remove_role(
        self,
        incident: IncidentRecord,
        role: str,
        user: User,
    ):
        """
        Removes a user from an incident as a participant

        Parameters:
            incident (IncidentRecord): The IncidentRecord for the incident
            is_lead (bool): Whether or not this role is the lead role
            role (dict): The role the user was associated with
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
            logger.error(
                f"removing user {user.name} from incident {incident.slug} failed: {error}"
            )

    """
    Postmortem
    """

    @classmethod
    def add_postmortem(
        self,
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
            logger.error(f"creating postmortem record failed: {error}")

    @classmethod
    def get_postmortem(
        self,
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
