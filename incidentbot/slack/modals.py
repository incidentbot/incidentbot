from datetime import datetime
from incidentbot.configuration.settings import (
    settings,
    statuspage_logo_url,
    __version__,
)
from incidentbot.exceptions import ConfigurationError
from incidentbot.incident.core import Incident, IncidentRequestParameters
from incidentbot.incident.event import EventLogHandler
from incidentbot.jira.issue import JiraIssue
from incidentbot.logging import logger
from incidentbot.maintenance_window.core import (
    MaintenanceWindow,
    MaintenanceWindowRequestParameters,
)
from incidentbot.models.database import (
    engine,
    ApplicationData,
    JiraIssueRecord,
)
from incidentbot.models.incident import IncidentDatabaseInterface
from incidentbot.models.maintenance_window import (
    MaintenanceWindowDatabaseInterface,
)
from incidentbot.slack.client import check_user_in_group, get_digest_channel_id
from incidentbot.slack.handler import app
from incidentbot.slack.messages import BlockBuilder, IncidentUpdate
from incidentbot.statuspage.handler import (
    StatuspageComponents,
    StatuspageIncident,
    StatuspageIncidentUpdate,
)
from incidentbot.slack.util import parse_modal_values
from incidentbot.util import gen
from sqlmodel import Session, select


@app.event("app_home_opened")
def update_home_tab(client, event, logger):
    """
    Provide information via the app's home screen
    """

    button_el = [
        {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "Declare Incident",
                "emoji": True,
            },
            "value": "show_declare_incident_modal",
            "action_id": "declare_incident_modal",
            "style": "danger",
        }
    ]

    if (
        settings.maintenance_windows
        and settings.maintenance_windows.components
    ):
        button_el.append(
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Create a Maintenance Window",
                    "emoji": True,
                },
                "value": "show_maintenance_window_modal",
                "action_id": "maintenance_window_modal",
                "style": "primary",
            },
        )

    base_blocks = [
        {"type": "actions", "elements": button_el},
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":firefighter: Creating Incidents",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "To start a new incident, you can do the following:\n"
                + "> Use the button here :point_up:\n"
                + f"> Use my slash command: `{settings.root_slash_command}`",
            },
        },
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":point_right: Documentation and Learning Materials",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Check out Incident Bot's <https://docs.incidentbot.io/|docs>.",
            },
        },
    ]

    database_data = IncidentDatabaseInterface.list_recent(
        limit=settings.options.show_most_recent_incidents_app_home_limit
    )
    open_incidents = BlockBuilder.incident_list(incidents=database_data)
    base_blocks.extend(open_incidents)

    if (
        settings.maintenance_windows
        and settings.maintenance_windows.components
    ):
        database_data = MaintenanceWindowDatabaseInterface.list_all()
        open_incidents = BlockBuilder.maintenance_window_list(
            maintenance_windows=database_data
        )
        base_blocks.extend(open_incidents)

    base_blocks.extend(
        [
            {"type": "divider"},
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Version {__version__}",
                    }
                ],
            },
        ]
    )

    try:
        client.views_publish(
            user_id=event["user"],
            view={
                "type": "home",
                "blocks": base_blocks,
            },
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")


@app.action("declare_incident_modal")
def show_modal(ack, body, client):  # noqa: F811
    """
    Provides the modal that will display for declaring an incident
    """

    ack()
    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            # View identifier
            "callback_id": "declare_incident_modal",
            "title": {"type": "plain_text", "text": "Declare Incident"},
            "submit": {"type": "plain_text", "text": "Start"},
            "blocks": BlockBuilder.declare_incident_modal(),
        },
    )


@app.view("declare_incident_modal")
def handle_submission(ack, body, client):  # noqa: F811
    """
    Handles declare_incident_modal
    """

    ack()
    parsed = parse_modal_values(body)
    user = body.get("user").get("id")

    # Create request parameters object
    try:
        incident = Incident(
            IncidentRequestParameters(
                additional_comms_channel=parsed.get(
                    "incident.declare_incident_modal.set_additional_comms_channel"
                ),
                incident_components=parsed.get(
                    "incident.declare_incident_modal.set_components"
                ),
                incident_description=parsed.get(
                    "incident.declare_incident_modal.set_description"
                ),
                incident_impact=parsed.get(
                    "incident.declare_incident_modal.set_impact"
                ),
                is_security_incident=parsed.get(
                    "incident.declare_incident_modal.set_security_type"
                )
                in (
                    "True",
                    "true",
                    True,
                ),
                private_channel=parsed.get(
                    "incident.declare_incident_modal.set_private"
                )
                in (
                    "True",
                    "true",
                    True,
                ),
                severity=parsed.get(
                    "incident.declare_incident_modal.set_severity"
                ),
                user=user,
            )
        )

        resp = incident.start()

        client.chat_postMessage(channel=user, text=resp)
    except Exception as error:
        logger.error(error)


