import config
import json
import requests

from bot.audit import log
from bot.models.incident import (
    db_read_incident,
    db_update_incident_sp_data_col,
    db_update_incident_sp_id_col,
    db_update_incident_sp_ts_col,
)
from bot.slack.client import slack_web_client
from logger import logger
from typing import Any, Dict, List

api = "https://api.statuspage.io/v1/"
api_key = config.statuspage_api_key
page_id = config.statuspage_page_id

headers = {
    "Authorization": f"OAuth {api_key}",
}


class StatuspageIncident:
    """Instantiates a Statuspage incident"""

    def __init__(self, channel_id: str, request_data: Dict[str, str]):
        """Creates a Statuspage incident"""
        self.request_data = request_data
        self.channel_id = channel_id

        # Construct payload for request to API
        payload = {
            "incident": {
                "name": self.request_data["name"],
                "status": self.request_data["status"],
                "body": self.request_data["body"],
                "impact_override": self.request_data["impact"],
                "components": self.request_data["components"],
            }
        }
        resp = requests.post(
            f"{api}/pages/{page_id}/incidents", headers=headers, json=payload
        )
        json_response = json.loads(resp.text)
        incident_name = json_response["name"]
        logger.info(f"Created Statuspage incident: {incident_name}")
        self.info = json.loads(resp.text)

        # Update incident record with Statuspage management message timestamp
        try:
            db_update_incident_sp_id_col(
                channel_id=self.channel_id,
                sp_incident_id=self.info["id"],
            )
        except Exception as error:
            logger.fatal(f"Error adding Statuspage incident ID: {error}")

        # Update incident record with Statuspage data
        try:
            db_update_incident_sp_data_col(
                channel_id=self.channel_id,
                sp_incident_data=self.info,
            )
        except Exception as error:
            logger.error(
                f"Error updating incident with Statuspage data: {error}"
            )

    @property
    def details(self) -> Dict[str, str]:
        return self.info


