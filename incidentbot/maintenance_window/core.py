from datetime import datetime
from incidentbot.logging import logger
from incidentbot.configuration.settings import settings
from incidentbot.models.database import MaintenanceWindowRecord, engine
from pydantic import BaseModel
from sqlmodel import Session


class MaintenanceWindowRequestParameters(BaseModel):
    """
    Base incident creation details
    """

    channels: list[str]
    components: list[str]
    contact: str
    description: str
    end_timestamp: datetime
    start_timestamp: datetime
    title: str


class MaintenanceWindow:
    """
    Instantiates a maintenance window

    Parameters:
        params (MaintenanceWindowRequestParameters): Parameters to pass to configuration
    """

    def __init__(self, params: MaintenanceWindowRequestParameters):
        self.params = params

    def create(self) -> str:
        """
        Create a maintenance window
        """

        # Need to store channels as both name and ID

        """
        Write maintenance window entry to database
        """

        logger.info(
            f"Writing maintenance window entry to database for {self.params.title}..."
        )
        try:
            with Session(engine) as session:
                maintenance_window = MaintenanceWindowRecord(
                    channels=self.params.channels,
                    components=self.params.components,
                    contact=self.params.contact,
                    description=self.params.description,
                    end_timestamp=self.params.end_timestamp,
                    start_timestamp=self.params.start_timestamp,
                    status=settings.maintenance_windows.statuses[0],
                    title=self.params.title,
                )
                session.add(maintenance_window)
                session.commit()
        except Exception as error:
            logger.fatal(
                f"Error writing entry to database for {self.params.title}: {error}"
            )
