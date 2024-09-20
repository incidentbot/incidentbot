import opsgenie_sdk
import requests

from incidentbot.configuration.settings import settings
from incidentbot.logging import logger
from incidentbot.models.database import engine, ApplicationData
from incidentbot.slack.client import slack_workspace_id
from sqlalchemy import update
from sqlmodel import Session, select


class OpsgenieAPI:
    def __init__(self):
        self.conf = opsgenie_sdk.configuration.Configuration()

        if settings.integrations.atlassian.opsgenie.team:
            key = settings.ATLASSIAN_OPSGENIE_API_TEAM_INTEGRATION_KEY
        else:
            key = settings.ATLASSIAN_OPSGENIE_API_KEY

        self.conf.api_key["Authorization"] = key

        self.api_client = opsgenie_sdk.api_client.ApiClient(
            configuration=self.conf
        )
        self.alert_api = opsgenie_sdk.AlertApi(api_client=self.api_client)

        self.endpoint = "https://api.opsgenie.com/v2"
        self.headers = {
            "Authorization": "GenieKey " + key,
            "Content-Type": "application/json",
        }
        self.priorities = ["P1", "P2", "P3", "P4", "P5"]

    def create_alert(
        self,
        channel_name: str,
        channel_id: str,
        paging_user: str,
        priority: str,
        responders: list[str],
    ):
        """
        Create an Opsgenie alert

        Parameters:
            channel_name (str): The name of the incident channel
            channel_id (str): The ID of the incident channel
            paging_user (str): The user issuing the pge
            priority (str): The priority of the page
            responders (list[str]): Recipients of the page
        """

        if priority not in self.priorities:
            msg = f"{priority} is not a valid priority - should be one of: {self.priorities}"
            logger.error(msg)

            return msg

        body = opsgenie_sdk.CreateAlertPayload(
            message=f"Slack incident {channel_name} has been started and a page has been issued for assistance.",
            description="An incident has been started in Slack and this team has been paged as a result. "
            + f"You were paged by {paging_user}. Link: https://{slack_workspace_id}.slack.com/archives/{channel_id}",
            responders=[{"name": t, "type": "team"} for t in responders],
            priority=priority,
        )

        try:
            create_response = self.alert_api.create_alert(
                create_alert_payload=body
            )

            return create_response
        except Exception as error:
            logger.error(
                f"Exception when calling Opsgenie:AlertApi->create_alert: {error}"
            )

    def list_teams(self) -> list[str]:
        """
        List Opsgenie teams
        """

        try:
            if not settings.integrations.atlassian.opsgenie.team:
                resp = requests.get(
                    f"{self.endpoint}/teams",
                    headers=self.headers,
                )
                resp.raise_for_status()

                return [t.get("name") for t in resp.json().get("data")]
            else:
                return [settings.integrations.atlassian.opsgenie.team]
        except requests.exceptions.HTTPError as error:
            logger.error(
                f"Exception when calling Opsgenie:teams->list: {error}"
            )

    def list_rotations(self) -> list[dict]:
        """
        List Opsgenie rotations
        """

        try:
            resp = requests.get(
                f"{self.endpoint}/schedules",
                headers=self.headers,
            )
            resp.raise_for_status()

            rotations = []

            for sch in resp.json().get("data"):
                resp = requests.get(
                    f"{self.endpoint}/schedules/{sch.get('id')}/rotations",
                    headers=self.headers,
                )

                for r in resp.json().get("data"):
                    rotations.append(r)

            return rotations
        except requests.exceptions.HTTPError as error:
            logger.error(
                f"Exception when calling Opsgenie:rotations->list: {error}"
            )

    def store_on_call_data(self):
        """
        Parses information from Opsgenie regarding on-call information and stores it
        in the database

        This stores both a comprehensive list of schedule information and a mapping made
        available to the auto page functions
        """

        try:
            record_name = "opsgenie_oc_data"

            with Session(engine) as session:
                # Create the row if it doesn't exist
                if not session.exec(
                    select(ApplicationData).filter(
                        ApplicationData.name == record_name
                    )
                ).first():
                    try:
                        row = ApplicationData(name=record_name)
                        session.add(row)
                        session.commit()
                    except Exception as error:
                        logger.error(
                            f"ApplicationData initial row create failed for {record_name}: {error}"
                        )

                session.exec(
                    update(ApplicationData)
                    .where(ApplicationData.name == record_name)
                    .values(
                        json_data=self.list_rotations(),
                    )
                )
                session.commit()
        except Exception as error:
            logger.error(
                f"ApplicationData row edit failed for {record_name}: {error}"
            )