@app.action("incident_update_modal")
def show_modal(ack, body, client):  # noqa: F811
    """
    Provides the modal that will display when the shortcut is used to provide an incident update
    """

    ack()

    database_data = IncidentDatabaseInterface.list_open()
    view = {
        "type": "modal",
        "callback_id": "incident_update_modal",
        "title": {"type": "plain_text", "text": "Provide incident update"},
        "submit": {"type": "plain_text", "text": "Submit"},
        "blocks": (
            [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"This will send a message to <#{get_digest_channel_id()}> "
                        + "in a thread under the selected "
                        + "incident's original announcement message. "
                        + "This is useful to keep users not directly "
                        + "involved in the incident up to date regarding "
                        + "its status.",
                    },
                },
                {
                    "block_id": "incident_update_modal_incident_channel",
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Associated Incident:",
                    },
                    "accessory": {
                        "type": "static_select",
                        "action_id": "incident.update_modal.select_incident",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Select an ongoing incident...",
                            "emoji": True,
                        },
                        "options": [
                            (
                                {
                                    "text": {
                                        "type": "plain_text",
                                        "text": "None",
                                        "emoji": True,
                                    },
                                    "value": "none",
                                }
                                if len(database_data) == 0
                                else {
                                    "text": {
                                        "type": "plain_text",
                                        "text": f"<#{inc.channel_id}>",
                                        "emoji": True,
                                    },
                                    "value": f"<#{inc.channel_id}>",
                                }
                            )
                            for inc in database_data
                            if inc.status
                            != [
                                status
                                for status, config in settings.statuses.items()
                                if config.final
                            ][0]
                        ],
                    },
                },
                {
                    "type": "input",
                    "block_id": "incident_update_modal_impacted_resources",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "incident.update_modal.set_impacted_resources",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "e.g. API, Authentication, Dashboards",
                        },
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Impacted Resources:",
                    },
                },
                {
                    "type": "input",
                    "block_id": "incident_update_modal_message",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "incident.update_modal.set_message",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "A brief message to include with this update.",
                        },
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Message to Include:",
                    },
                },
            ]
            if len(database_data) != 0
            else [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "There are currently no open incidents.",
                    },
                },
            ]
        ),
    }
    client.views_open(
        trigger_id=body["trigger_id"],
        view=view,
    )


@app.view("incident_update_modal")
def handle_submission(ack, body, client):  # noqa: F811
    """
    Handles incident_update_modal
    """

    ack()

    parsed = parse_modal_values(body)
    channel_id = parsed.get("incident.update_modal.select_incident")
    user_id = body.get("user").get("id")

    # Extract the channel ID without extra characters
    for character in "#<>":
        channel_id = channel_id.replace(character, "")

    inc = IncidentDatabaseInterface.get_one(channel_id=channel_id)

    try:
        client.chat_postMessage(
            channel=get_digest_channel_id(),
            thread_ts=(
                inc.digest_message_ts
                if settings.options.updates_in_threads
                else None
            ),
            blocks=IncidentUpdate.public_update(
                id=channel_id,
                impacted_resources=parsed.get(
                    "incident.update_modal.set_impacted_resources"
                ),
                message=parsed.get("incident.update_modal.set_message"),
                timestamp=gen.fetch_timestamp(),
                user_id=user_id,
            ),
            text="Incident update for incident <#{}>: {}".format(
                channel_id, parsed.get("incident.update_modal.set_message")
            ),
        )
    except Exception as error:
        logger.error(
            f"Error sending update out for {inc.channel_name}: {error}"
        )


"""
Maintenance Windows
"""


@app.action("maintenance_window_modal")
def show_modal(ack, body, client):  # noqa: F811
    """
    Provides the modal that will display when the shortcut is used to create a maintenance window
    """

    base_blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "This will create a new maintenance window.",
            },
        },
        {
            "type": "input",
            "block_id": "title",
            "element": {
                "type": "plain_text_input",
                "action_id": "maintenance_window.set_title",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Title",
                },
            },
            "label": {"type": "plain_text", "text": "Title"},
        },
        {
            "type": "input",
            "block_id": "description",
            "element": {
                "type": "plain_text_input",
                "multiline": True,
                "action_id": "maintenance_window.set_description",
                "placeholder": {
                    "type": "plain_text",
                    "text": "A description of the maintenance window.",
                },
            },
            "label": {"type": "plain_text", "text": "Description"},
        },
        {
            "block_id": "components",
            "type": "input",
            "element": {
                "type": "multi_static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select components...",
                    "emoji": True,
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": component,
                            "emoji": True,
                        },
                        "value": component,
                    }
                    for component in settings.maintenance_windows.components
                ],
                "action_id": "maintenance_window.set_components",
            },
            "label": {
                "type": "plain_text",
                "text": "Components",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "block_id": "channels",
            "text": {"type": "mrkdwn", "text": "Channels to be notified"},
            "accessory": {
                "type": "multi_conversations_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select channels...",
                    "emoji": True,
                },
                "action_id": "maintenance_window.set_channels",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Who is the contact point for this maintenance window?",
            },
            "accessory": {
                "type": "users_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select a user",
                    "emoji": True,
                },
                "action_id": "maintenance_window.set_contact",
            },
        },
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":white_check_mark: Start time",
            },
        },
        {
            "type": "input",
            "block_id": "start_date",
            "element": {
                "type": "datepicker",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select a date",
                    "emoji": True,
                },
                "action_id": "maintenance_window.set_start_date",
            },
            "label": {"type": "plain_text", "text": "Date", "emoji": True},
        },
        {
            "type": "input",
            "block_id": "start_time",
            "element": {
                "type": "timepicker",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select time",
                    "emoji": True,
                },
                "action_id": "maintenance_window.set_start_time",
            },
            "label": {"type": "plain_text", "text": "Time", "emoji": True},
        },
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":checkered_flag: End time",
            },
        },
        {
            "type": "input",
            "block_id": "end_date",
            "element": {
                "type": "datepicker",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select a date",
                    "emoji": True,
                },
                "action_id": "maintenance_window.set_end_date",
            },
            "label": {"type": "plain_text", "text": "Date", "emoji": True},
        },
        {
            "type": "input",
            "block_id": "end_time",
            "element": {
                "type": "timepicker",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select time",
                    "emoji": True,
                },
                "action_id": "maintenance_window.set_end_time",
            },
            "label": {"type": "plain_text", "text": "Time", "emoji": True},
        },
    ]
    ack()
    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            # View identifier
            "callback_id": "maintenance_window_modal",
            "title": {
                "type": "plain_text",
                "text": "Maintenance window",
            },
            "submit": {"type": "plain_text", "text": "Create"},
            "blocks": base_blocks,
        },
    )


