import config


class IncidentUpdate:
    @staticmethod
    def role(channel: str, role: str, user: str):
        return {
            "channel": channel,
            "blocks": [
                {"type": "divider"},
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": ":raising_hand: Role Update",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"<@{user}> has been assigned the *{role}* role.",
                    },
                },
                {"type": "divider"},
            ],
        }

    @staticmethod
    def status(channel: str, status: str):
        return {
            "channel": channel,
            "blocks": [
                {"type": "divider"},
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": ":warning: Status Update",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"The incident status has changed to *{status.title()}*.",
                    },
                },
                {"type": "divider"},
            ],
        }

    @staticmethod
    def severity(channel: str, severity: str):
        return {
            "channel": channel,
            "blocks": [
                {"type": "divider"},
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": ":warning: Severity Update",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"The incident severity has changed to *{severity.upper()}*. {config.active.severities.get(severity)}",
                    },
                },
                {"type": "divider"},
            ],
        }

    @staticmethod
    def public_update(
        incident_id: str, impacted_resources: str, message: str, timestamp: str
    ):
        header = ":warning: Incident Update"
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": header,
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Incident:*\n <#{incident_id}>",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Posted At:*\n {timestamp}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Impacted Resources:*\n {impacted_resources}",
                    },
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Current Status*\n {message}",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "This update was provided by the incident management team in response to an ongoing incident.",
                    }
                ],
            },
        ]
