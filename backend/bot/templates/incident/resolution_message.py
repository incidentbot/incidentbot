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
                        "text": "This incident has been marked as resolved.",
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
                                "text": "Archive Channel",
                            },
                            "style": "danger",
                            "action_id": "incident.archive_incident_channel",
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