@app.view("maintenance_window_modal")
def handle_submission(ack, body, client):  # noqa: F811
    """
    Handles maintenance_window_modal
    """

    ack()
    parsed = parse_modal_values(body)
    user = body.get("user").get("id")

    end_date = parsed.get("maintenance_window.set_end_date")
    end_time = parsed.get("maintenance_window.set_end_time")
    start_date = parsed.get("maintenance_window.set_start_date")
    start_time = parsed.get("maintenance_window.set_start_time")

    end_timestamp = datetime.strptime(
        f"{end_date} {end_time}", "%Y-%m-%d %H:%M"
    )
    start_timestamp = datetime.strptime(
        f"{start_date} {start_time}", "%Y-%m-%d %H:%M"
    )

    try:
        maintenance_window = MaintenanceWindow(
            params=MaintenanceWindowRequestParameters(
                channels=parsed.get("maintenance_window.set_channels"),
                components=parsed.get("maintenance_window.set_components"),
                contact=parsed.get("maintenance_window.set_contact"),
                description=parsed.get("maintenance_window.set_description"),
                end_timestamp=end_timestamp,
                start_timestamp=start_timestamp,
                title=parsed.get("maintenance_window.set_title"),
            )
        )
        maintenance_window.create()
    except Exception as error:
        logger.error(error)

    try:
        client.chat_postMessage(
            channel=user, text="I've created the maintenance window."
        )
    except ConfigurationError as error:
        logger.error(error)


"""
Paging
"""


@app.action("pager")
@app.shortcut("pager")
def show_modal(ack, body, client):  # noqa: F811
    # Acknowledge the command request
    ack()

    if (
        settings.integrations
        and settings.integrations.pagerduty
        and settings.integrations.pagerduty.enabled
    ):
        from incidentbot.configuration.settings import pagerduty_logo_url

        platform = "PagerDuty"

        with Session(engine) as session:
            result = (
                session.exec(
                    select(ApplicationData).filter(
                        ApplicationData.name == "pagerduty_oc_data"
                    )
                )
            ).first()

            oncalls = result.json_data

        priorities = ["low", "high"]
        image_url = pagerduty_logo_url
    elif (
        settings.integrations
        and settings.integrations.atlassian
        and settings.integrations.atlassian.opsgenie
        and settings.integrations.atlassian.opsgenie.enabled
    ):
        from incidentbot.configuration.settings import opsgenie_logo_url
        from incidentbot.opsgenie import api as og_api

        platform = "Opsgenie"
        sess = og_api.OpsgenieAPI()
        oncalls = sess.list_teams()
        priorities = sess.priorities
        image_url = opsgenie_logo_url
    else:
        platform = None
        image_url = None
        oncalls = []
        priorities = []

    blocks = [
        {
            "type": "context",
            "elements": [
                {
                    "type": "image",
                    "image_url": image_url,
                    "alt_text": platform,
                },
            ],
        },
        {
            "type": "section",
            "block_id": "pager_team_select",
            "text": {
                "type": "mrkdwn",
                "text": "Choose a team to page:",
            },
            "accessory": {
                "action_id": "update_pager_selected_team",
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Team...",
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": i,
                        },
                        "value": i,
                    }
                    for i in oncalls
                ],
            },
        },
        {
            "type": "section",
            "block_id": "pager_priority_select",
            "text": {
                "type": "mrkdwn",
                "text": "Choose an urgency:",
            },
            "accessory": {
                "action_id": "update_pager_selected_priority",
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Urgency...",
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": i,
                        },
                        "value": i,
                    }
                    for i in priorities
                ],
            },
        },
        {
            "type": "section",
            "block_id": "pager_incident_select",
            "text": {
                "type": "mrkdwn",
                "text": "Choose an incident:",
            },
            "accessory": {
                "action_id": "update_pager_selected_incident",
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Incident...",
                },
                "options": [
                    (
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "None",
                                "emoji": True,
                            },
                            "value": "none",
                        }
                        if len(IncidentDatabaseInterface.list_open()) == 0
                        else {
                            "text": {
                                "type": "plain_text",
                                "text": inc.channel_name,
                                "emoji": True,
                            },
                            "value": f"{inc.channel_name}/{inc.channel_id}",
                        }
                    )
                    for inc in IncidentDatabaseInterface.list_open()
                    if inc.status
                    != [
                        status
                        for status, config in settings.statuses.items()
                        if config.final
                    ][0]
                ],
            },
        },
    ]

    client.views_open(
        # Pass a valid trigger_id within 3 seconds of receiving it
        trigger_id=body["trigger_id"],
        # View payload
        view={
            "type": "modal",
            "callback_id": "pager_modal",
            "title": {
                "type": "plain_text",
                "text": f"Page a team in {platform}",
            },
            "blocks": (
                blocks
                if (
                    settings.integrations
                    and settings.integrations.pagerduty
                    and settings.integrations.pagerduty.enabled
                )
                or (
                    settings.integrations
                    and settings.integrations.atlassian
                    and settings.integrations.atlassian.opsgenie
                    and settings.integrations.atlassian.opsgenie.enabled
                )
                else [
                    {
                        "type": "section",
                        "block_id": "pager_disabled",
                        "text": {
                            "type": "mrkdwn",
                            "text": "No pager integrations are enabled.",
                        },
                    },
                ]
            ),
        },
    )


