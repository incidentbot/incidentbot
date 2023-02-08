import config

from typing import Any, Dict


class IncidentChannelBoilerplateMessage:
    @staticmethod
    def create(incident_channel_details: Dict[str, Any], severity: str):
        blocks = [
            {"type": "divider"},
            {
                "block_id": "header",
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "We're in an incident - now what?",
                },
            },
            {
                "block_id": "header_info_1",
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Incident Commander should be claimed or "
                    + "assigned first. Any other roles should then be "
                    + "claimed or assigned.",
                },
            },
            {
                "block_id": "header_info_2",
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "The Incident Commander should verify the severity "
                    + "of this incident immediately. If the severity changes,"
                    + " please update it accordingly.",
                },
            },
            {
                "block_id": "header_info_3",
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "The incident starts out in *investigating* mode."
                    + " As the incident progresses, it can be moved through "
                    + "statuses until it is resolved.",
                },
            },
            {"type": "divider"},
            {
                "block_id": "status",
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Current Status:*"},
                "accessory": {
                    "type": "static_select",
                    "action_id": "incident.set_status",
                    "placeholder": {
                        "type": "plain_text",
                        "text": config.active.statuses[0].title(),
                        "emoji": True,
                    },
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": st.title(),
                                "emoji": True,
                            },
                            "value": st,
                        }
                        for st in config.active.statuses
                    ],
                },
            },
            {
                "block_id": "severity",
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Severity:*"},
                "accessory": {
                    "type": "static_select",
                    "action_id": "incident.set_severity",
                    "placeholder": {
                        "type": "plain_text",
                        "text": severity.upper(),
                        "emoji": True,
                    },
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": sev.upper(),
                                "emoji": True,
                            },
                            "value": sev,
                        }
                        for sev, _ in config.active.severities.items()
                    ],
                },
            },
            {"type": "divider"},
        ]
        for role, _ in config.active.roles.items():
            blocks.extend(
                [
                    {
                        "block_id": f"role_{role}",
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*{}*:\n _none_".format(
                                role.title().replace("_", " ")
                            ),
                        },
                    },
                    {
                        "type": "section",
                        "block_id": f"claim_{role}",
                        "text": {
                            "type": "plain_text",
                            "text": "Claim Role",
                            "emoji": True,
                        },
                        "accessory": {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Claim",
                                "emoji": True,
                            },
                            "value": role,
                            "action_id": "incident.claim_role",
                        },
                    },
                    {
                        "type": "section",
                        "block_id": f"assign_{role}",
                        "text": {
                            "type": "plain_text",
                            "text": "Assign Role",
                            "emoji": True,
                        },
                        "accessory": {
                            "action_id": "incident.assign_role",
                            "type": "users_select",
                            "placeholder": {
                                "type": "plain_text",
                                "text": "Select a user...",
                            },
                        },
                    },
                    {"type": "divider"},
                ]
            )
        blocks.extend(
            [
                {
                    "block_id": "help_buttons",
                    "type": "actions",
                    "elements": [
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
                {"type": "divider"},
            ]
        )

        return {
            "channel": incident_channel_details.get("id"),
            "blocks": blocks,
        }
