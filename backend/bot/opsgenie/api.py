import config
import logging
import opsgenie_sdk
import requests

from bot.slack.client import slack_workspace_id
from typing import Dict, List

logger = logging.getLogger("opsgenie")

image_url = "https://i.imgur.com/NjiEBCu.png"


class OpsgenieAPI:
    def __init__(self):
        self.conf = opsgenie_sdk.configuration.Configuration()

        if config.active.integrations.get("atlassian").get("opsgenie").get("team"):
            key = config.atlassian_opsgenie_api_team_integration_key
        else:
            key = config.atlassian_opsgenie_api_key

        self.conf.api_key["Authorization"] = key

        self.api_client = opsgenie_sdk.api_client.ApiClient(configuration=self.conf)
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
            create_response = self.alert_api.create_alert(create_alert_payload=body)

            return create_response
        except Exception as err:
            logger.error(
                f"Exception when calling Opsgenie:AlertApi->create_alert: {err}"
            )

            raise Exception(err)

    def list_teams(self) -> List[str]:
        """List Opsgenie teams"""
        if not config.active.integrations.get("atlassian").get("opsgenie").get("team"):
            resp = requests.get(
                f"{self.endpoint}/teams",
                headers=self.headers,
            )

            return [t.get("name") for t in resp.json().get("data")]
        else:
            return [
                config.active.integrations.get("atlassian").get("opsgenie").get("team")
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