@app.action("update_pager_selected_incident")
def update_modal(ack, body, client):
    # Acknowledge the button request
    ack()

    parsed = parse_modal_values(body)
    incident = parsed.get("update_pager_selected_incident")
    incident_channel_name = incident.split("/")[0]
    incident_channel_id = incident.split("/")[1]
    priority = parsed.get("update_pager_selected_priority")
    team = parsed.get("update_pager_selected_team")

    if (
        settings.integrations
        and settings.integrations.pagerduty
        and settings.integrations.pagerduty.enabled
    ):
        platform = "PagerDuty"
        artifact = "incident"
    elif (
        settings.integrations
        and settings.integrations.atlassian
        and settings.integrations.atlassian.opsgenie
        and settings.integrations.atlassian.opsgenie.enabled
    ):
        platform = "Opsgenie"
        artifact = "alert"

    # Call views_update with the built-in client
    client.views_update(
        # Pass the view_id
        view_id=body["view"]["id"],
        # String that represents view state to protect against race conditions
        hash=body["view"]["hash"],
        # View payload with updated blocks
        view={
            "type": "modal",
            "callback_id": "pager_modal",
            "title": {
                "type": "plain_text",
                "text": f"Page a team in {platform}",
            },
            "submit": {"type": "plain_text", "text": "Page"},
            "blocks": [
                {
                    "type": "section",
                    "block_id": "pager_info",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*You have selected the following options - please review them carefully.*\n\n"
                        + f"Once you click Submit, an {artifact} will be created in {platform} for the team listed here and they will be paged. "
                        + "They will also be invited to the incident's Slack channel.",
                    },
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "block_id": f"team/{team}",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Team:* _{team}_",
                    },
                },
                {
                    "type": "section",
                    "block_id": f"priority/{priority}",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Urgency:* _{priority}_",
                    },
                },
                {
                    "type": "section",
                    "block_id": f"incident/{incident_channel_name}/{incident_channel_id}",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Incident:* _{incident_channel_name}_",
                    },
                },
            ],
        },
    )


@app.action("update_pager_selected_team")
def handle_static_action(ack, body, logger):  # noqa: F811
    ack()
    logger.debug(body)


@app.action("update_pager_selected_priority")
def handle_static_action(ack, body, logger):  # noqa: F811
    ack()
    logger.debug(body)


