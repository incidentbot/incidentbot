from apscheduler.job import Job
from incidentbot.configuration.settings import settings
from incidentbot.models.database import (
    IncidentParticipant,
    IncidentRecord,
    MaintenanceWindowRecord,
)
from incidentbot.models.incident import IncidentDatabaseInterface
from incidentbot.models.pager import read_pager_auto_page_targets
from incidentbot.models.slack import User
from typing import Any


class BlockBuilder:
    """
    Handles building blocks for Slack message content
    """

    @staticmethod
    def boilerplate_message(incident: IncidentRecord):
        blocks = [
            {"type": "divider"},
            {
                "block_id": "header",
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": incident.slug.upper(),
                },
            },
            {
                "block_id": "digest_channel_description",
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "{} *Description:* {}".format(
                        settings.icons.get(settings.platform).get(
                            "description"
                        ),
                        incident.description,
                    ),
                },
            },
            {
                "block_id": "digest_channel_components",
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "{} *Components:* {}".format(
                        settings.icons.get(settings.platform).get(
                            "components"
                        ),
                        incident.components,
                    ),
                },
            },
            {
                "block_id": "digest_channel_impact",
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "{} *Impact:* {}".format(
                        settings.icons.get(settings.platform).get("impact"),
                        incident.impact,
                    ),
                },
            },
            {"type": "divider"},
        ]

        button_el = []

        if (
            settings.integrations
            and settings.integrations.atlassian
            and settings.integrations.atlassian.jira
            and settings.integrations.atlassian.jira.enabled
        ):
            button_el.append(
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Create Jira Issue",
                        "emoji": True,
                    },
                    "action_id": "incident_create_jira_issue_modal",
                    "style": "primary",
                },
            )

        if settings.links:
            for link in settings.links:
                button_el.extend(
                    [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": link.title,
                            },
                            "url": link.url,
                            "action_id": f"incident.clicked_link_{link.title.lower().replace(' ', '_')}",
                        },
                    ]
                )

        if len(button_el) > 0:
            blocks.extend(
                [
                    {
                        "block_id": "help_buttons",
                        "type": "actions",
                        "elements": button_el,
                    },
                    {"type": "divider"},
                ]
            )

        return {
            "channel": incident.channel_id,
            "blocks": blocks,
        }

    @staticmethod
    def comms_reminder_message() -> list[dict[str, Any]]:
        """
        Return a message containing a reminder to handle communications at intervals
        """

        blocks = [
            {
                "block_id": "initial_comms_reminder_message",
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Some time has passed since this incident was declared. "
                    + "How about updating others on its status? If now isn't "
                    + "the right time, consider delaying this message using the "
                    + "buttons below. If you don't want any more reminders, you "
                    + "can also disable them.",
                },
            },
            {
                "block_id": "initial_comms_reminder_actions",
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Send Update",
                            "emoji": True,
                        },
                        "value": "show_incident_update_modal",
                        "action_id": "incident_update_modal",
                        "style": "primary",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "30m",
                            "emoji": True,
                        },
                        "value": "handle_initial_comms_reminder_30m",
                        "action_id": "incident.handle_initial_comms_reminder_30m",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "60m",
                            "emoji": True,
                        },
                        "value": "handle_initial_comms_reminder_60m",
                        "action_id": "incident.handle_initial_comms_reminder_60m",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "90m",
                            "emoji": True,
                        },
                        "value": "handle_initial_comms_reminder_90m",
                        "action_id": "incident.handle_initial_comms_reminder_90m",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Never",
                            "emoji": True,
                        },
                        "value": "handle_initial_comms_reminder_never",
                        "action_id": "incident.handle_initial_comms_reminder_never",
                    },
                ],
            },
        ]

        return blocks

    @staticmethod
    def declare_incident_modal(
        security_selected: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Blocks for the declare incident modal

        Parameters:
            security_selected (bool): Whether or not the security option is selected
        """
        placeholder = [sev for sev, _ in settings.severities.items()][-1]

        security_default = {
            "type": "section",
            "block_id": "is_security_incident",
            "text": {
                "type": "mrkdwn",
                "text": "*Is this a security incident?*",
            },
            "accessory": {
                "action_id": "incident.declare_incident_modal.set_security_type",
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select...",
                },
                "initial_option": {
                    "text": {
                        "type": "plain_text",
                        "text": "No",
                    },
                    "value": "false",
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Yes",
                        },
                        "value": "true",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "No",
                        },
                        "value": "false",
                    },
                ],
            },
        }

        security_true = {
            "type": "section",
            "block_id": "is_security_incident",
            "text": {
                "type": "mrkdwn",
                "text": "*Is this a security incident?*",
            },
            "accessory": {
                "action_id": "incident.declare_incident_modal.set_security_type",
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Yes",
                },
                "initial_option": {
                    "text": {
                        "type": "plain_text",
                        "text": "Yes",
                    },
                    "value": "true",
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Yes",
                        },
                        "value": "true",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "No",
                        },
                        "value": "false",
                    },
                ],
            },
        }

        set_private_default = {
            "type": "section",
            "block_id": "private_channel",
            "text": {
                "type": "mrkdwn",
                "text": "*Make Slack channel private?*",
            },
            "accessory": {
                "action_id": "incident.declare_incident_modal.set_private",
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select...",
                },
                "initial_option": {
                    "text": {
                        "type": "plain_text",
                        "text": "No",
                    },
                    "value": "false",
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Yes",
                        },
                        "value": "true",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "No",
                        },
                        "value": "false",
                    },
                ],
            },
        }

        set_private_security_true = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": ":lock: *Security incident channels will be created as private channels.*",
            },
        }

        blocks = [
            {
                "type": "input",
                "block_id": "incident.declare_incident_modal.set_description",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "incident.declare_incident_modal.set_description",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "A brief description of the problem.",
                    },
                    "max_length": 40,
                },
                "label": {"type": "plain_text", "text": "Description"},
            },
            {
                "type": "input",
                "block_id": "incident.declare_incident_modal.set_components",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "incident.declare_incident_modal.set_components",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Components impacted by the problem. (comma-separated)",
                    },
                    "max_length": 60,
                },
                "label": {"type": "plain_text", "text": "Components"},
            },
            {
                "type": "input",
                "block_id": "incident.declare_incident_modal.set_impact",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "incident.declare_incident_modal.set_impact",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Any known impact the problem is causing for users.",
                    },
                    "initial_value": "None",
                    "max_length": 120,
                    "min_length": 0,
                },
                "label": {"type": "plain_text", "text": "Impact"},
            },
            {
                "block_id": "incident.declare_incident_modal.set_severity",
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Severity*"},
                "accessory": {
                    "type": "static_select",
                    "action_id": "incident.declare_incident_modal.set_severity",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select a severity...",
                        "emoji": True,
                    },
                    "initial_option": {
                        "text": {
                            "type": "plain_text",
                            "text": placeholder.upper(),
                        },
                        "value": placeholder,
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
                        for sev, _ in settings.severities.items()
                    ],
                },
            },
            {
                "type": "section",
                "block_id": "incident.declare_incident_modal.set_additional_comms_channel",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Create additional comms channel?*",
                },
                "accessory": {
                    "action_id": "incident.declare_incident_modal.set_additional_comms_channel",
                    "type": "static_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select...",
                    },
                    "initial_option": {
                        "text": {
                            "type": "plain_text",
                            "text": "No",
                        },
                        "value": "false",
                    },
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Yes",
                            },
                            "value": "true",
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "No",
                            },
                            "value": "false",
                        },
                    ],
                },
            },
        ]

        if security_selected:
            blocks.append(security_true)
            blocks.append(set_private_security_true)
        else:
            blocks.append(security_default)
            blocks.append(set_private_default)

        """
        If there are teams that will be auto paged, mention that
        """

        if (
            settings.integrations
            and settings.integrations.pagerduty
            and settings.integrations.pagerduty.enabled
        ):
            auto_page_targets = read_pager_auto_page_targets()

            if auto_page_targets:
                blocks.extend(
                    [
                        {"type": "divider"},
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": ":point_right: *The following teams will "
                                + "be automatically paged when this incident is created:*",
                            },
                        },
                    ]
                )

                for i in auto_page_targets:
                    for k, v in i.items():
                        blocks.extend(
                            [
                                {
                                    "type": "section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": f"_{k}_",
                                    },
                                },
                            ]
                        )

        return blocks

    @staticmethod
    def describe_message(incident: IncidentRecord):
        """
        Formats a message for the describe command
        """

        blocks = digest_base(
            channel_id=incident.channel_id,
            incident_components=incident.components,
            incident_description=incident.description,
            incident_impact=incident.impact,
            incident_slug=incident.slug,
            severity=incident.severity,
            status=incident.status,
        )

        # If there are any roles assigned, list those too
        responders = IncidentDatabaseInterface.list_participants(
            incident=incident
        )

        if len(responders) > 0:
            responders_ = ""

            for responder in responders:
                role_normalized = responder.role.replace("_", " ").title()
                responders_ += "👤 *{}:* <@{}>\n\n".format(
                    role_normalized,
                    responder.user_id,
                )

            blocks.append(
                {
                    "block_id": "responders_info",
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": responders_,
                    },
                },
            )

        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "This message is a current description of "
                        + "this incident sent at user request.",
                    },
                ],
            }
        )

        return blocks

    @staticmethod
    def help_message() -> list[dict[str, Any]]:
        """
        Return a help message
        """

        help_message = f"""
> To interact with this incident: `{settings.root_slash_command} this`\n
> To interact with the bot in general: `{settings.root_slash_command}`\n
"""

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":ring_buoy: Help",
                },
            },
            {
                "block_id": "help_message",
                "type": "section",
                "text": {"type": "mrkdwn", "text": help_message},
            },
        ]

        return blocks

    @staticmethod
    def incident_list(
        incidents: list[IncidentRecord],
        exclude_timestamp: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Return a message containing details on incidents

        Parameters:
            incidents (list[IncidentRecord]): Incidents to include in message
            exclude_timestamp (bool): Whether or not to include the timestamp
        """

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":fire: Incidents",
                },
            },
            {"type": "divider"},
        ]

        results = []

        for incident in incidents:
            if exclude_timestamp:
                results.append(
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "> {} <#{}> *|* ".format(
                                settings.icons.get(settings.platform).get(
                                    "channel"
                                ),
                                incident.channel_id,
                            )
                            + f"*{incident.slug.upper()}* *|* "
                            + f":rotating_light: *{incident.severity.upper()}* *|* "
                            + f":fire_extinguisher: *{incident.status.title()}*",
                        },
                    }
                )
            else:
                results.append(
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "> {} <#{}> *|* ".format(
                                settings.icons.get(settings.platform).get(
                                    "channel"
                                ),
                                incident.channel_id,
                            )
                            + f"*{incident.slug.upper()}* *|* "
                            + f":rotating_light: *{incident.severity.upper()}* *|* "
                            + f":fire_extinguisher: *{incident.status.title()}*"
                            + f" *|* _Open Since_ *{incident.created_at}*",
                        },
                    }
                )

        if len(incidents) == 0:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "No open incidents.",
                    },
                },
            )
        else:
            blocks.extend(results)

        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "This list is truncated to the last "
                        + f"{settings.options.show_most_recent_incidents_app_home_limit}"
                        + " most recent incidents.",
                    },
                ],
            }
        )

        return blocks

    @staticmethod
    def jira_issue_message(
        key: str, summary: str, type: str, link: str
    ) -> list[dict]:
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "A Jira issue has been created for this incident.",
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": "*Key:* {}".format(key),
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Summary:* {}".format(summary),
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Type:* {}".format(type),
                    },
                ],
            },
            {
                "type": "actions",
                "block_id": "jira_view_issue",
                "elements": [
                    {
                        "type": "button",
                        "action_id": "jira.view_issue",
                        "style": "primary",
                        "text": {
                            "type": "plain_text",
                            "text": "View Issue",
                        },
                        "url": link,
                    },
                ],
            },
        ]

    @staticmethod
    def maintenance_window_list(
        maintenance_windows: list[MaintenanceWindowRecord],
    ) -> list[dict[str, Any]]:
        """
        Return a message containing details on maintenance windows

        Parameters:
            maintenance_windows (list[MaintenanceWindowRecord]): Maintenance windows to include in message
        """

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "{} Maintenance Windows".format(
                        settings.icons.get(settings.platform).get(
                            "maintenance"
                        )
                    ),
                },
            },
            {"type": "divider"},
        ]

        for window in maintenance_windows:
            if window.status != settings.maintenance_windows.statuses[-1]:
                base = [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"> {window.title} *|* "
                            + f"*Components:* `{window.components}` *|* "
                            + f"*Status:* `{window.status.title()}` *|* "
                            + f"*Start:* `{window.start_timestamp}` *|* "
                            + f"*End:* `{window.end_timestamp}` *|* "
                            + f"*Contact:* <@{window.contact}>",
                        },
                    },
                    {
                        "block_id": f"maintenance_window_actions_{window.id}",
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Set Status",
                                    "emoji": True,
                                },
                                "value": "maintenance_window_set_status",
                                "action_id": "maintenance_window.set_this_status_modal",
                                "style": "primary",
                            },
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Delete",
                                    "emoji": True,
                                },
                                "value": "maintenance_window_delete",
                                "action_id": "maintenance_window.delete",
                                "style": "danger",
                            },
                        ],
                    },
                ]

                blocks.extend(base)

        if (
            len(
                [
                    window
                    for window in maintenance_windows
                    if window.status
                    != settings.maintenance_windows.statuses[-1]
                ]
            )
            == 0
        ):
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "No scheduled maintenance windows.",
                    },
                },
            )

        return blocks

    @staticmethod
    def maintenance_window_notification(
        record: MaintenanceWindowRecord,
        status: str,
    ) -> dict[str, Any]:
        """
        Return a message for maintenance window notifications

        Parameters:
            record (MaintenanceWindowRecord): Maintenance window to include in message
        """

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "{} Scheduled Maintenance Notification".format(
                        settings.icons.get(settings.platform).get(
                            "maintenance"
                        )
                    ),
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": record.title,
                },
            },
            {"type": "divider"},
            {
                "block_id": "maintenance_window_notification_description",
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "{} *Description:* {}".format(
                        settings.icons.get(settings.platform).get(
                            "description"
                        ),
                        record.description,
                    ),
                },
            },
            {
                "block_id": "maintenance_window_notification_components",
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "{} *Components:* `{}`".format(
                        settings.icons.get(settings.platform).get(
                            "components"
                        ),
                        record.components,
                    ),
                },
            },
            {
                "block_id": "maintenance_window_notification_start",
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "{} *Start Time:* `{}`".format(
                        settings.icons.get(settings.platform).get("stopwatch"),
                        record.start_timestamp,
                    ),
                },
            },
            {
                "block_id": "maintenance_window_notification_end",
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "{} *End Time:* `{}`".format(
                        settings.icons.get(settings.platform).get("stopwatch"),
                        record.end_timestamp,
                    ),
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"This maintenance window's status has changed to *{status}*.",
                },
            },
        ]

        return blocks

    @staticmethod
    def resolution_message(channel: str) -> dict[str, Any]:
        """
        Return a message containing resolution information for an incident

        Parameters:
            channel (str): channel_id to send message to
        """
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

        if settings.links:
            for link in settings.links:
                button_el.extend(
                    [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": link.title,
                            },
                            "url": link.url,
                            "action_id": f"incident.clicked_link_{link.title.lower().replace(' ', '_')}",
                        },
                    ]
                )

        status_definition = [
            status
            for status, config in settings.statuses.items()
            if config.final
        ][0]

        blocks = [
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
                    "text": f":tada: This incident has been marked as *{status_definition.title()}*.",
                },
            },
            {
                "block_id": "resolution_buttons",
                "type": "actions",
                "elements": button_el,
            },
        ]

        return {
            "channel": channel,
            "blocks": blocks,
        }

    @staticmethod
    def responders_list(
        incident: IncidentRecord,
        responders: list[IncidentParticipant],
        user: User,
    ) -> list[dict[str, Any]]:
        """
        Return a message containing details on incident responders

        Parameters:
            incident: (IncidentRecord): The record for the referenced incident
            responders (list[IncidentParticipant]): Participants to include in the response
            user (incidentbot.models.slack.User): User object describing the user executing the command
        """

        if len(responders) == 0:
            return [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f":fire: Responders for {incident.slug.upper()}",
                    },
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "No responders have claimed any roles for this incident.",
                    },
                },
            ]

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f":fire: Responders for {incident.slug.upper()}",
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "These people are currently responding to this incident.",
                },
            },
        ]

        for responder in responders:
            button_el = []

            if responder.user_id == user.id:
                button_el.append(
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Leave",
                            "emoji": True,
                        },
                        "value": f"leave_this_incident_as_{responder.role}",
                        "action_id": "incident.leave_this_incident",
                    }
                )

            blocks.extend(
                [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "> <@{}> is currently *{}*".format(
                                responder.user_id,
                                responder.role.replace("_", " ").title(),
                            ),
                        },
                    },
                ]
            )

            if len(button_el):
                blocks.append(
                    {
                        "type": "actions",
                        "elements": button_el,
                    }
                )

        return blocks

    @staticmethod
    def role_assignment_message() -> list[dict[str, Any]]:
        """
        Return a message containing a reminder to claim roles
        """

        blocks = [
            {
                "block_id": "role_assignment_reminder_message",
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ":point_right: @here No roles have been assigned for this incident yet. "
                    + "Please review, assess, and claim as-needed.",
                },
            },
            {
                "block_id": "role_assignment_reminder_message_actions",
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "👤 Join as {}".format(
                                " ".join(role.split("_")).title()
                            ),
                            "emoji": True,
                        },
                        "value": f"join_this_incident_{role}",
                        "action_id": f"incident.join_this_incident_{role}",
                    }
                    for role in [key for key, _ in settings.roles.items()]
                ],
            },
        ]

        return blocks

    @staticmethod
    def set_this_severity_modal(
        record: IncidentRecord,
    ) -> list[dict[str, Any]]:
        """
        Blocks for the severity select modal

        Parameters:
            record (IncidentRecord): The IncidentRecord for the incident
        """

        blocks = [
            {
                "block_id": f"set_this_severity_modal_header_{record.channel_id}",
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": record.slug.upper(),
                },
            },
            {
                "block_id": "set_this_severity_modal_description",
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "{} *Description:* {}".format(
                        settings.icons.get(settings.platform).get(
                            "description"
                        ),
                        record.description,
                    ),
                },
            },
            {
                "block_id": "set_this_severity_modal_components",
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "{} *Components:* {}".format(
                        settings.icons.get(settings.platform).get(
                            "components"
                        ),
                        record.components,
                    ),
                },
            },
            {
                "block_id": "set_this_severity_modal_impact",
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "{} *Impact:* {}".format(
                        settings.icons.get(settings.platform).get("impact"),
                        record.impact,
                    ),
                },
            },
            {"type": "divider"},
            {
                "block_id": "set_this_severity_modal_current_severity_header",
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Set Severity",
                },
            },
            {
                "block_id": "set_this_severity_modal_severity_select",
                "type": "actions",
                "elements": [
                    {
                        "type": "static_select",
                        "action_id": "incident.set_this_severity",
                        "placeholder": {
                            "type": "plain_text",
                            "text": record.severity.upper(),
                            "emoji": True,
                        },
                        "initial_option": {
                            "text": {
                                "type": "plain_text",
                                "text": record.severity.upper(),
                                "emoji": True,
                            },
                            "value": record.severity,
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
                            for sev, _ in settings.severities.items()
                        ],
                    }
                ],
            },
            {"type": "divider"},
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "When you click Done, the severity will be "
                        + "updated to the value selected above. The channel "
                        + "will be notified of this change. The home message "
                        + "in the digest channel will also be updated.",
                    }
                ],
            },
        ]

        return blocks

    @staticmethod
    def set_this_status_modal(
        object_type: str,
        record: IncidentRecord | MaintenanceWindowRecord,
    ) -> list[dict[str, Any]]:
        """
        Blocks for the status select modal

        Parameters:
            object_type (str): One of incident,maintenance_window
            record (IncidentRecord | MaintenanceWindowRecord): The record for the object
        """

        match object_type:
            case "incident":
                blocks = [
                    {
                        "block_id": f"set_this_status_modal_header_{record.channel_id}",
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": record.slug.upper(),
                        },
                    },
                    {
                        "block_id": "set_this_status_modal_description",
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "{} *Description:* {}".format(
                                settings.icons.get(settings.platform).get(
                                    "description"
                                ),
                                record.description,
                            ),
                        },
                    },
                    {
                        "block_id": "set_this_status_modal_components",
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "{} *Components:* {}".format(
                                settings.icons.get(settings.platform).get(
                                    "components"
                                ),
                                record.components,
                            ),
                        },
                    },
                    {
                        "block_id": "set_this_status_modal_impact",
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "{} *Impact:* {}".format(
                                settings.icons.get(settings.platform).get(
                                    "impact"
                                ),
                                record.impact,
                            ),
                        },
                    },
                    {"type": "divider"},
                    {
                        "block_id": "set_this_status_modal_current_status_header",
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "Set Status",
                        },
                    },
                    {
                        "block_id": "set_this_status_modal_status_select",
                        "type": "actions",
                        "elements": [
                            {
                                "type": "static_select",
                                "action_id": "incident.set_this_status",
                                "placeholder": {
                                    "type": "plain_text",
                                    "text": record.status.title(),
                                    "emoji": True,
                                },
                                "initial_option": {
                                    "text": {
                                        "type": "plain_text",
                                        "text": record.status.title(),
                                        "emoji": True,
                                    },
                                    "value": record.status,
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
                                    for st in [
                                        status
                                        for status in settings.statuses.keys()
                                    ]
                                ],
                            }
                        ],
                    },
                    {"type": "divider"},
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": "When you click Done, the status will be "
                                + "updated to the value selected above. The channel "
                                + "will be notified of this change. The home message "
                                + "in the digest channel will also be updated.",
                            }
                        ],
                    },
                ]
            case "maintenance_window":
                blocks = [
                    {
                        "block_id": f"set_this_status_modal_header_{record.id}",
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": record.description,
                        },
                    },
                    {
                        "block_id": "set_this_status_modal_description",
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "{} *Description:* {}".format(
                                settings.icons.get(settings.platform).get(
                                    "description"
                                ),
                                record.description,
                            ),
                        },
                    },
                    {
                        "block_id": "set_this_status_modal_components",
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "{} *Components:* {}".format(
                                settings.icons.get(settings.platform).get(
                                    "components"
                                ),
                                record.components,
                            ),
                        },
                    },
                    {"type": "divider"},
                    {
                        "block_id": "set_this_status_modal_current_status_header",
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "Set Status",
                        },
                    },
                    {
                        "block_id": "set_this_status_modal_status_select",
                        "type": "actions",
                        "elements": [
                            {
                                "type": "static_select",
                                "action_id": "maintenance_window.set_this_status",
                                "placeholder": {
                                    "type": "plain_text",
                                    "text": record.status,
                                    "emoji": True,
                                },
                                "initial_option": {
                                    "text": {
                                        "type": "plain_text",
                                        "text": record.status,
                                        "emoji": True,
                                    },
                                    "value": record.status,
                                },
                                "options": [
                                    {
                                        "text": {
                                            "type": "plain_text",
                                            "text": st,
                                            "emoji": True,
                                        },
                                        "value": st,
                                    }
                                    for st in settings.maintenance_windows.statuses
                                ],
                            }
                        ],
                    },
                ]

        return blocks

    @staticmethod
    def statuspage_incident_list(
        incidents: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Return a message containing details on Statuspage incidents

        Parameters:
            incidents (list[Dict[str, str]]): Incidents to iterate over
        """

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":fire: Statuspage Incidents",
                },
            },
            {"type": "divider"},
        ]
        formatted_incidents = []
        none_found_block = [
            {"type": "divider"},
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":fire: No Statuspage Incidents",
                },
            },
            {"type": "divider"},
        ]

        # Check to see if there are any incidents
        if len(incidents) == 0:
            return none_found_block
        else:
            for inc in incidents:
                name = inc["name"]
                status = inc["status"]
                impact = inc["impact"]
                created_at = inc["created_at"]
                updated_at = inc["updated_at"]
                shortlink = inc["shortlink"]
                if (
                    inc["status"]
                    != [
                        status
                        for status, config in settings.statuses.items()
                        if config.final
                    ][0]
                ):
                    formatted_incidents.append(
                        {
                            "type": "section",
                            "fields": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Name:* {name}",
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Status* {status}",
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Impact:* {impact}",
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Created:* {created_at}",
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Last Updated:* {updated_at}",
                                },
                            ],
                        }
                    )
                    formatted_incidents.append(
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {
                                        "type": "plain_text",
                                        "text": "Open In Statuspage",
                                    },
                                    "url": shortlink,
                                },
                            ],
                        },
                    )
                    formatted_incidents.append({"type": "divider"})
        if len(formatted_incidents) == 0:
            return none_found_block
        else:
            for inc in formatted_incidents:
                blocks.append(inc)

        return blocks

    @staticmethod
    def task_list(
        tasks: list[Job],
    ) -> list[dict[str, Any]]:
        """
        Return a message containing details on tasks associated with incidents

        Parameters:
            incidents (list[Job]): Tasks to include in message
        """

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":fire: Tasks",
                },
            },
            {"type": "divider"},
        ]

        for item in [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "> {} *|* {} *|* {} ".format(
                        settings.icons.get(settings.platform).get("task"),
                        task.id,
                        task.name,
                    ),
                },
            }
            for task in tasks
        ]:
            blocks.append(item)

        return blocks

    @staticmethod
    def user_notification(role: str) -> list[dict[str, Any]]:
        # Role comes into this method as a lowercase, space delimited string
        # Since roles are defined using underscores, we have to put them back when looking
        # up the definitions
        role_def = "_".join(role.split(" "))

        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":wave: You have joined this incident as {}. {}".format(
                        role.title(),
                        settings.roles.get(role_def).get("description"),
                    ),
                },
            }
        ]

    @staticmethod
    def welcome_message() -> list[dict[str, Any]]:
        """
        Return a message containing helpful information at the start of
        an incident - this is different from the boilerplate message
        """

        join_buttons = [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "👤 Join as {}".format(
                        " ".join(role.split("_")).title()
                    ),
                    "emoji": True,
                },
                "value": f"join_this_incident_{role}",
                "action_id": f"incident.join_this_incident_{role}",
            }
            for role in [key for key, _ in settings.roles.items()]
        ]

        other_buttons = [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "🛟 Get Help",
                    "emoji": True,
                },
                "value": "get_help_for_this_incident",
                "action_id": "incident.get_help_for_this_incident",
            }
        ]

        if (
            settings.integrations
            and settings.integrations.atlassian
            and settings.integrations.atlassian.jira
            and settings.integrations.atlassian.jira.enabled
        ):
            other_buttons.append(
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "➕ Create Jira Issue",
                        "emoji": True,
                    },
                    "action_id": "incident_create_jira_issue_modal",
                },
            )

        if (
            settings.integrations
            and settings.integrations.pagerduty
            and settings.integrations.pagerduty.enabled
        ) or (
            settings.integrations
            and settings.integrations.atlassian
            and settings.integrations.atlassian.opsgenie
            and settings.integrations.atlassian.opsgenie.enabled
        ):
            other_buttons.append(
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📟 Page On-call",
                        "emoji": True,
                    },
                    "action_id": "pager",
                },
            )

        if settings.links:
            for link in settings.links:
                other_buttons.append(
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": f"🔗 {link.title}",
                        },
                        "url": link.url,
                        "action_id": f"incident.clicked_link_{link.title.lower().replace(' ', '_')}",
                    },
                )

        blocks = [
            {
                "block_id": "welcome_message",
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Here are some actions to help your team get started "
                    + "with this new incident.",
                },
            },
            {
                "block_id": "welcome_actions",
                "type": "actions",
                "elements": join_buttons + other_buttons,
            },
        ]

        return blocks


"""
Digest channel messages
"""


def digest_base(
    channel_id: str,
    incident_components: str,
    incident_description: str,
    incident_impact: str | None,
    incident_slug: str,
    severity: str,
    status: str,
) -> list[dict[str, Any]]:
    """
    Base formatting for the digest channel message
    """

    match status.lower():
        case "resolved":
            header = f"{incident_slug.upper()} [Resolved] :tada:"
            status_format = "Resolved :white_check_mark:"
        case _:
            header = incident_slug.upper()
            status_format = status.title()

    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": header,
            },
        },
        {"type": "divider"},
        {
            "block_id": "digest_channel_link",
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "{} *Channel:* <#{}>".format(
                    settings.icons.get(settings.platform).get("channel"),
                    channel_id,
                ),
            },
        },
        {
            "block_id": "digest_channel_description",
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "{} *Description:* {}".format(
                    settings.icons.get(settings.platform).get("description"),
                    incident_description,
                ),
            },
        },
        {
            "block_id": "digest_channel_components",
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "{} *Components:* {}".format(
                    settings.icons.get(settings.platform).get("components"),
                    incident_components,
                ),
            },
        },
        {
            "block_id": "digest_channel_impact",
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "{} *Impact:* {}".format(
                    settings.icons.get(settings.platform).get("impact"),
                    incident_impact,
                ),
            },
        },
        {
            "block_id": "digest_channel_status",
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "{} *Status:* {}".format(
                    settings.icons.get(settings.platform).get("status"),
                    status_format,
                ),
            },
        },
        {
            "block_id": "digest_channel_severity",
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "{} *Severity:* {}".format(
                    settings.icons.get(settings.platform).get("severity"),
                    severity.upper(),
                ),
            },
        },
    ]


class IncidentChannelDigestNotification:
    @staticmethod
    def create(
        channel_id: str,
        has_private_channel: bool,
        incident_components: str,
        incident_description: str,
        incident_impact: str | None,
        incident_slug: str,
        initial_status: str,
        severity: str,
        meeting_link: str | None = None,
        postmortem_link: str | None = None,
    ) -> dict[str, Any]:
        """
        Formats a digest channel notification for initial creation
        """

        blocks = digest_base(
            channel_id=channel_id,
            incident_components=incident_components,
            incident_description=incident_description,
            incident_impact=incident_impact,
            incident_slug=incident_slug,
            severity=severity,
            status=initial_status,
        )

        if meeting_link and (not has_private_channel):
            blocks.extend(
                [
                    {
                        "block_id": "digest_channel_meeting",
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "{} *Meeting:* <{}|Join>".format(
                                settings.icons.get(settings.platform).get(
                                    "meeting"
                                ),
                                meeting_link,
                            ),
                        },
                    }
                ]
            )

        if postmortem_link:
            blocks.extend(
                [
                    {
                        "block_id": "postmortem_link",
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "{} *Postmortem:* <{}|View>".format(
                                settings.icons.get(settings.platform).get(
                                    "postmortem"
                                ),
                                postmortem_link,
                            ),
                        },
                    },
                    {"type": "divider"},
                ]
            )
        else:
            blocks.append({"type": "divider"})

        return {
            "channel": settings.digest_channel,
            "blocks": blocks,
        }

    @staticmethod
    def update(
        channel_id: str,
        has_private_channel: bool,
        incident_components: str,
        incident_description: str,
        incident_impact: str | None,
        incident_slug: str,
        severity: str,
        status: str,
        meeting_link: str | None = None,
        postmortem_link: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Formats a digest channel notification for updates
        """

        blocks = digest_base(
            channel_id=channel_id,
            incident_components=incident_components,
            incident_description=incident_description,
            incident_impact=incident_impact,
            incident_slug=incident_slug,
            severity=severity,
            status=status,
        )

        if meeting_link and (not has_private_channel):
            blocks.append(
                {
                    "block_id": "digest_channel_meeting",
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "{} *Meeting:* <{}|Join>".format(
                            settings.icons.get(settings.platform).get(
                                "meeting"
                            ),
                            meeting_link,
                        ),
                    },
                },
            )

        if postmortem_link:
            blocks.extend(
                [
                    {
                        "block_id": "postmortem_link",
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "{} *Postmortem:* <{}|View>".format(
                                settings.icons.get(settings.platform).get(
                                    "postmortem"
                                ),
                                postmortem_link,
                            ),
                        },
                    },
                    {"type": "divider"},
                ]
            )
        else:
            blocks.append({"type": "divider"})

        return blocks


