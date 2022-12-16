import re

from bot.incident.action_parameters import ActionParameters
from bot.incident.incident import Incident
from bot.incident.templates import (
    build_digest_notification,
    build_incident_channel_boilerplate,
    build_post_resolution_message,
    build_public_status_update,
    build_role_update,
    build_severity_update,
    build_status_update,
    build_updated_digest_message,
    build_user_role_notification,
)
from bot.shared import tools

placeholder_token = "verification-token"
placeholder_team_id = "T111"
placeholder_enterprise_id = "E111"
placeholder_app_id = "A111"


class TestIncidentManagement:
    def test_action_parameters(self):
        ap = ActionParameters(
            payload={
                "type": "block_actions",
                "team": {"id": "T9TK3CUKW", "domain": "example"},
                "user": {
                    "id": "UA8RXUSPL",
                    "name": "sample",
                    "team_id": "T9TK3CUKW",
                },
                "api_app_id": "AABA1ABCD",
                "token": "9s8d9as89d8as9d8as989",
                "container": {
                    "type": "message_attachment",
                    "message_ts": "1548261231.000200",
                    "attachment_id": 1,
                    "channel_id": "CBR2V3XEX",
                    "is_ephemeral": False,
                    "is_app_unfurl": False,
                },
                "trigger_id": "12321423423.333649436676.d8c1bb837935619ccad0f624c448ffb3",
                "channel": {"id": "CBR2V3XEX", "name": "mock"},
                "message": {
                    "bot_id": "BAH5CA16Z",
                    "type": "message",
                    "text": "This content can't be displayed.",
                    "user": "UAJ2RU415",
                    "ts": "1548261231.000200",
                },
                "response_url": "https://hooks.slack.com/actions/AABA1ABCD/1232321423432/D09sSasdasdAS9091209",
                "actions": [
                    {
                        "action_id": "sample-action",
                        "block_id": "=qXel",
                        "text": {
                            "type": "plain_text",
                            "text": "View",
                            "emoji": True,
                        },
                        "value": "click_me_123",
                        "type": "button",
                        "action_ts": "1548426417.840180",
                    }
                ],
            }
        )

        assert ap.actions() == {
            "action_id": "sample-action",
            "block_id": "=qXel",
            "text": {"type": "plain_text", "text": "View", "emoji": True},
            "value": "click_me_123",
            "type": "button",
            "action_ts": "1548426417.840180",
        }

        assert ap.channel_details() == {"id": "CBR2V3XEX", "name": "mock"}

        assert ap.message_details() == {
            "bot_id": "BAH5CA16Z",
            "type": "message",
            "text": "This content can't be displayed.",
            "user": "UAJ2RU415",
            "ts": "1548261231.000200",
        }

        assert ap.user_details() == {
            "id": "UA8RXUSPL",
            "name": "sample",
            "team_id": "T9TK3CUKW",
        }

        assert ap.parameters() == {
            "action_id": "sample-action",
            "channel_id": "CBR2V3XEX",
            "channel_name": "mock",
            "timestamp": "1548261231.000200",
            "user": "sample",
            "user_id": "UA8RXUSPL",
        }

    def test_incident_instantiate(self):
        inc = Incident(
            request_parameters={
                "channel": "CBR2V3XEX",
                "incident_description": "something has broken",
                "user": "sample-incident-creator-user",
                "severity": "sev4",
                "created_from_web": False,
                "is_security_incident": False,
            }
        )
        assert isinstance(inc, Incident)

        assert re.search("^inc.*something-has-broken$", inc.channel_name)

        assert inc.conference_bridge == "https://zoom.us"

    def test_incident_channel_name_create(self):
        inc = Incident(
            request_parameters={
                "channel": "CBR2V3XEX",
                "incident_description": "unallowed ch@racter check!",
                "user": "sample-incident-creator-user",
                "severity": "sev4",
                "created_from_web": False,
                "is_security_incident": False,
            }
        )

        assert re.search("^inc.*unallowed-chracter-check$", inc.channel_name)

    def test_incident_build_digest_notification(self):
        assert build_digest_notification(
            created_channel_details={
                "incident_description": "mock",
                "id": "CBR2V3XEX",
                "name": "mock",
                "is_security_incident": False,
            },
            severity="sev4",
            conference_bridge="mock",
        ) == {
            "channel": "incidents",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": ":fire::fire_engine: New Incident",
                    },
                },
                {
                    "block_id": "digest_channel_title",
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": ":mag_right: Description:\n *mock*",
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
                        "text": ":grey_exclamation: Severity:\n *SEV4*",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "A new incident has been declared. Please use the buttons here to participate.",
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
                            "url": "https://test.slack.com/archives/mock",
                            "action_id": "incident.join_incident_channel",
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Conference",
                            },
                            "url": "mock",
                            "action_id": "incident.click_conference_bridge_link",
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Incident Guide",
                            },
                            "url": "https://changeme.com",
                            "action_id": "incident.incident_guide_link",
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Incident Postmortems",
                            },
                            "url": "https://changeme.com",
                            "action_id": "incident.incident_postmortem_link",
                        },
                    ],
                },
            ],
        }

    def test_build_incident_channel_boilerplate(self):
        assert build_incident_channel_boilerplate(
            created_channel_details={"id": "CBR2V3XEX", "name": "mock"},
            severity="sev4",
        ) == {
            "blocks": [
                {"type": "divider"},
                {
                    "block_id": "header",
                    "text": {
                        "text": "We're in an incident - now what?",
                        "type": "plain_text",
                    },
                    "type": "header",
                },
                {
                    "block_id": "header_info_1",
                    "text": {
                        "text": "Incident Commander should be claimed or "
                        "assigned first. The other roles should then be "
                        "claimed or assigned.",
                        "type": "mrkdwn",
                    },
                    "type": "section",
                },
                {
                    "block_id": "header_info_2",
                    "text": {
                        "text": "The Incident Commander should set the severity "
                        "of this incident immediately. If the severity "
                        "changes, please update it accordingly.",
                        "type": "mrkdwn",
                    },
                    "type": "section",
                },
                {
                    "block_id": "header_info_3",
                    "text": {
                        "text": "The incident starts out in *investigating* "
                        "mode. As the incident progresses, it can be "
                        "moved through statuses until it is resolved. An "
                        "explanation of statuses is available in our "
                        "incident guide linked below.",
                        "type": "mrkdwn",
                    },
                    "type": "section",
                },
                {"type": "divider"},
                {
                    "accessory": {
                        "action_id": "incident.set_incident_status",
                        "options": [
                            {
                                "text": {
                                    "emoji": True,
                                    "text": "Investigating",
                                    "type": "plain_text",
                                },
                                "value": "investigating",
                            },
                            {
                                "text": {
                                    "emoji": True,
                                    "text": "Identified",
                                    "type": "plain_text",
                                },
                                "value": "identified",
                            },
                            {
                                "text": {
                                    "emoji": True,
                                    "text": "Monitoring",
                                    "type": "plain_text",
                                },
                                "value": "monitoring",
                            },
                            {
                                "text": {
                                    "emoji": True,
                                    "text": "Resolved",
                                    "type": "plain_text",
                                },
                                "value": "resolved",
                            },
                        ],
                        "placeholder": {
                            "emoji": True,
                            "text": "Investigating",
                            "type": "plain_text",
                        },
                        "type": "static_select",
                    },
                    "block_id": "status",
                    "text": {"text": "*Current Status:*", "type": "mrkdwn"},
                    "type": "section",
                },
                {
                    "accessory": {
                        "action_id": "incident.set_severity",
                        "options": [
                            {
                                "text": {
                                    "emoji": True,
                                    "text": "SEV1",
                                    "type": "plain_text",
                                },
                                "value": "sev1",
                            },
                            {
                                "text": {
                                    "emoji": True,
                                    "text": "SEV2",
                                    "type": "plain_text",
                                },
                                "value": "sev2",
                            },
                            {
                                "text": {
                                    "emoji": True,
                                    "text": "SEV3",
                                    "type": "plain_text",
                                },
                                "value": "sev3",
                            },
                            {
                                "text": {
                                    "emoji": True,
                                    "text": "SEV4",
                                    "type": "plain_text",
                                },
                                "value": "sev4",
                            },
                        ],
                        "placeholder": {
                            "emoji": True,
                            "text": "SEV4",
                            "type": "plain_text",
                        },
                        "type": "static_select",
                    },
                    "block_id": "severity",
                    "text": {"text": "*Severity:*", "type": "mrkdwn"},
                    "type": "section",
                },
                {"type": "divider"},
                {
                    "block_id": "role_incident_commander",
                    "text": {
                        "text": "*Incident Commander*:\n" " _none_",
                        "type": "mrkdwn",
                    },
                    "type": "section",
                },
                {
                    "accessory": {
                        "action_id": "incident.claim_role",
                        "text": {
                            "emoji": True,
                            "text": "Claim",
                            "type": "plain_text",
                        },
                        "type": "button",
                        "value": "incident_commander",
                    },
                    "block_id": "claim_incident_commander",
                    "text": {
                        "emoji": True,
                        "text": "Claim Role",
                        "type": "plain_text",
                    },
                    "type": "section",
                },
                {
                    "accessory": {
                        "action_id": "incident.assign_role",
                        "placeholder": {
                            "text": "Select a user...",
                            "type": "plain_text",
                        },
                        "type": "users_select",
                    },
                    "block_id": "assign_incident_commander",
                    "text": {
                        "emoji": True,
                        "text": "Assign Role",
                        "type": "plain_text",
                    },
                    "type": "section",
                },
                {"type": "divider"},
                {
                    "block_id": "role_technical_lead",
                    "text": {
                        "text": "*Technical Lead*:\n" " _none_",
                        "type": "mrkdwn",
                    },
                    "type": "section",
                },
                {
                    "accessory": {
                        "action_id": "incident.claim_role",
                        "text": {
                            "emoji": True,
                            "text": "Claim",
                            "type": "plain_text",
                        },
                        "type": "button",
                        "value": "technical_lead",
                    },
                    "block_id": "claim_technical_lead",
                    "text": {
                        "emoji": True,
                        "text": "Claim Role",
                        "type": "plain_text",
                    },
                    "type": "section",
                },
                {
                    "accessory": {
                        "action_id": "incident.assign_role",
                        "placeholder": {
                            "text": "Select a user...",
                            "type": "plain_text",
                        },
                        "type": "users_select",
                    },
                    "block_id": "assign_technical_lead",
                    "text": {
                        "emoji": True,
                        "text": "Assign Role",
                        "type": "plain_text",
                    },
                    "type": "section",
                },
                {"type": "divider"},
                {
                    "block_id": "role_communications_liaison",
                    "text": {
                        "text": "*Communications Liaison*:\n" " _none_",
                        "type": "mrkdwn",
                    },
                    "type": "section",
                },
                {
                    "accessory": {
                        "action_id": "incident.claim_role",
                        "text": {
                            "emoji": True,
                            "text": "Claim",
                            "type": "plain_text",
                        },
                        "type": "button",
                        "value": "communications_liaison",
                    },
                    "block_id": "claim_communications_liaison",
                    "text": {
                        "emoji": True,
                        "text": "Claim Role",
                        "type": "plain_text",
                    },
                    "type": "section",
                },
                {
                    "accessory": {
                        "action_id": "incident.assign_role",
                        "placeholder": {
                            "text": "Select a user...",
                            "type": "plain_text",
                        },
                        "type": "users_select",
                    },
                    "block_id": "assign_communications_liaison",
                    "text": {
                        "emoji": True,
                        "text": "Assign Role",
                        "type": "plain_text",
                    },
                    "type": "section",
                },
                {"type": "divider"},
                {
                    "block_id": "help_buttons",
                    "elements": [
                        {
                            "action_id": "incident.incident_guide_link",
                            "text": {
                                "text": "Incident Guide",
                                "type": "plain_text",
                            },
                            "type": "button",
                            "url": "https://changeme.com",
                        },
                        {
                            "action_id": "incident.incident_postmortem_link",
                            "text": {
                                "text": "Incident Postmortems",
                                "type": "plain_text",
                            },
                            "type": "button",
                            "url": "https://changeme.com",
                        },
                    ],
                    "type": "actions",
                },
                {"type": "divider"},
                {
                    "block_id": "resources",
                    "text": {
                        "text": "*Resources*\n"
                        " <https://app.datadoghq.com/apm/home|Datadog>",
                        "type": "mrkdwn",
                    },
                    "type": "section",
                },
                {"type": "divider"},
            ],
            "channel": "CBR2V3XEX",
        }

    def test_build_post_resolution_message(self):
        assert build_post_resolution_message(
            channel="mock", status="resolved"
        ) == {
            "blocks": [
                {"type": "divider"},
                {
                    "text": {
                        "text": ":white_check_mark: Incident Resolved",
                        "type": "plain_text",
                    },
                    "type": "header",
                },
                {
                    "text": {
                        "text": "This incident has been marked as resolved. The "
                        "Incident Commander and the Technical Lead will "
                        "be invited to an additional channel to discuss "
                        "the RCA. Please use that channel to coordinate "
                        "with others as needed. Remember to export the "
                        "chat log for this incident below so it can be "
                        "referenced in the RCA.",
                        "type": "mrkdwn",
                    },
                    "type": "section",
                },
                {
                    "block_id": "resolution_buttons",
                    "elements": [
                        {
                            "action_id": "incident.export_chat_logs",
                            "style": "primary",
                            "text": {
                                "text": "Export Chat Logs",
                                "type": "plain_text",
                            },
                            "type": "button",
                        },
                        {
                            "text": {
                                "text": "Incident Guide",
                                "type": "plain_text",
                            },
                            "type": "button",
                            "url": "https://changeme.com",
                        },
                        {
                            "text": {
                                "text": "Incident Postmortems",
                                "type": "plain_text",
                            },
                            "type": "button",
                            "url": "https://changeme.com",
                        },
                    ],
                    "type": "actions",
                },
                {"type": "divider"},
            ],
            "channel": "mock",
        }

    def test_build_role_update(self):
        role = "Incident Commander"
        assert build_role_update(
            channel="mock", role=role, user="sample-user"
        ) == {
            "blocks": [
                {"type": "divider"},
                {
                    "text": {
                        "text": ":raising_hand: Role Update",
                        "type": "plain_text",
                    },
                    "type": "header",
                },
                {
                    "text": {
                        "text": f"<@sample-user> has been assigned the *{role}* role.",
                        "type": "mrkdwn",
                    },
                    "type": "section",
                },
                {"type": "divider"},
            ],
            "channel": "mock",
        }

    def test_build_status_update(self):
        status = "monitoring"
        assert build_status_update(channel="mock", status=status) == {
            "blocks": [
                {"type": "divider"},
                {
                    "text": {
                        "text": ":warning: Status Update",
                        "type": "plain_text",
                    },
                    "type": "header",
                },
                {
                    "text": {
                        "text": f"The incident status has changed to *{status.title()}*.",
                        "type": "mrkdwn",
                    },
                    "type": "section",
                },
                {"type": "divider"},
            ],
            "channel": "mock",
        }

    def test_build_updated_digest_message(self):
        status = "identified"
        severity = "sev2"
        is_security_incident = False
        assert build_updated_digest_message(
            incident_id="mock",
            incident_description="mock",
            status=status,
            severity=severity,
            is_security_incident=is_security_incident,
            conference_bridge="mock",
        ) == {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": ":fire::fire_engine: Ongoing Incident",
                    },
                },
                {
                    "block_id": "digest_channel_title",
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": ":mag_right: Description:\n *mock*",
                    },
                },
                {
                    "block_id": "digest_channel_status",
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": ":grey_question: Current Status:\n *Identified*",
                    },
                },
                {
                    "block_id": "digest_channel_severity",
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": ":grey_exclamation: Severity:\n *SEV2*",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "This incident is in progress. Current status is listed here. Join the channel for more information.",
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
                            "url": "https://test.slack.com/archives/mock",
                            "action_id": "incident.join_incident_channel",
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Conference",
                            },
                            "url": "mock",
                            "action_id": "incident.click_conference_bridge_link",
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Incident Guide",
                            },
                            "url": "https://changeme.com",
                            "action_id": "incident.incident_guide_link",
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Incident Postmortems",
                            },
                            "url": "https://changeme.com",
                            "action_id": "incident.incident_postmortem_link",
                        },
                    ],
                },
            ]
        }

    def test_build_public_status_update(self):
        timestamp = tools.fetch_timestamp()
        assert build_public_status_update(
            incident_id="mock",
            impacted_resources="api",
            message="foobar",
            timestamp=timestamp,
        ) == [
            {
                "text": {
                    "text": ":warning: Incident Update",
                    "type": "plain_text",
                },
                "type": "header",
            },
            {
                "fields": [
                    {"text": "*Incident:*\n <#mock>", "type": "mrkdwn"},
                    {
                        "text": f"*Posted At:*\n {timestamp}",
                        "type": "mrkdwn",
                    },
                    {"text": "*Impacted Resources:*\n api", "type": "mrkdwn"},
                ],
                "type": "section",
            },
            {
                "text": {
                    "text": "*Current Status*\n foobar",
                    "type": "mrkdwn",
                },
                "type": "section",
            },
            {
                "elements": [
                    {
                        "text": "This update was provided by the incident management team in response to an ongoing incident.",
                        "type": "mrkdwn",
                    }
                ],
                "type": "context",
            },
        ]

    # This needs to mock the client.
    # def test_incident_create(self):
    #     request_parameters = {
    #         "channel": "mock",
    #         "incident_description": "test incident",
    #         "user": "sample-user",
    #         "token": placeholder_token,
    #         "created_from_web": False,
    #     }
    #     resp = create_incident(request_parameters, internal=True)
    #
    #     assert resp == "ok"