@app.view("pager_modal")
def handle_submission(ack, body, say, view):  # noqa: F811
    """
    Handles pager
    """

    ack()

    team = view["blocks"][2]["block_id"].split("/")[1]
    priority = view["blocks"][3]["block_id"].split("/")[1]
    incident_channel_name = view["blocks"][4]["block_id"].split("/")[1]
    incident_channel_id = view["blocks"][4]["block_id"].split("/")[2]
    paging_user = body["user"]["name"]

    if (
        settings.integrations
        and settings.integrations.pagerduty
        and settings.integrations.pagerduty.enabled
    ):
        from incidentbot.configuration.settings import pagerduty_logo_url
        from incidentbot.pagerduty.api import PagerDutyInterface

        pagerduty_interface = PagerDutyInterface(escalation_policy=team)

        platform = "PagerDuty"
        artifact = "incident"
    elif (
        settings.integrations
        and settings.integrations.atlassian
        and settings.integrations.atlassian.opsgenie
        and settings.integrations.atlassian.opsgenie.enabled
    ):
        from incidentbot.configuration.settings import opsgenie_logo_url
        from incidentbot.opsgenie import api as og_api

        platform = "Opsgenie"
        artifact = "alert"

    try:
        match platform.lower():
            case "pagerduty":
                image_url = pagerduty_logo_url
                url = pagerduty_interface.page(
                    priority=priority,
                    channel_name=incident_channel_name,
                    channel_id=incident_channel_id,
                    paging_user=paging_user,
                )
            case "opsgenie":
                image_url = opsgenie_logo_url
                sess = og_api.OpsgenieAPI()
                sess.create_alert(
                    channel_name=incident_channel_name,
                    channel_id=incident_channel_id,
                    paging_user=paging_user,
                    priority=priority,
                    responders=[team],
                )

        outgoing = f"The team `{team}` has been paged to respond to this {artifact} via {platform} at the request of *{paging_user}*."

        blocks = [
            {
                "type": "context",
                "elements": [
                    {
                        "type": "image",
                        "image_url": image_url,
                        "alt_text": platform,
                    },
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": outgoing,
                },
            },
        ]

        if url:
            blocks.append(
                {
                    "block_id": "buttons",
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "View",
                            },
                            "style": "primary",
                            "url": url,
                            "action_id": "view_upstream_incident",
                        },
                    ],
                }
            )
        say(
            channel=incident_channel_id,
            text=outgoing,
            blocks=blocks,
        )
    except Exception as error:
        say(
            channel=incident_channel_id,
            text=f":robot_face::heart_on_fire: Looks like I encountered an error issuing that page: `{error}`",
        )


"""
Timeline
"""


@app.action("incident_timeline_modal")
def show_modal(ack, body, client):  # noqa: F811
    # Acknowledge the command request
    ack()

    # Format incident list
    database_data = IncidentDatabaseInterface.list_open()

    # Call views_open with the built-in client
    client.views_open(
        # Pass a valid trigger_id within 3 seconds of receiving it
        trigger_id=body["trigger_id"],
        # View payload
        view={
            "type": "modal",
            "callback_id": "incident_timeline_modal",
            "title": {"type": "plain_text", "text": "Incident timeline"},
            "blocks": [
                (
                    {
                        "type": "section",
                        "block_id": "incident_timeline_incident_select",
                        "text": {
                            "type": "mrkdwn",
                            "text": "Choose an incident to add an event to:",
                        },
                        "accessory": {
                            "action_id": "update_timeline_selected_incident",
                            "type": "static_select",
                            "placeholder": {
                                "type": "plain_text",
                                "text": "Incident...",
                            },
                            "options": [
                                {
                                    "text": {
                                        "type": "plain_text",
                                        "text": inc.channel_name,
                                        "emoji": True,
                                    },
                                    "value": f"{inc.channel_name}/{inc.channel_id}",
                                }
                                for inc in database_data
                                if inc.status
                                != [
                                    status
                                    for status, config in settings.statuses.items()
                                    if config.final
                                ][0]
                            ],
                        },
                    }
                    if len(database_data) != 0
                    else {
                        "type": "section",
                        "block_id": "no_incidents",
                        "text": {
                            "type": "mrkdwn",
                            "text": "There are currently no open incidents.\n\nYou can only add timeline events to open incidents.",
                        },
                    }
                )
            ],
        },
    )


@app.action("update_timeline_selected_incident")
def update_modal(ack, body, client):  # noqa: F811
    # Acknowledge the button request
    ack()

    parsed = parse_modal_values(body)
    incident = parsed.get("update_timeline_selected_incident")
    incident_channel_name = incident.split("/")[0]
    base_blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": incident_channel_name,
            },
        },
        {
            "type": "section",
            "block_id": "timeline_info",
            "text": {
                "type": "mrkdwn",
                "text": "Add a new event to the incident's timeline.",
            },
        },
        {"type": "divider"},
        {
            "type": "input",
            "block_id": "date",
            "element": {
                "type": "datepicker",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select a date",
                    "emoji": True,
                },
                "action_id": "update_timeline_date",
            },
            "label": {"type": "plain_text", "text": "Date", "emoji": True},
        },
        {
            "type": "input",
            "block_id": "time",
            "element": {
                "type": "timepicker",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select time",
                    "emoji": True,
                },
                "action_id": "update_timeline_time",
            },
            "label": {"type": "plain_text", "text": "Time", "emoji": True},
        },
        {
            "type": "input",
            "block_id": "text",
            "element": {
                "type": "plain_text_input",
                "action_id": "update_timeline_text",
            },
            "label": {"type": "plain_text", "text": "Text", "emoji": True},
        },
    ]

    # Call views_update with the built-in client
    client.views_update(
        # Pass the view_id
        view_id=body["view"]["id"],
        # String that represents view state to protect against race conditions
        hash=body["view"]["hash"],
        # View payload with updated blocks
        view={
            "type": "modal",
            "callback_id": "incident_timeline_modal_add",
            "title": {"type": "plain_text", "text": "Incident timeline"},
            "submit": {"type": "plain_text", "text": "Add"},
            "blocks": base_blocks,
        },
    )


