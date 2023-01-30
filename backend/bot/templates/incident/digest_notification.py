import config

from bot.slack.client import slack_workspace_id
from typing import Any, Dict


class IncidentChannelDigestNotification:
    @staticmethod
    def create(
        incident_channel_details: Dict[str, Any],
        conference_bridge: str,
        severity: str,
    ):
        if incident_channel_details.get("is_security_incident"):
            header = ":fire::lock::fire_engine: New Security Incident"
        else:
            header = ":fire::fire_engine: New Incident"
        return {
            "channel": f"{config.active.digest_channel}",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": header,
                    },
                },
                {
                    "block_id": "digest_channel_title",
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": ":mag_right: Description:\n *{}*".format(
                            incident_channel_details.get(
                                "incident_description"
                            )
                        ),
                    },
                },
                {
                    "block_id": "digest_channel_status",
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": ":grey_question: Current Status:\n *Investigating*",
                    },
                },
                {
                    "block_id": "digest_channel_severity",
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f":grey_exclamation: Severity:\n *{severity.upper()}*",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "A new incident has been declared. "
                        + "Please use the buttons here to participate.",
                    },
                },
                {
                    "type": "actions",
                    "block_id": "incchannelbuttons",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Join Incident Channel",
                            },
                            "style": "primary",
                            "url": "https://{}.slack.com/archives/{}".format(
                                slack_workspace_id,
                                incident_channel_details.get("name"),
                            ),
                            "action_id": "incident.join_incident_channel",
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Conference",
                            },
                            "url": conference_bridge,
                            "action_id": "incident.click_conference_bridge_link",
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Incident Guide",
                            },
                            "url": config.active.links.get("incident_guide"),
                            "action_id": "incident.incident_guide_link",
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Incident Postmortems",
                            },
                            "url": config.active.links.get(
                                "incident_postmortems"
                            ),
                            "action_id": "incident.incident_postmortem_link",
                        },
                    ],
                },
            ],
        }

    @staticmethod
    def update(
        incident_id: str,
        incident_description: str,
        is_security_incident: bool,
        status: str,
        severity: str,
        conference_bridge: str,
    ):
        incident_reacji_header = (
            ":fire::lock::fire_engine:"
            if is_security_incident
            else ":fire::fire_engine:"
        )
        incident_type = (
            "Security Incident" if is_security_incident else "Incident"
        )
        if status == "resolved":
            header = f":white_check_mark: Resolved {incident_type} :white_check_mark:"
            message = "This incident has been resolved."
        else:
            header = f"{incident_reacji_header} Ongoing {incident_type}"
            message = "This incident is in progress. Current status is listed here. Join the channel for more information."
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": header,
                },
            },
            {
                "block_id": "digest_channel_title",
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":mag_right: Description:\n *{incident_description}*",
                },
            },
            {
                "block_id": "digest_channel_status",
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":grey_question: Current Status:\n *{status.title()}*",
                },
            },
            {
                "block_id": "digest_channel_severity",
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":grey_exclamation: Severity:\n *{severity.upper()}*",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message,
                },
            },
            {
                "type": "actions",
                "block_id": "incchannelbuttons",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Join Incident Channel",
                        },
                        "style": "primary",
                        "url": f"https://{slack_workspace_id}.slack.com/archives/{incident_id}",
                        "action_id": "incident.join_incident_channel",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Conference",
                        },
                        "url": conference_bridge,
                        "action_id": "incident.click_conference_bridge_link",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Incident Guide",
                        },
                        "url": config.active.links.get("incident_guide"),
                        "action_id": "incident.incident_guide_link",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Incident Postmortems",
                        },
                        "url": config.active.links.get("incident_postmortems"),
                        "action_id": "incident.incident_postmortem_link",
                    },
                ],
            },
        ]
