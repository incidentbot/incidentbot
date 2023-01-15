import config


class IncidentResolutionMessage:
    @staticmethod
    def create(channel: str):
        return {
            "channel": channel,
            "blocks": [
                {"type": "divider"},
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": ":white_check_mark: Incident Resolved",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "This incident has been marked as resolved. The Incident Commander will be invited to an additional channel to discuss the RCA. Please use that channel to coordinate with others as needed. Remember to export the chat log for this incident below so it can be referenced in the RCA.",
                    },
                },
                {
                    "block_id": "resolution_buttons",
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Export Chat Logs",
                            },
                            "style": "primary",
                            "action_id": "incident.export_chat_logs",
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Incident Guide",
                            },
                            "url": config.active.links.get("incident_guide"),
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
                        },
                    ],
                },
                {"type": "divider"},
            ],
        }