@app.action("update_timeline_date")
def handle_static_action(ack, body, logger):  # noqa: F811
    ack()
    logger.debug(body)


@app.action("update_timeline_time")
def handle_static_action(ack, body, logger):  # noqa: F811
    ack()
    logger.debug(body)


@app.action("update_timeline_text")
def handle_static_action(ack, body, logger):  # noqa: F811
    ack()
    logger.debug(body)


@app.view("incident_timeline_modal_add")
def handle_submission(ack, body, say, view):  # noqa: F811
    """
    Handles
    """
    ack()

    parsed = parse_modal_values(body)
    channel_name = view["blocks"][0]["text"]["text"]
    event_date = parsed.get("update_timeline_date")
    event_time = parsed.get("update_timeline_time")
    event_text = parsed.get("update_timeline_text")
    ts = datetime.strptime(f"{event_date} {event_time}", "%Y-%m-%d %H:%M")

    record = IncidentDatabaseInterface.get_one(channel_name=channel_name)

    try:
        EventLogHandler.create(
            event=event_text,
            incident_id=record.id,
            incident_slug=record.slug,
            source="user",
            timestamp=ts,
            user=body["user"]["id"],
        )
    except Exception as error:
        logger.error(error)
    finally:
        say(
            channel=record.channel_id,
            text=f"Event added to timeline: {ts} - {event_text}",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"> {ts} - {event_text} (added to timeline)",
                    },
                },
            ],
        )


"""
Statuspage
"""


@app.action("statuspage_incident_modal")
def show_modal(ack, body, client):  # noqa: F811
    """
    Provides the modal that will display when the shortcut is
    used to start a Statuspage incident
    """

    user = body.get("user").get("id")
    channel_id = body.get("actions")[0].get("value").split("_")[-1:][0]
    incident_data = IncidentDatabaseInterface.get_one(channel_id=channel_id)

    blocks = [
        {
            "type": "image",
            "image_url": statuspage_logo_url,
            "alt_text": "statuspage",
        },
        {"type": "divider"},
        {
            "type": "section",
            "block_id": incident_data.slug,
            "text": {
                "type": "mrkdwn",
                "text": f"Incident: {incident_data.slug.upper()}",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "This Statuspage incident will start in "
                + "*investigating* mode. You may change its status as the "
                + "incident proceeds.",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Please enter a brief description that will appear "
                + "as the incident description in the Statuspage incident. "
                + "Then select impacted components and confirm. Once "
                + "confirmed, the incident will be opened.",
            },
        },
        {"type": "divider"},
        {
            "type": "input",
            "block_id": "statuspage_name_input",
            "element": {
                "type": "plain_text_input",
                "action_id": "statuspage.name_input",
                "min_length": 1,
            },
            "label": {
                "type": "plain_text",
                "text": "Name for the incident",
                "emoji": True,
            },
        },
        {
            "type": "input",
            "block_id": "statuspage_body_input",
            "element": {
                "type": "plain_text_input",
                "action_id": "statuspage.body_input",
                "min_length": 1,
            },
            "label": {
                "type": "plain_text",
                "text": "Message describing the incident",
                "emoji": True,
            },
        },
        {
            "block_id": "statuspage_impact_select",
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Impact:*"},
            "accessory": {
                "type": "static_select",
                "action_id": "statuspage.impact_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select an impact...",
                    "emoji": True,
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Minor",
                            "emoji": True,
                        },
                        "value": "minor",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Major",
                            "emoji": True,
                        },
                        "value": "major",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Critical",
                            "emoji": True,
                        },
                        "value": "critical",
                    },
                ],
            },
        },
        {
            "block_id": "statuspage_components_status",
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Components Impact:*"},
            "accessory": {
                "type": "static_select",
                "action_id": "statuspage.components_status_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select status of components...",
                    "emoji": True,
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Degraded Performance",
                            "emoji": True,
                        },
                        "value": "degraded_performance",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Partial Outage",
                            "emoji": True,
                        },
                        "value": "partial_outage",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Major Outage",
                            "emoji": True,
                        },
                        "value": "major_outage",
                    },
                ],
            },
        },
        {
            "type": "section",
            "block_id": "statuspage_components_select",
            "text": {
                "type": "mrkdwn",
                "text": "Select impacted components",
            },
            "accessory": {
                "action_id": "statuspage.components_select",
                "type": "multi_static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select components",
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": c,
                        },
                        "value": c,
                    }
                    for c in StatuspageComponents().list_of_names
                ],
            },
        },
    ]

    ack()

    # Return modal only if user has permissions
    if (
        settings.integrations.atlassian.statuspage.permissions
        and settings.integrations.atlassian.statuspage.permissions.groups
    ):
        for (
            group
        ) in settings.integrations.atlassian.statuspage.permissions.groups:
            if check_user_in_group(user_id=user, group_name=group):
                client.views_open(
                    trigger_id=body["trigger_id"],
                    view={
                        "type": "modal",
                        "callback_id": "statuspage_incident_modal",
                        "title": {
                            "type": "plain_text",
                            "text": "Statuspage Incident",
                        },
                        "submit": {"type": "plain_text", "text": "Start"},
                        "blocks": blocks,
                    },
                )
            else:
                client.chat_postEphemeral(
                    channel=channel_id,
                    user=user,
                    text="You don't have permissions to manage Statuspage incidents.",
                )
    else:
        client.views_open(
            trigger_id=body["trigger_id"],
            view={
                "type": "modal",
                "callback_id": "statuspage_incident_modal",
                "title": {
                    "type": "plain_text",
                    "text": "Statuspage Incident",
                },
                "submit": {"type": "plain_text", "text": "Start"},
                "blocks": blocks,
            },
        )