"""
Incident updates
"""


class IncidentUpdate:
    @staticmethod
    def public_update(
        id: str,
        impacted_resources: str,
        message: str,
        timestamp: str,
        user_id: str,
    ) -> dict[str, Any]:
        """
        Message for incident updates
        """

        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "{} Incident Update".format(
                        settings.icons.get(settings.platform).get("update")
                    ),
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": "*Incident:*\n {} <#{}>".format(
                            settings.icons.get(settings.platform).get(
                                "channel"
                            ),
                            id,
                        ),
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Posted At:*\n {timestamp}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Impacted Resources:*\n {impacted_resources}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Sent By:*\n <@{user_id}>",
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
                        "text": "This update was provided by the incident "
                        + "management team in response to an ongoing incident.",
                    }
                ],
            },
        ]

    @staticmethod
    def role(
        action: str, channel: str, role: str, user: str
    ) -> dict[str, Any]:
        return {
            "channel": channel,
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "{} Role Update".format(
                            settings.icons.get(settings.platform).get("role")
                        ),
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"<@{user}> has {action} this incident as *{role}*.",
                    },
                },
            ],
        }

    @staticmethod
    def severity(channel: str, severity: str):
        return {
            "channel": channel,
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "{} Severity Update".format(
                            settings.icons.get(settings.platform).get(
                                "severity"
                            )
                        ),
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"The incident severity has changed to *{severity.upper()}*. "
                        + settings.severities.get(severity),
                    },
                },
            ],
        }

    @staticmethod
    def status(channel: str, status: str):
        return {
            "channel": channel,
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "{} Status Update".format(
                            settings.icons.get(settings.platform).get("status")
                        ),
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"The incident status has changed to *{status.title()}*.",
                    },
                },
            ],
        }
