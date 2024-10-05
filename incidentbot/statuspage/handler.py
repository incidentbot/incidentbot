import json
import requests

from incidentbot.configuration.settings import settings, statuspage_logo_url
from incidentbot.logging import logger
from incidentbot.models.database import engine, StatuspageIncidentRecord
from incidentbot.models.incident import IncidentDatabaseInterface
from incidentbot.slack.client import slack_web_client
from sqlmodel import Session, select
from typing import Any

api = "https://api.statuspage.io/v1"
api_key = settings.STATUSPAGE_API_KEY

headers = {
    "Authorization": f"OAuth {api_key}",
}


class StatuspageIncident:
    """
    Instantiates a Statuspage incident
    """

    def __init__(self, channel_id: str, request_data: dict[str, str]):
        self.channel_id = channel_id
        self.request_data = request_data

        # Construct payload for request to API
        self.payload = {
            "incident": {
                "name": self.request_data["name"],
                "status": self.request_data["status"],
                "body": self.request_data["body"],
                "impact_override": self.request_data["impact"],
                "components": self.request_data["components"],
            }
        }

    def start(self) -> str:
        """
        Start the incident
        """

        # Find the ts of the Statuspage prompt message
        message_ts = None
        result = slack_web_client.conversations_history(
            channel=self.channel_id,
            inclusive=True,
        )

        for message in result.get("messages"):
            if (
                message.get("text")
                == "Statuspage prompt has been posted to an incident."
            ):
                message_ts = message.get("ts")

        try:
            resp = requests.post(
                f"{api}/pages/{settings.STATUSPAGE_PAGE_ID}/incidents",
                headers=headers,
                json=self.payload,
            )

            self.info = json.loads(resp.text)

            logger.info(
                "Created Statuspage incident: {}".format(self.info.get("name"))
            )

            incident_data = IncidentDatabaseInterface.get_one(
                channel_id=self.channel_id
            )
        except Exception as error:
            logger.error(f"Error during statuspage incident creation: {error}")

            return

        try:
            record = StatuspageIncidentRecord(
                channel_id=self.channel_id,
                message_ts=message_ts,
                name=self.info.get("name"),
                parent=incident_data.id,
                shortlink=self.info.get("shortlink"),
                status=self.info.get("status"),
                updates=self.info.get("incident_updates"),
                upstream_id=self.info.get("id"),
            )

            with Session(engine) as session:
                session.add(record)
                session.commit()

            return message_ts
        except Exception as error:
            logger.error(
                f"Error during statuspage incident record creation: {error}"
            )

            return

    @property
    def details(self) -> dict[str, str]:
        return self.info


class StatuspageIncidentUpdate:
    """
    Updates a Statuspage incident
    """

    @staticmethod
    def update(channel_id: str, message: str, status: str):
        """
        Update Statuspage incident
        """

        incident_data = IncidentDatabaseInterface.get_one(
            channel_id=channel_id
        )

        with Session(engine) as session:
            record = session.exec(
                select(StatuspageIncidentRecord).filter(
                    StatuspageIncidentRecord.parent == incident_data.id
                )
            ).one()

            sp_components = StatuspageComponents()

            # Update incident
            # If resolved, return components to operational
            # If not resolved, preserve original statuses
            components = None

            if status == "resolved":
                components = sp_components.formatted_components_update(
                    sp_components.list_of_names, "operational"
                )
            else:
                affected_components = record.updates[0].get(
                    "affected_components", []
                )

                if affected_components:
                    components = {
                        obj.get("code"): obj.get("new_status")
                        for obj in affected_components
                    }

            payload = {
                "incident": {
                    "status": status,
                    "body": message,
                    "components": components,
                }
            }

            # Patch the incident
            resp = requests.patch(
                "{}/pages/{}/incidents/{}".format(
                    api, settings.STATUSPAGE_PAGE_ID, record.upstream_id
                ),
                headers=headers,
                json=payload,
            )

            record.status = status
            record.updates = json.loads(resp.text).get("incident_updates")

            session.add(record)
            session.commit()

            try:
                slack_web_client.chat_update(
                    channel=incident_data.channel_id,
                    ts=record.message_ts,
                    text=f"Statuspage incident updated to {status}.",
                    blocks=StatuspageIncidentUpdate.update_management_message(
                        incident_data.channel_id
                    ),
                )
            except Exception as error:
                logger.error(
                    f"Error updating Statuspage message for {incident_data.channel_name}: {error}"
                )

    @staticmethod
    def update_management_message(channel_id: str) -> list[dict[str, Any]]:
        """
        Formats the Statuspage management message for updates
        """

        incident_data = IncidentDatabaseInterface.get_one(
            channel_id=channel_id
        )

        with Session(engine) as session:
            record = session.exec(
                select(StatuspageIncidentRecord).filter(
                    StatuspageIncidentRecord.parent == incident_data.id
                )
            ).one()

            blocks = [
                {"type": "divider"},
                {
                    "type": "image",
                    "image_url": statuspage_logo_url,
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
                            record.name,
                            record.status.title(),
                        ),
                    },
                },
                {"type": "divider"},
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": ":loudspeaker: Updates",
                    },
                },
            ]

            for update in record.updates:
                blocks.extend(
                    [
                        {
                            "type": "section",
                            "fields": [
                                {
                                    "type": "mrkdwn",
                                    "text": "*Message:* {}".format(
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
                                    "text": "*Time:* {}".format(
                                        update.get("updated_at")
                                    ),
                                },
                            ],
                        },
                        {"type": "divider"},
                    ]
                )

            blocks.extend(
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
                                "action_id": "statuspage_incident_update_modal",
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
                                "url": record.shortlink,
                            },
                            {
                                "type": "button",
                                "style": "primary",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Open Statuspage",
                                },
                                "action_id": "statuspage.open",
                                "url": settings.integrations.atlassian.statuspage.url,
                            },
                        ],
                    },
                    {"type": "divider"},
                ]
            )

            return blocks


class StatuspageComponents:
    """
    Return and use Statuspage components
    """

    def __init__(self) -> list[dict[str, str]]:
        """
        Retrieves a list of components from the Statuspage API
        for the supplied page ID

        Returns Dict[str, str] containing the formatted message
        to be sent to Slack
        """

        components_raw = requests.get(
            f"{api}/pages/{settings.STATUSPAGE_PAGE_ID}/components",
            headers=headers,
        )

        self.resp = json.loads(components_raw.text)

    @property
    def list_of_names(self) -> list[str]:

        return [c["name"] for c in self.resp]

    @property
    def list_of_dict_name_ids(self) -> list[dict[str, str]]:

        return [{c["name"]: c["id"]} for c in self.resp]

    def formatted_components_update(
        self, selected_components: list[str], status: str
    ) -> list[str]:
        formatted_json = {}
        for dict in self.list_of_dict_name_ids:
            for sc in selected_components:
                if sc in dict:
                    for _, value in dict.items():
                        formatted_json[value] = status

        return formatted_json


class StatuspageObjects:
    """
    Return and use Statuspage objects
    """

    def __init__(self) -> list[dict[str, str]]:
        """Retrieves a list of components from the Statuspage API
        for the supplied page ID

        Returns Dict[str, str] containing the formatted message
        to be sent to Slack
        """

        incidents_raw = requests.get(
            f"{api}/pages/{settings.STATUSPAGE_PAGE_ID}/incidents",
            headers=headers,
        )
        self.open_incidents = json.loads(incidents_raw.text)

    @property
    def open_incidents(self) -> dict[str, str]:

        return self.open_incidents
