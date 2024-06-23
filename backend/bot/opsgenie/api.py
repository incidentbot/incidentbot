import config
import opsgenie_sdk
import requests

from bot.models.pg import OperationalData, Session
from bot.utils import utils
from bot.slack.client import slack_workspace_id
from logger import logger
from sqlalchemy import update
from typing import Dict, List

image_url = "https://i.imgur.com/NjiEBCu.png"


class OpsgenieAPI:
    def __init__(self):
        self.conf = opsgenie_sdk.configuration.Configuration()

        if (
            config.active.integrations.get("atlassian")
            .get("opsgenie")
            .get("team")
        ):
            key = config.atlassian_opsgenie_api_team_integration_key
        else:
            key = config.atlassian_opsgenie_api_key

        self.conf.api_key["Authorization"] = key

        self.api_client = opsgenie_sdk.api_client.ApiClient(
            configuration=self.conf
        )
        self.alert_api = opsgenie_sdk.AlertApi(api_client=self.api_client)

        self.endpoint = "https://api.opsgenie.com/v2"
        self.headers = {
            "Authorization": "GenieKey " + config.atlassian_opsgenie_api_key,
            "Content-Type": "application/json",
        }
        self.priorities = ["P1", "P2", "P3", "P4", "P5"]

    def create_alert(
        self,
        channel_name: str,
        channel_id: str,
        paging_user: str,
        priority: str,
        responders: List[str],
    ):
        """Create an Opsgenie alert"""
        if priority not in self.priorities:
            msg = f"{priority} is not a valid priority - should be one of: {self.priorities}"
            logger.error(msg)

            return msg

        body = opsgenie_sdk.CreateAlertPayload(
            message=f"Slack incident {channel_name} has been started and a page has been issued for assistance.",
            description="An incident has been declared in Slack and this team has been paged as a result. "
            + f"You were paged by {paging_user}. Link: https://{slack_workspace_id}.slack.com/archives/{channel_id}",
            responders=[{"name": t, "type": "team"} for t in responders],
            priority=priority,
        )

        try:
            create_response = self.alert_api.create_alert(
                create_alert_payload=body
            )

            return create_response
        except Exception as err:
            logger.error(
                f"Exception when calling Opsgenie:AlertApi->create_alert: {err}"
            )

            raise Exception(err)

    def list_teams(self) -> List[str]:
        """List Opsgenie teams"""
        if (
            not config.active.integrations.get("atlassian")
            .get("opsgenie")
            .get("team")
        ):
            resp = requests.get(
                f"{self.endpoint}/teams",
                headers=self.headers,
            )

            return [t.get("name") for t in resp.json().get("data")]
        else:
            return [
                config.active.integrations.get("atlassian")
                .get("opsgenie")
                .get("team")
            ]

    def list_rotations(self) -> List[Dict]:
        """List Opsgenie rotations"""
        resp = requests.get(
            f"{self.endpoint}/schedules",
            headers=self.headers,
        )

        rotations = []

        for sch in resp.json().get("data"):
            resp = requests.get(
                f"{self.endpoint}/schedules/{sch.get('id')}/rotations",
                headers=self.headers,
            )

            for r in resp.json().get("data"):
                rotations.append(r)

        return rotations

    def store_on_call_data(self):
        """
        Parses information from Opsgenie regarding on-call information and stores it
        in the database

        This stores both a comprehensive list of schedule information and a mapping made
        available to the auto page functions
        """
        # Store all data
        try:
            record_name = "opsgenie_oc_data"

            # Create the row if it doesn't exist
            if (
                not Session.query(OperationalData)
                .filter_by(id=record_name)
                .all()
            ):
                try:
                    row = OperationalData(id=record_name)
                    Session.add(row)
                    Session.commit()
                except Exception as error:
                    logger.error(
                        f"Opdata row create failed for {record_name}: {error}"
                    )
            Session.execute(
                update(OperationalData)
                .where(OperationalData.id == record_name)
                .values(
                    json_data=self.list_rotations(),
                    updated_at=utils.fetch_timestamp(),
                )
            )
            Session.commit()
        except Exception as error:
            logger.error(f"Opdata row edit failed for {record_name}: {error}")
            Session.rollback()
        finally:
            Session.close()
