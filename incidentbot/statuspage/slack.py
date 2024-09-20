from incidentbot.configuration.settings import settings, statuspage_logo_url


def return_new_statuspage_incident_message(channel_id: str) -> dict[str, str]:
    """
    Renders content for the Statuspage prompts

    Parameters:
        channel_id (str): the ID of the channel to post the message to
    """

    return {
        "channel": channel_id,
        "blocks": [
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
                            "text": "Start Statuspage Incident",
                            "emoji": True,
                        },
                        "value": channel_id,
                        "action_id": "statuspage_incident_modal",
                        "style": "primary",
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "action_id": "statuspage.open",
                        "text": {
                            "type": "plain_text",
                            "text": "Open Statuspage",
                        },
                        "url": settings.integrations.atlassian.statuspage.url,
                    },
                ],
            },
            {"type": "divider"},
        ],
    }
