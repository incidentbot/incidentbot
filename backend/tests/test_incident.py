import re

from bot.incident.action_parameters import (
    ActionParametersSlack,
    ActionParametersWeb,
)
from bot.incident.incident import Incident, RequestParameters
from bot.utils import utils
from bot.templates.incident.channel_boilerplate import (
    IncidentChannelBoilerplateMessage,
)
from bot.templates.incident.digest_notification import (
    IncidentChannelDigestNotification,
)
from bot.templates.incident.resolution_message import IncidentResolutionMessage
from bot.templates.incident.updates import IncidentUpdate
from bot.templates.incident.user_dm import IncidentUserNotification

placeholder_token = "verification-token"
placeholder_team_id = "T111"
placeholder_enterprise_id = "E111"
placeholder_app_id = "A111"


class TestIncidentManagement:
    def test_action_parameters_slack(self):
        ap = ActionParametersSlack(
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

        assert ap.actions == {
            "action_id": "sample-action",
            "block_id": "=qXel",
            "text": {"type": "plain_text", "text": "View", "emoji": True},
            "value": "click_me_123",
            "type": "button",
            "action_ts": "1548426417.840180",
        }

        assert ap.channel_details == {"id": "CBR2V3XEX", "name": "mock"}

        assert ap.message_details == {
            "bot_id": "BAH5CA16Z",
            "type": "message",
            "text": "This content can't be displayed.",
            "user": "UAJ2RU415",
            "ts": "1548261231.000200",
        }

        assert ap.user_details == {
            "id": "UA8RXUSPL",
            "name": "sample",
            "team_id": "T9TK3CUKW",
        }

        assert ap.parameters == {
            "action_id": "sample-action",
            "channel_id": "CBR2V3XEX",
            "channel_name": "mock",
            "timestamp": "1548261231.000200",
            "user": "sample",
            "user_id": "UA8RXUSPL",
        }

    def test_action_parameters_web(self):
        ap = ActionParametersWeb(
            incident_id="mock_incident_id",
            channel_id="mock_channel_id",
            role="mock_role",
            bp_message_ts="mock_ts",
            user="mock_user",
        )

        assert ap.incident_id == "mock_incident_id"

        assert ap.channel_id == "mock_channel_id"

        assert ap.role == "mock_role"

        assert ap.bp_message_ts == "mock_ts"

        assert ap.user == "mock_user"

    def test_incident_instantiate(self):
        inc = Incident(
            request_parameters=RequestParameters(
                channel="CBR2V3XEX",
                incident_description="something has broken",
                user="sample-incident-creator-user",
                severity="sev4",
                created_from_web=False,
                is_security_incident=False,
            )
        )
        assert isinstance(inc, Incident)

        assert re.search("^inc.*something-has-broken$", inc.channel_name)

        assert inc.meeting_link == "mock"

    def test_incident_channel_name_create(self):
        inc = Incident(
            request_parameters=RequestParameters(
                channel="CBR2V3XEX",
                incident_description="unallowed ch@racter check!",
                user="sample-incident-creator-user",
                severity="sev4",
                created_from_web=False,
                is_security_incident=False,
            )
        )

        assert re.search("^inc.*unallowed-chracter-check$", inc.channel_name)

    def test_incident_build_digest_notification(self):
        assert IncidentChannelDigestNotification.create(
            incident_channel_details={
                "incident_description": "mock",
                "id": "CBR2V3XEX",
                "name": "mock",
                "is_security_incident": False,
            },
            meeting_link="mock",
            severity="sev4",
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
                        "text": "A new incident has been declared. Please use the buttons here to participate.\n#mock",
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
                                "text": "🚀 Join",
                            },
                            "style": "primary",
                            "url": "https://test.slack.com/archives/mock",
                            "action_id": "incident.join_incident_channel",
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "☎️ Meeting",
                            },
                            "url": "mock",
                            "action_id": "incident.clicked_meeting_link",
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Incident Guide",
                            },
                            "url": "https://mycompany.com/incidents",
                            "action_id": "incident.clicked_link_incident_guide",
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "My Neato Link",
                            },
                            "url": "https://cool.com",
                            "action_id": "incident.clicked_link_my_neato_link",
                        },
                    ],
                },
            ],
        }

    def test_build_incident_channel_boilerplate(self):
        msg = IncidentChannelBoilerplateMessage.create(
            incident_channel_details={"id": "CBR2V3XEX", "name": "mock"},
            severity="sev4",
        )
        assert msg == {
            "channel": "CBR2V3XEX",
            "blocks": [
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
                        "text": "Incident Commander should be claimed or assigned first. Any other roles should then be claimed or assigned.",
                    },
                },
                {
                    "block_id": "header_info_2",
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "The Incident Commander should verify the severity of this incident immediately. If the severity changes, please update it accordingly.",
                    },
                },
                {
                    "block_id": "header_info_3",
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "The incident starts out in *investigating* mode. As the incident progresses, it can be moved through statuses until it is resolved.",
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
                            "text": "Investigating",
                            "emoji": True,
                        },
                        "options": [
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "Investigating",
                                    "emoji": True,
                                },
                                "value": "investigating",
                            },
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "Identified",
                                    "emoji": True,
                                },
                                "value": "identified",
                            },
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "Monitoring",
                                    "emoji": True,
                                },
                                "value": "monitoring",
                            },
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "Resolved",
                                    "emoji": True,
                                },
                                "value": "resolved",
                            },
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
                            "text": "SEV4",
                            "emoji": True,
                        },
                        "options": [
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "SEV1",
                                    "emoji": True,
                                },
                                "value": "sev1",
                            },
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "SEV2",
                                    "emoji": True,
                                },
                                "value": "sev2",
                            },
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "SEV3",
                                    "emoji": True,
                                },
                                "value": "sev3",
                            },
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "SEV4",
                                    "emoji": True,
                                },
                                "value": "sev4",
                            },
                        ],
                    },
                },
                {"type": "divider"},
                {
                    "block_id": "role_incident_commander",
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Incident Commander*:\n _none_",
                    },
                },
                {
                    "type": "section",
                    "block_id": "claim_incident_commander",
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
                        "value": "incident_commander",
                        "action_id": "incident.claim_role",
                    },
                },
                {
                    "type": "section",
                    "block_id": "assign_incident_commander",
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
                {
                    "block_id": "role_technical_lead",
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Technical Lead*:\n _none_",
                    },
                },
                {
                    "type": "section",
                    "block_id": "claim_technical_lead",
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
                        "value": "technical_lead",
                        "action_id": "incident.claim_role",
                    },
                },
                {
                    "type": "section",
                    "block_id": "assign_technical_lead",
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
                {
                    "block_id": "role_communications_liaison",
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Communications Liaison*:\n _none_",
                    },
                },
                {
                    "type": "section",
                    "block_id": "claim_communications_liaison",
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
                        "value": "communications_liaison",
                        "action_id": "incident.claim_role",
                    },
                },
                {
                    "type": "section",
                    "block_id": "assign_communications_liaison",
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
                {
                    "block_id": "help_buttons",
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Manage Timeline",
                                "emoji": True,
                            },
                            "action_id": "open_incident_bot_timeline",
                            "style": "primary",
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Provide Update",
                                "emoji": True,
                            },
                            "action_id": "open_incident_general_update_modal",
                            "style": "primary",
                        },
                        {
                            "action_id": "open_incident_create_jira_issue_modal",
                            "style": "primary",
                            "text": {
                                "emoji": True,
                                "text": "Create Jira Issue",
                                "type": "plain_text",
                            },
                            "type": "button",
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Incident Guide",
                            },
                            "url": "https://mycompany.com/incidents",
                            "action_id": "incident.clicked_link_incident_guide",
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "My Neato Link",
                            },
                            "url": "https://cool.com",
                            "action_id": "incident.clicked_link_my_neato_link",
                        },
                    ],
                },
                {"type": "divider"},
            ],
        }

    def test_build_status_update(self):
        status = "monitoring"
        assert IncidentUpdate.status(channel="mock", status=status) == {
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
        severity = "sev4"
        is_security_incident = False
        msg = IncidentChannelDigestNotification.update(
            incident_id="mock",
            incident_description="mock",
            is_security_incident=is_security_incident,
            status=status,
            severity=severity,
            meeting_link="mock",
        )
        assert msg == [
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
                    "text": ":grey_exclamation: Severity:\n *SEV4*",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "This incident is in progress. Current status is listed here. Join the channel for more information.\n#mock",
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
                            "text": "🚀 Join",
                        },
                        "style": "primary",
                        "url": "https://test.slack.com/archives/mock",
                        "action_id": "incident.join_incident_channel",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "☎️ Meeting",
                        },
                        "url": "mock",
                        "action_id": "incident.clicked_meeting_link",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Incident Guide",
                        },
                        "url": "https://mycompany.com/incidents",
                        "action_id": "incident.clicked_link_incident_guide",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "My Neato Link",
                        },
                        "url": "https://cool.com",
                        "action_id": "incident.clicked_link_my_neato_link",
                    },
                ],
            },
        ]

    def test_build_public_status_update(self):
        timestamp = utils.fetch_timestamp()
        assert IncidentUpdate.public_update(
            incident_id="mock",
            impacted_resources="api",
            message="foobar",
            timestamp=timestamp,
            user_id="1234",
        ) == [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":warning: Incident Update",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": "*Incident:*\n <#mock>"},
                    {
                        "type": "mrkdwn",
                        "text": f"*Posted At:*\n {timestamp}",
                    },
                    {"type": "mrkdwn", "text": "*Impacted Resources:*\n api"},
                    {"type": "mrkdwn", "text": "*Sent By:*\n <@1234>"},
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Current Status*\n foobar",
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