class StatuspageIncidentUpdate:
    """Updates a Statuspage incident"""

    @staticmethod
    def update(channel_id: str, status: str, message: str):
        """Update Statuspage incident"""
        incident_data = db_read_incident(channel_id=channel_id)
        sp_incident_data = incident_data.sp_incident_data

        sp_components = StatuspageComponents()
        # Update incident
        # If resolved, return components to operational
        # If not resolved, preserve original statuses
        components = None
        incident_updates = sp_incident_data.get("incident_updates")
        if status == "resolved":
            components = sp_components.formatted_components_update(
                sp_components.list_of_names, "operational"
            )
        elif incident_updates:
            affected_components = incident_updates[-1:][0].get(
                "affected_components", []
            )
            if affected_components:
                components = {
                    obj.get("code"): obj.get("new_status")
                    for obj in sp_incident_data.get("incident_updates", [])[
                        -1:
                    ][0].get("affected_components")
                }
        update_data = {
            "id": incident_data.sp_incident_id,
            "body": message,
            "status": status,
            "components": components,
        }

        payload = {
            "incident": {
                "status": update_data.get("status"),
                "body": update_data.get("body"),
                "components": update_data.get("components"),
            }
        }

        # Patch the incident
        resp = requests.patch(
            "{}/pages/{}/incidents/{}".format(
                api, page_id, update_data.get("id")
            ),
            headers=headers,
            json=payload,
        )

        updated_incident_data = json.loads(resp.text)

        # Update Statuspage incident data for incident
        try:
            db_update_incident_sp_data_col(
                channel_id=incident_data.channel_id,
                sp_incident_data=updated_incident_data,
            )
        except Exception as error:
            logger.fatal(
                f"Error updating incident record for {incident_data.channel_name}: {error}"
            )

        # Update the message in the channel
        result = slack_web_client.chat_update(
            channel=incident_data.channel_id,
            ts=incident_data.sp_message_ts,
            text=f"Statuspage incident updated to {status}.",
            blocks=StatuspageIncidentUpdate.update_management_message(
                incident_data.channel_id
            ),
        )

        # Update timestamp in database entry to the newest one
        try:
            db_update_incident_sp_ts_col(
                channel_id=incident_data.channel_id,
                ts=result["ts"],
            )
        except Exception as error:
            logger.fatal(
                f"Error updating incident record for {incident_data.channel_name}: {error}"
            )

    @staticmethod
    def update_management_message(channel_id: str) -> List[Dict[str, Any]]:
        """Formats the Statuspage management message for updates"""
        incident_data = db_read_incident(channel_id=channel_id)
        sp_incident_data = incident_data.sp_incident_data

        base_blocks = [
            {"type": "divider"},
            {
                "type": "image",
                "image_url": config.sp_logo_url,
                "alt_text": "statuspage",
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "A Statuspage incident has been created. Use the options here to manage it.",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Name*: {}\n*Status*: {}\n".format(
                        sp_incident_data.get("name"),
                        sp_incident_data.get("status").title(),
                    ),
                },
            },
            {"type": "divider"},
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":alarm_clock: Statuspage Incident Updates",
                },
            },
        ]
        for update in sp_incident_data.get("incident_updates"):
            base_blocks.extend(
                [
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Body:* {}".format(
                                    update.get("body")
                                ),
                            },
                            {
                                "type": "mrkdwn",
                                "text": "*Status:* {}".format(
                                    update.get("status").title()
                                ),
                            },
                            {
                                "type": "mrkdwn",
                                "text": "*Updated At:* {}".format(
                                    update.get("updated_at")
                                ),
                            },
                        ],
                    },
                    {"type": "divider"},
                ]
            )
        base_blocks.extend(
            [
                {
                    "type": "actions",
                    "block_id": "statuspage_update_button",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Update Incident",
                                "emoji": True,
                            },
                            "value": channel_id,
                            "action_id": "open_statuspage_incident_update_modal",
                            "style": "primary",
                        },
                        {
                            "type": "button",
                            "style": "primary",
                            "text": {
                                "type": "plain_text",
                                "text": "View Incident",
                            },
                            "action_id": "statuspage.view_incident",
                            "url": sp_incident_data.get("shortlink"),
                        },
                        {
                            "type": "button",
                            "style": "primary",
                            "text": {
                                "type": "plain_text",
                                "text": "Open Statuspage",
                            },
                            "action_id": "statuspage.open_statuspage",
                            "url": config.active.integrations.get(
                                "statuspage"
                            ).get("url"),
                        },
                    ],
                },
                {"type": "divider"},
            ]
        )
        return base_blocks


class StatuspageComponents:
    """Return and use Statuspage components"""

    def __init__(self) -> List[Dict[str, str]]:
        """Retrieves a list of components from the Statuspage API
        for the supplied page ID

        Returns Dict[str, str] containing the formatted message
        to be sent to Slack
        """
        components_raw = requests.get(
            f"{api}/pages/{page_id}/components",
            headers=headers,
        )
        self.resp = json.loads(components_raw.text)

    @property
    def list_of_names(self) -> List[str]:
        return [c["name"] for c in self.resp]

    @property
    def list_of_dict_name_ids(self) -> List[Dict[str, str]]:
        return [{c["name"]: c["id"]} for c in self.resp]

    def formatted_components_update(
        self, selected_components: List[str], status: str
    ) -> List[str]:
        formatted_json = {}
        for dict in self.list_of_dict_name_ids:
            for sc in selected_components:
                if sc in dict:
                    for _, value in dict.items():
                        formatted_json[value] = status
        return formatted_json


class StatuspageObjects:
    """Return and use Statuspage objects"""

    def __init__(self) -> List[Dict[str, str]]:
        """Retrieves a list of components from the Statuspage API
        for the supplied page ID

        Returns Dict[str, str] containing the formatted message
        to be sent to Slack
        """
        incidents_raw = requests.get(
            f"{api}/pages/{page_id}/incidents",
            headers=headers,
        )
        self.open_incidents = json.loads(incidents_raw.text)

    @property
    def open_incidents(self) -> Dict[str, str]:
        return self.open_incidents
