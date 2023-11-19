import config

from typing import Dict


def return_new_statuspage_incident_message(channel_id: str) -> Dict[str, str]:
    """Posts a message in the incident channel prompting for the creation of a Statuspage incident
    Args:
        channel_id: the channel to post the message to
        info: Dict[str, str] as returned by the StatuspageIncident class info method
    """
    return {
        "channel": channel_id,
        "blocks": [
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
                    "text": "To start a Statuspage incident, use the prompt here. "
                    + "In order to use this feature, you'll need to have access rights.",
                },
            },
            {
                "type": "actions",
                "block_id": "statuspage_starter_button",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Start New Incident",
                            "emoji": True,
                        },
                        "value": channel_id,
                        "action_id": "open_statuspage_incident_modal",
                        "style": "primary",
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "action_id": "statuspage.open_statuspage",
                        "text": {
                            "type": "plain_text",
                            "text": "Open Statuspage",
                        },
                        "url": config.active.integrations.get(
                            "statuspage"
                        ).get("url"),
                    },
                ],
            },
            {"type": "divider"},
        ],
    }
