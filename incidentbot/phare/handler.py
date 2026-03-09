import requests

from datetime import datetime, timezone
from incidentbot.configuration.settings import settings
from incidentbot.logging import logger
from incidentbot.models.database import engine, PhareIncidentRecord
from incidentbot.models.incident import IncidentDatabaseInterface
from incidentbot.slack.client import slack_web_client
from sqlmodel import Session, select
from typing import Any

api = "https://api.phare.io"


def _headers() -> dict:
    h = {"Authorization": f"Bearer {settings.PHARE_API_KEY}"}
    if settings.PHARE_PROJECT_ID:
        h["X-Phare-Project-Id"] = str(settings.PHARE_PROJECT_ID)
    return h


class PhareMonitors:
    """
    Fetches and exposes Phare monitors from the API
    """

    def __init__(self):
        self._monitors = []
        page = 1
        while True:
            resp = requests.get(
                f"{api}/uptime/monitors",
                headers=_headers(),
                params={"page": page, "per_page": 100},
            )
            resp.raise_for_status()
            body = resp.json()
            self._monitors.extend(body.get("data", []))
            links = body.get("links", {})
            if not links.get("next"):
                break
            page += 1

    @property
    def list_of_names(self) -> list[str]:
        return [m["name"] for m in self._monitors]

    @property
    def list_of_dict_name_ids(self) -> list[dict[str, int]]:
        return [{m["name"]: m["id"]} for m in self._monitors]


class PhareIncident:
    """
    Instantiates a Phare incident
    """

    def __init__(self, request_data: dict):
        self.request_data = request_data
        self.payload = {
            "title": self.request_data["title"],
            "description": self.request_data.get("description", ""),
            "impact": self.request_data.get("impact", "operational"),
            "monitor_ids": self.request_data.get("monitor_ids", []),
        }

    def start(self) -> str | None:
        """
        Create the Phare incident and store a record in the DB
        """

        channel_id = self.request_data["channel_id"]

        # Find the ts of the Phare prompt message
        message_ts = None
        result = slack_web_client.conversations_history(
            channel=channel_id,
            inclusive=True,
        )
        for message in result.get("messages", []):
            if message.get("text") == "Phare prompt has been posted to an incident.":
                message_ts = message.get("ts")

        try:
            resp = requests.post(
                f"{api}/uptime/incidents",
                headers=_headers(),
                json=self.payload,
            )
            resp.raise_for_status()
            self.info = resp.json()
            logger.info(f"Created Phare incident: {self.info.get('title')}")

            incident_data = IncidentDatabaseInterface.get_one(channel_id=channel_id)
        except Exception as error:
            logger.error(f"Error during Phare incident creation: {error}")
            return None

        try:
            record = PhareIncidentRecord(
                channel_id=channel_id,
                message_ts=message_ts,
                name=self.info.get("title"),
                parent=incident_data.id,
                state=self.info.get("state", "investigating"),
                updated_at=datetime.now(tz=timezone.utc),
                updates=[],
                upstream_id=self.info.get("id"),
                url=self.info.get("url"),
            )

            with Session(engine) as session:
                session.add(record)
                session.commit()

            return message_ts
        except Exception as error:
            logger.error(f"Error during Phare incident record creation: {error}")
            return None

    @property
    def details(self) -> dict:
        return self.info


class PhareIncidentUpdate:
    """
    Updates a Phare incident
    """

    @staticmethod
    def update(channel_id: str, content: str, state: str):
        """
        Update or recover a Phare incident
        """

        incident_data = IncidentDatabaseInterface.get_one(channel_id=channel_id)

        with Session(engine) as session:
            record = session.exec(
                select(PhareIncidentRecord).filter(
                    PhareIncidentRecord.parent == incident_data.id
                )
            ).one()

            try:
                if state == "resolved":
                    resp = requests.post(
                        f"{api}/uptime/incidents/{record.upstream_id}/recover",
                        headers=_headers(),
                    )
                    resp.raise_for_status()
                else:
                    resp = requests.post(
                        f"{api}/uptime/incidents/{record.upstream_id}/updates",
                        headers=_headers(),
                        json={"state": state, "content": content},
                    )
                    resp.raise_for_status()
                    updates = list(record.updates or [])
                    updates.append(
                        {
                            "content": content,
                            "state": state,
                            "time": datetime.now(tz=timezone.utc).isoformat(),
                        }
                    )
                    record.updates = updates
            except Exception as error:
                logger.error(f"Error updating Phare incident: {error}")
                return

            record.state = state
            record.updated_at = datetime.now(tz=timezone.utc)

            session.add(record)
            session.commit()

            try:
                slack_web_client.chat_update(
                    channel=incident_data.channel_id,
                    ts=record.message_ts,
                    text=f"Phare incident updated to {state}.",
                    blocks=PhareIncidentUpdate.update_management_message(
                        incident_data.channel_id
                    ),
                )
            except Exception as error:
                logger.error(
                    f"Error updating Phare message for {incident_data.channel_name}: {error}"
                )

    @staticmethod
    def update_management_message(channel_id: str) -> list[dict[str, Any]]:
        """
        Formats the Phare management message for updates
        """

        incident_data = IncidentDatabaseInterface.get_one(channel_id=channel_id)

        with Session(engine) as session:
            record = session.exec(
                select(PhareIncidentRecord).filter(
                    PhareIncidentRecord.parent == incident_data.id
                )
            ).one()

            blocks = [
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Phare* - A Phare incident has been created. Use the options here to manage it.",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Name*: {}\n*State*: {}\n".format(
                            record.name,
                            record.state.title() if record.state else "",
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

            for update in record.updates or []:
                blocks.extend(
                    [
                        {
                            "type": "section",
                            "fields": [
                                {
                                    "type": "mrkdwn",
                                    "text": "*Message:* {}".format(
                                        update.get("content")
                                    ),
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": "*State:* {}".format(
                                        update.get("state", "").title()
                                    ),
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": "*Time:* {}".format(
                                        update.get("time")
                                    ),
                                },
                            ],
                        },
                        {"type": "divider"},
                    ]
                )

            action_elements = [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Update Incident",
                        "emoji": True,
                    },
                    "value": channel_id,
                    "action_id": "phare_incident_update_modal",
                    "style": "primary",
                },
            ]

            if record.url:
                action_elements.append(
                    {
                        "type": "button",
                        "style": "primary",
                        "text": {
                            "type": "plain_text",
                            "text": "View Incident",
                        },
                        "action_id": "phare.view_incident",
                        "url": record.url,
                    }
                )

            action_elements.append(
                {
                    "type": "button",
                    "style": "primary",
                    "text": {
                        "type": "plain_text",
                        "text": "Open Phare",
                    },
                    "action_id": "phare.open",
                    "url": settings.integrations.phare.url,
                }
            )

            blocks.extend(
                [
                    {
                        "type": "actions",
                        "block_id": "phare_update_button",
                        "elements": action_elements,
                    },
                    {"type": "divider"},
                ]
            )

            return blocks