@app.view("statuspage_incident_modal")
def handle_submission(ack, body, client, view):  # noqa: F811
    """
    Handles statuspage_incident_modal
    """

    ack()
    slug = view["blocks"][2].get("block_id")
    incident_data = IncidentDatabaseInterface.get_one(slug=slug)

    # Fetch parameters from modal
    parsed = parse_modal_values(body)

    ibody = parsed.get("statuspage.body_input")
    impact = parsed.get("statuspage.impact_select")
    name = parsed.get("statuspage.name_input")
    status = parsed.get("statuspage.components_status_select")
    selected_components = parsed.get("statuspage.components_select")

    # Create Statuspage incident
    incident = StatuspageIncident(
        channel_id=incident_data.channel_id,
        request_data={
            "name": name,
            "status": "investigating",
            "body": ibody,
            "impact": impact,
            "components": StatuspageComponents().formatted_components_update(
                selected_components, status
            ),
        },
    )

    message_ts = incident.start()

    client.chat_update(
        channel=incident_data.channel_id,
        ts=message_ts,
        text="Statuspage incident has been created.",
        blocks=StatuspageIncidentUpdate.update_management_message(
            incident_data.channel_id
        ),
    )


@app.action("statuspage_incident_update_modal")
def show_modal(ack, body, client):  # noqa: F811
    """
    Provides the modal that will display when the shortcut is used to update a Statuspage incident
    """

    user = body.get("user").get("id")
    channel_id = body.get("channel").get("id")
    incident_data = IncidentDatabaseInterface.get_one(channel_id=channel_id)

    record = IncidentDatabaseInterface.get_statuspage_incident_record(
        id=incident_data.id
    )

    blocks = [
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
                "text": "*Name*: {}\n*Status*: {}\nLast Updated: {}\n".format(
                    record.name,
                    record.status,
                    record.updated_at,
                ),
            },
        },
        {"type": "divider"},
        {
            "type": "input",
            "block_id": f"statuspage_update_message_input_{channel_id}",
            "element": {
                "type": "plain_text_input",
                "action_id": "statuspage.update_message_input",
                "min_length": 1,
            },
            "label": {
                "type": "plain_text",
                "text": "Message to include with this update",
                "emoji": True,
            },
        },
        {
            "block_id": "statuspage_incident_status_management",
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Update Status:*"},
            "accessory": {
                "type": "static_select",
                "action_id": "statuspage.update_status",
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
    ]

    ack()

    # Return modal only if user has permissions
    if (
        settings.integrations.atlassian.statuspage.permissions
        and settings.integrations.atlassian.statuspage.permissions.groups
    ):
        for (
            group
        ) in settings.integrations.atlassian.statuspage.permissions.groups:
            if check_user_in_group(user_id=user, group_name=group):
                client.views_open(
                    trigger_id=body["trigger_id"],
                    view={
                        "type": "modal",
                        # View identifier
                        "callback_id": "statuspage_incident_update_modal",
                        "title": {
                            "type": "plain_text",
                            "text": "Update Incident",
                        },
                        "submit": {"type": "plain_text", "text": "Update"},
                        "blocks": blocks,
                    },
                )
            else:
                client.chat_postEphemeral(
                    channel=channel_id,
                    user=user,
                    text="You don't have permissions to manage Statuspage incidents.",
                )
    else:
        client.views_open(
            trigger_id=body["trigger_id"],
            view={
                "type": "modal",
                # View identifier
                "callback_id": "statuspage_incident_update_modal",
                "title": {
                    "type": "plain_text",
                    "text": "Update Incident",
                },
                "submit": {"type": "plain_text", "text": "Update"},
                "blocks": blocks,
            },
        )


@app.view("statuspage_incident_update_modal")
def handle_submission(ack, body):  # noqa: F811
    """
    Handles statuspage_incident_update_modal
    """

    ack()

    channel_id = (
        body.get("view").get("blocks")[4].get("block_id").split("_")[-1:][0]
    )
    values = body.get("view").get("state").get("values")
    update_message = (
        values.get(f"statuspage_update_message_input_{channel_id}")
        .get("statuspage.update_message_input")
        .get("value")
    )
    update_status = (
        values.get("statuspage_incident_status_management")
        .get("statuspage.update_status")
        .get("selected_option")
        .get("value")
    )

    try:
        StatuspageIncidentUpdate().update(
            channel_id=channel_id, message=update_message, status=update_status
        )
    except Exception as error:
        logger.error(f"Error updating Statuspage incident: {error}")


"""
Jira
"""


@app.action("incident_create_jira_issue_modal")
def show_modal(ack, body, client):  # noqa: F811
    """
    Provides the modal that will display when the shortcut is used to create a Jira issue
    """

    incident_id = body.get("channel").get("id")
    from incidentbot.jira.api import JiraApi

    j = JiraApi()

    blocks = [
        {
            "type": "header",
            "block_id": incident_id,
            "text": {
                "type": "plain_text",
                "text": "Create a Jira Issue",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "This issue will be created in the project: *{}*".format(
                    settings.integrations.atlassian.jira.project
                ),
            },
        },
        {"type": "divider"},
        {
            "type": "input",
            "block_id": "jira_issue_summary_input",
            "element": {
                "type": "plain_text_input",
                "action_id": "jira.summary_input",
                "min_length": 1,
            },
            "label": {
                "type": "plain_text",
                "text": "Issue Summary",
                "emoji": True,
            },
        },
        {
            "type": "input",
            "block_id": "jira_issue_description_input",
            "element": {
                "type": "plain_text_input",
                "action_id": "jira.description_input",
                "min_length": 1,
            },
            "label": {
                "type": "plain_text",
                "text": "Issue Description",
                "emoji": True,
            },
        },
        {
            "block_id": "jira_issue_type_select",
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Issue Type:*"},
            "accessory": {
                "type": "static_select",
                "action_id": "jira.type_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": j.issue_types[0],
                    "emoji": True,
                },
                "initial_option": {
                    "text": {
                        "type": "plain_text",
                        "text": j.issue_types[0],
                    },
                    "value": j.issue_types[0],
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": issue_type,
                            "emoji": True,
                        },
                        "value": issue_type,
                    }
                    for issue_type in j.issue_types
                ],
            },
        },
        # {
        #     "block_id": "jira_issue_priority_select",
        #     "type": "section",
        #     "text": {"type": "mrkdwn", "text": "*Priority:*"},
        #     "accessory": {
        #         "type": "static_select",
        #         "action_id": "jira.priority_select",
        #         "placeholder": {
        #             "type": "plain_text",
        #             "text": j.priorities[0],
        #             "emoji": True,
        #         },
        #         "initial_option": {
        #             "text": {
        #                 "type": "plain_text",
        #                 "text": j.priorities[0],
        #             },
        #             "value": j.priorities[0],
        #         },
        #         "options": [
        #             {
        #                 "text": {
        #                     "type": "plain_text",
        #                     "text": priority,
        #                     "emoji": True,
        #                 },
        #                 "value": priority,
        #             }
        #             for priority in j.priorities
        #         ],
        #     },
        # },
    ]

    ack()
    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            # View identifier
            "callback_id": "incident_create_jira_issue_modal",
            "title": {
                "type": "plain_text",
                "text": "Jira Issue",
            },
            "submit": {"type": "plain_text", "text": "Create"},
            "blocks": blocks,
        },
    )


