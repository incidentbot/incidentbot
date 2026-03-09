from incidentbot.configuration.settings import settings


def return_new_phare_incident_message(channel_id: str) -> dict:
    """
    Renders content for the Phare prompt message

    Parameters:
        channel_id (str): the ID of the channel to post the message to
    """

    return {
        "channel": channel_id,
        "blocks": [
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Phare* - To start a Phare incident, use the prompt here. "
                    + "In order to use this feature, you'll need to have access rights.",
                },
            },
            {
                "type": "actions",
                "block_id": "phare_starter_button",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Start Phare Incident",
                            "emoji": True,
                        },
                        "value": channel_id,
                        "action_id": "phare_incident_modal",
                        "style": "primary",
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "action_id": "phare.open",
                        "text": {
                            "type": "plain_text",
                            "text": "Open Phare",
                        },
                        "url": settings.integrations.phare.url,
                    },
                ],
            },
            {"type": "divider"},
        ],
    }
