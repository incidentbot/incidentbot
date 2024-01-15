import config


class IncidentResolutionMessage:
    @staticmethod
    def create(channel: str):
        button_el = [
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
        ]

        if config.active.links:
            for l in config.active.links:
                button_el.extend(
                    [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": l.get("title"),
                            },
                            "url": l.get("url"),
                            "action_id": f"incident.clicked_link_{l.get('title').lower().replace(' ', '_')}",
                        },
                    ]
                )

        blocks = [
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
                "elements": button_el,
            },
            {"type": "divider"},
        ]

        return {
            "channel": channel,
            "blocks": blocks,
        }