@app.view("incident_create_jira_issue_modal")
def handle_submission(ack, body, client):  # noqa: F811
    """
    Handles incident_create_jira_issue_modal
    """
    ack()
    channel_id = body.get("view").get("blocks")[0].get("block_id")
    parsed = parse_modal_values(body)

    try:
        incident_data = IncidentDatabaseInterface.get_one(
            channel_id=channel_id
        )

        issue_obj = JiraIssue(
            incident_id=incident_data.id,
            description=parsed.get("jira.description_input"),
            issue_type=parsed.get("jira.type_select"),
            # priority=parsed.get("jira.priority_select"),
            summary=parsed.get("jira.summary_input"),
        )

        resp = issue_obj.new()

        if resp is not None:
            issue_link = "{}/browse/{}".format(
                settings.ATLASSIAN_API_URL, resp.get("key")
            )

            jira_issue_record = JiraIssueRecord(
                key=resp.get("key"),
                parent=incident_data.id,
                status="Unassigned",
                url=issue_link,
            )

            with Session(engine) as session:
                session.add(jira_issue_record)
                session.commit()

            try:
                from incidentbot.slack.messages import BlockBuilder

                resp = client.chat_postMessage(
                    channel=channel_id,
                    blocks=BlockBuilder.jira_issue_message(
                        key=resp.get("key"),
                        summary=parsed.get("jira.summary_input"),
                        type=parsed.get("jira.type_select"),
                        link=issue_link,
                    ),
                    text="A Jira issue has been created for this incident: {}".format(
                        resp.get("self")
                    ),
                )
                client.pins_add(
                    channel=resp.get("channel"),
                    timestamp=resp.get("ts"),
                )
            except Exception as error:
                logger.error(
                    f"Error sending Jira issue message for {incident_data.id}: {error}"
                )
        else:
            resp = client.chat_postMessage(
                channel=channel_id,
                text="Hmmm.. that didn't work. Check my logs for more information.",
            )
    except Exception as error:
        logger.error(error)
