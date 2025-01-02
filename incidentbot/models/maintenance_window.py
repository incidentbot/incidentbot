import uuid

from incidentbot.logging import logger
from incidentbot.models.database import engine, MaintenanceWindowRecord
from sqlalchemy.exc import NoResultFound
from sqlmodel import or_, Session, select

"""
API Models
"""


"""
Database Interface
"""


class MaintenanceWindowDatabaseInterface:
    """
    An interface for managing maintenance window related database records
    """

    """
    Get
    """

    @classmethod
    def get_one(
        self,
        id: uuid.UUID = None,
    ) -> MaintenanceWindowRecord:
        """
        Read a single maintenance window from the database

        Parameters:
            id (uuid.UUID): Filter by record id

        """

        try:
            with Session(engine) as session:
                maintenance_window = session.exec(
                    select(MaintenanceWindowRecord).filter(
                        or_(
                            MaintenanceWindowRecord.id == id,
                        )
                    )
                ).one()

                return maintenance_window
        except NoResultFound:
            logger.error(f"maintenance window {id} not found in database")
        except Exception as error:
            logger.error(
                f"maintenance window lookup (single) query failed: {error}"
            )

    """
    List
    """

    @classmethod
    def list_all(self) -> list[MaintenanceWindowRecord]:
        """
        Return all maintenance windows
        """

        try:
            with Session(engine) as session:
                return session.exec(select(MaintenanceWindowRecord)).all()
        except Exception as error:
            logger.error(
                f"maintenance window lookup (all) query failed: {error}"
            )

    """
    Delete
    """

    @classmethod
    def delete_one(
        self,
        maintenance_window: MaintenanceWindowRecord,
    ):
        """
        Deletes a maintenance window record

        Parameters:
            maintenance_window (MaintenanceWindowRecord): The record for the maintenance window
        """

        try:
            with Session(engine) as session:
                session.delete(maintenance_window)
                session.commit()
        except Exception as error:
            logger.error(
                f"deleting maintenance window {maintenance_window.id} failed: {error}"
            )

    """
    Update
    """

    @classmethod
    def set_status(
        self,
        id: uuid.UUID,
        status: str,
    ):
        """
        Sets maintenance window status to Complete

        Parameters:
            maintenance_window (MaintenanceWindowRecord): The record for the maintenance window
            status (str): Status to set
        """

        try:
            with Session(engine) as session:
                maintenance_window = session.exec(
                    select(MaintenanceWindowRecord).filter(
                        or_(
                            MaintenanceWindowRecord.id == id,
                        )
                    )
                ).one()

                maintenance_window.status = status
                session.commit()
        except NoResultFound:
            logger.error(f"maintenance window {id} not found in database")
        except Exception as error:
            logger.error(
                f"maintenance window update (single) query failed: {error}"
            )
