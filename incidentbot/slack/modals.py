from incidentbot.configuration.settings import (
    settings,
    statuspage_logo_url,
)
from incidentbot.version import APP_VERSION
from incidentbot.incident.core import Incident, IncidentRequestParameters
from incidentbot.jira.issue import JiraIssue
from incidentbot.gitlab.issue import GitLabIncident
from incidentbot.logging import logger
from incidentbot.models.database import (
    engine,
    ApplicationData,
    JiraIssueRecord,
    GitlabIssueRecord,
)
from incidentbot.models.incident import IncidentDatabaseInterface
from incidentbot.slack.client import check_user_in_group, get_digest_channel_id
from incidentbot.slack.handler import app
from incidentbot.slack.messages import BlockBuilder, IncidentUpdate
from incidentbot.phare.handler import (
    PhareIncident,
    PhareIncidentUpdate,
    PhareMonitors,
)
from incidentbot.statuspage.handler import (
    StatuspageComponents,
    StatuspageIncident,
    StatuspageIncidentUpdate,
)
from incidentbot.slack.util import parse_modal_values
from incidentbot.util import gen
from sqlmodel import Session, select


def _open_modal_if_permitted(
    client,
    body: dict,
    view: dict,
    channel_id: str,
    user: str,
    permissions,
    unauthorized_text: str,
) -> None:
    """Open a modal gated behind group membership.

    If `permissions` has groups, the modal opens only when the user belongs to
    at least one of them; otherwise it opens unconditionally.
    """
    if permissions and permissions.groups:
        if any(
            check_user_in_group(user_id=user, group_name=group)
            for group in permissions.groups
        ):
            client.views_open(trigger_id=body["trigger_id"], view=view)
        else:
            client.chat_postEphemeral(
                channel=channel_id,
                user=user,
                text=unauthorized_text,
            )
    else:
        client.views_open(trigger_id=body["trigger_id"], view=view)


@app.event("app_home_opened")
def update_home_tab(client, event, logger):
    """
    Provide information via the app's home screen
    """

    base_blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Declare a new incident below or use `{settings.root_slash_command}` anywhere in Slack.",
            },
        },
        {
            "type": "actions",
            "elements": [
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
            ],
        },
        {"type": "divider"},
    ]

    database_data = IncidentDatabaseInterface.list_recent(
        limit=settings.options.show_most_recent_incidents_app_home_limit
    )
    open_incidents = BlockBuilder.incident_list(incidents=database_data)
    base_blocks.extend(open_incidents)

    base_blocks.append(
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Version {APP_VERSION}  ·  <https://docs.incidentbot.io/|Documentation>",
                }
            ],
        }
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
        logger.exception("error publishing home tab", error=e)


@app.action("declare_incident_modal")
def show_declare_incident_modal(ack, body, client):
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
def handle_declare_incident_submission(ack, body, client):
    """
    Handles declare_incident_modal
    """

    ack()
    parsed = parse_modal_values(body)
    user = body.get("user").get("id")
    components = parsed.get("incident.declare_incident_modal.set_components")
    if isinstance(components, list):
        components = " , ".join(components)
    # Create request parameters object
    try:
        incident = Incident(
            IncidentRequestParameters(
                additional_comms_channel=parsed.get(
                    "incident.declare_incident_modal.set_additional_comms_channel"
                ),
                incident_components=components,  # converted components to string
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

        incident.start()
    except Exception as error:
        logger.exception("error starting incident", error=error)


@app.action("incident_update_modal")
def show_incident_update_modal(ack, body, client):
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
                            not in [
                                status
                                for status, config in settings.statuses.items()
                                if config.final
                            ]
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
            if database_data
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
def handle_incident_update_submission(ack, body, client):
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
        logger.exception("error sending incident update", channel=inc.channel_name, error=error)


"""
Paging
"""


@app.action("pager")
@app.shortcut("pager")
def show_pager_modal(ack, body, client):
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
                    not in [
                        status
                        for status, config in settings.statuses.items()
                        if config.final
                    ]
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
def update_pager_incident_modal(ack, body, client):
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
def handle_pager_team_select(ack, body, logger):
    ack()
    logger.debug(body)


@app.action("update_pager_selected_priority")
def handle_pager_priority_select(ack, body, logger):
    ack()
    logger.debug(body)


@app.view("pager_modal")
def handle_pager_submission(ack, body, say, view):
    """
    Handles pager_modal
    """

    ack()

    # The updated modal encodes selected values in block_id fields with
    # prefixed keys: "team/{value}", "priority/{value}", "incident/{name}/{id}".
    # Look up by prefix so block reordering never silently reads the wrong field.
    _blocks_by_prefix: dict[str, str] = {}
    for _b in view["blocks"]:
        _bid = _b.get("block_id", "")
        for _prefix in ("team/", "priority/", "incident/"):
            if _bid.startswith(_prefix):
                _blocks_by_prefix[_prefix] = _bid
                break

    team = _blocks_by_prefix.get("team/", "/unknown").split("/", 1)[1]
    priority = _blocks_by_prefix.get("priority/", "/unknown").split("/", 1)[1]
    _incident_bid = _blocks_by_prefix.get("incident/", "incident/unknown/unknown")
    _, incident_channel_name, incident_channel_id = _incident_bid.split("/", 2)
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
Statuspage
"""


@app.action("statuspage_incident_modal")
def show_statuspage_incident_modal(ack, body, client):
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

    _open_modal_if_permitted(
        client=client,
        body=body,
        view={
            "type": "modal",
            "callback_id": "statuspage_incident_modal",
            "title": {"type": "plain_text", "text": "Statuspage Incident"},
            "submit": {"type": "plain_text", "text": "Start"},
            "blocks": blocks,
        },
        channel_id=channel_id,
        user=user,
        permissions=settings.integrations.atlassian.statuspage.permissions,
        unauthorized_text="You don't have permissions to manage Statuspage incidents.",
    )


@app.view("statuspage_incident_modal")
def handle_statuspage_incident_submission(ack, body, client, view):
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
def show_statuspage_incident_update_modal(ack, body, client):
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
                "text": f"*Name*: {record.name}\n*Status*: {record.status}\nLast Updated: {record.updated_at}\n",
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

    _open_modal_if_permitted(
        client=client,
        body=body,
        view={
            "type": "modal",
            "callback_id": "statuspage_incident_update_modal",
            "title": {"type": "plain_text", "text": "Update Incident"},
            "submit": {"type": "plain_text", "text": "Update"},
            "blocks": blocks,
        },
        channel_id=channel_id,
        user=user,
        permissions=settings.integrations.atlassian.statuspage.permissions,
        unauthorized_text="You don't have permissions to manage Statuspage incidents.",
    )


@app.view("statuspage_incident_update_modal")
def handle_statuspage_incident_update_submission(ack, body):
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
        logger.exception("error updating statuspage incident", error=error)


"""
Phare Uptime
"""


@app.action("phare_incident_modal")
def show_phare_incident_modal(ack, body, client):
    """
    Provides the modal that will display when the shortcut is
    used to start a Phare incident
    """

    user = body.get("user").get("id")
    channel_id = body.get("actions")[0].get("value").split("_")[-1:][0]
    incident_data = IncidentDatabaseInterface.get_one(channel_id=channel_id)

    try:
        phare_monitors = PhareMonitors()
        monitor_options = [
            {
                "text": {
                    "type": "plain_text",
                    "text": name,
                    "emoji": True,
                },
                "value": str(monitor_id),
            }
            for entry in phare_monitors.list_of_dict_name_ids
            for name, monitor_id in entry.items()
        ]
    except Exception as error:
        logger.exception("error fetching phare monitors", error=error)
        monitor_options = []

    blocks = [
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
                "text": "This Phare Uptime incident will start in *investigating* mode. "
                + "You may change its state as the incident proceeds.",
            },
        },
        {"type": "divider"},
        {
            "type": "input",
            "block_id": "phare_title_input",
            "element": {
                "type": "plain_text_input",
                "action_id": "phare.title_input",
                "min_length": 1,
            },
            "label": {
                "type": "plain_text",
                "text": "Title for the incident",
                "emoji": True,
            },
        },
        {
            "type": "input",
            "block_id": "phare_description_input",
            "element": {
                "type": "plain_text_input",
                "action_id": "phare.description_input",
                "min_length": 1,
            },
            "label": {
                "type": "plain_text",
                "text": "Description of the incident",
                "emoji": True,
            },
        },
        {
            "block_id": "phare_impact_select",
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Impact:*"},
            "accessory": {
                "type": "static_select",
                "action_id": "phare.impact_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select an impact...",
                    "emoji": True,
                },
                "options": [
                    {
                        "text": {"type": "plain_text", "text": "Operational", "emoji": True},
                        "value": "operational",
                    },
                    {
                        "text": {"type": "plain_text", "text": "Degraded Performance", "emoji": True},
                        "value": "degraded_performance",
                    },
                    {
                        "text": {"type": "plain_text", "text": "Partial Outage", "emoji": True},
                        "value": "partial_outage",
                    },
                    {
                        "text": {"type": "plain_text", "text": "Major Outage", "emoji": True},
                        "value": "major_outage",
                    },
                ],
            },
        },
    ]

    if monitor_options:
        blocks.append(
            {
                "type": "section",
                "block_id": "phare_monitors_select",
                "text": {
                    "type": "mrkdwn",
                    "text": "Select impacted monitors",
                },
                "accessory": {
                    "action_id": "phare.monitors_select",
                    "type": "multi_static_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select monitors",
                    },
                    "options": monitor_options,
                },
            }
        )

    blocks.append(
        {
            "type": "input",
            "block_id": "phare_exclude_from_downtime",
            "optional": True,
            "element": {
                "type": "checkboxes",
                "action_id": "phare.exclude_from_downtime",
                "options": [
                    {
                        "text": {"type": "plain_text", "text": "Exclude from downtime calculations"},
                        "value": "exclude",
                    }
                ],
            },
            "label": {"type": "plain_text", "text": "Downtime", "emoji": True},
        }
    )

    ack()

    _open_modal_if_permitted(
        client=client,
        body=body,
        view={
            "type": "modal",
            "callback_id": "phare_incident_modal",
            "title": {"type": "plain_text", "text": "Phare Uptime Incident"},
            "submit": {"type": "plain_text", "text": "Start"},
            "blocks": blocks,
        },
        channel_id=channel_id,
        user=user,
        permissions=settings.integrations.phare.permissions,
        unauthorized_text="You don't have permissions to manage Phare Uptime incidents.",
    )


@app.view("phare_incident_modal")
def handle_phare_incident_submission(ack, body, client, view):
    """
    Handles phare_incident_modal submission
    """

    ack()
    slug = view["blocks"][1].get("block_id")
    incident_data = IncidentDatabaseInterface.get_one(slug=slug)

    parsed = parse_modal_values(body)

    title = parsed.get("phare.title_input")
    description = parsed.get("phare.description_input")
    impact = parsed.get("phare.impact_select")
    selected_monitors_raw = parsed.get("phare.monitors_select") or []
    monitors = [int(m) for m in selected_monitors_raw] if selected_monitors_raw else []
    exclude_from_downtime = "exclude" in (parsed.get("phare.exclude_from_downtime") or [])

    incident = PhareIncident(
        request_data={
            "channel_id": incident_data.channel_id,
            "title": title,
            "description": description,
            "impact": impact,
            "monitors": monitors,
            "exclude_from_downtime": exclude_from_downtime,
        }
    )

    message_ts = incident.start()

    if message_ts:
        client.chat_update(
            channel=incident_data.channel_id,
            ts=message_ts,
            text="Phare Uptime incident has been created.",
            blocks=PhareIncidentUpdate.update_management_message(
                incident_data.channel_id
            ),
        )


@app.action("phare_incident_update_modal")
def show_phare_incident_update_modal(ack, body, client):
    """
    Provides the modal that will display when the shortcut is used to update a Phare incident
    """

    user = body.get("user").get("id")
    channel_id = body.get("channel").get("id")
    incident_data = IncidentDatabaseInterface.get_one(channel_id=channel_id)

    record = IncidentDatabaseInterface.get_phare_incident_record(id=incident_data.id)

    blocks = [
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Name*: {record.name}\n*State*: {record.state}\nLast Updated: {record.updated_at}\n",
            },
        },
        {"type": "divider"},
        {
            "type": "input",
            "block_id": f"phare_update_content_input_{channel_id}",
            "element": {
                "type": "plain_text_input",
                "action_id": "phare.update_content_input",
                "min_length": 1,
            },
            "label": {
                "type": "plain_text",
                "text": "Message to include with this update",
                "emoji": True,
            },
        },
        {
            "block_id": "phare_incident_state_management",
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Update State:*"},
            "accessory": {
                "type": "static_select",
                "action_id": "phare.update_status",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Investigating",
                    "emoji": True,
                },
                "options": [
                    {
                        "text": {"type": "plain_text", "text": "Investigating", "emoji": True},
                        "value": "investigating",
                    },
                    {
                        "text": {"type": "plain_text", "text": "Identified", "emoji": True},
                        "value": "identified",
                    },
                    {
                        "text": {"type": "plain_text", "text": "Monitoring", "emoji": True},
                        "value": "monitoring",
                    },
                    {
                        "text": {"type": "plain_text", "text": "Resolved", "emoji": True},
                        "value": "resolved",
                    },
                ],
            },
        },
        {
            "block_id": "phare_incident_impact_management",
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Update Impact:*"},
            "accessory": {
                "type": "static_select",
                "action_id": "phare.update_impact",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Leave unchanged",
                    "emoji": True,
                },
                "options": [
                    {
                        "text": {"type": "plain_text", "text": "Operational", "emoji": True},
                        "value": "operational",
                    },
                    {
                        "text": {"type": "plain_text", "text": "Degraded Performance", "emoji": True},
                        "value": "degraded_performance",
                    },
                    {
                        "text": {"type": "plain_text", "text": "Partial Outage", "emoji": True},
                        "value": "partial_outage",
                    },
                    {
                        "text": {"type": "plain_text", "text": "Major Outage", "emoji": True},
                        "value": "major_outage",
                    },
                    {
                        "text": {"type": "plain_text", "text": "Maintenance", "emoji": True},
                        "value": "maintenance",
                    },
                    {
                        "text": {"type": "plain_text", "text": "Unknown", "emoji": True},
                        "value": "unknown",
                    },
                ],
            },
        },
    ]

    ack()

    _open_modal_if_permitted(
        client=client,
        body=body,
        view={
            "type": "modal",
            "callback_id": "phare_incident_update_modal",
            "title": {"type": "plain_text", "text": "Update Incident"},
            "submit": {"type": "plain_text", "text": "Update"},
            "blocks": blocks,
        },
        channel_id=channel_id,
        user=user,
        permissions=settings.integrations.phare.permissions,
        unauthorized_text="You don't have permissions to manage Phare Uptime incidents.",
    )


@app.view("phare_incident_update_modal")
def handle_phare_incident_update_submission(ack, body):
    """
    Handles phare_incident_update_modal
    """

    ack()

    channel_id = (
        body.get("view").get("blocks")[3].get("block_id").split("_")[-1:][0]
    )
    values = body.get("view").get("state").get("values")
    content = (
        values.get(f"phare_update_content_input_{channel_id}")
        .get("phare.update_content_input")
        .get("value")
    )
    state = (
        values.get("phare_incident_state_management")
        .get("phare.update_status")
        .get("selected_option")
        .get("value")
    )
    impact_option = (
        values.get("phare_incident_impact_management", {})
        .get("phare.update_impact", {})
        .get("selected_option")
    )
    impact = impact_option.get("value") if impact_option else None

    try:
        PhareIncidentUpdate.update(
            channel_id=channel_id, content=content, state=state
        )
    except Exception as error:
        logger.exception("error updating phare incident", error=error)

    if impact:
        try:
            PhareIncidentUpdate.update_impact(channel_id=channel_id, impact=impact)
        except Exception as error:
            logger.exception("error updating phare incident impact", error=error)


"""
Jira
"""


@app.action("incident_create_jira_issue_modal")
def show_jira_issue_modal(ack, body, client):
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
                "text": f"This issue will be created in the project: *{settings.integrations.atlassian.jira.project}*",
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
def handle_jira_issue_submission(ack, body, client):
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
                logger.exception("error sending jira issue message", incident_id=incident_data.id, error=error)
        else:
            resp = client.chat_postMessage(
                channel=channel_id,
                text="Hmmm.. that didn't work. Check my logs for more information.",
            )
    except Exception as error:
        logger.exception("error creating jira issue", error=error)


"""
Gitlab
"""


@app.action("incident_create_gitlab_incident_modal")
def show_gitlab_incident_modal(ack, body, client):
    """
    Provides the modal that will display when the shortcut is used to create a Gitlab issue
    """

    incident_id = body.get("channel").get("id")

    # Get the incident record
    incident_data = IncidentDatabaseInterface.get_one(channel_id=incident_id)

    blocks = [
        {
            "type": "header",
            "block_id": incident_id,
            "text": {
                "type": "plain_text",
                "text": f"Create a Gitlab {settings.integrations.gitlab.issue_type.title()}",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"This incident will be created in the project: *{settings.integrations.gitlab.project_id}*",
            },
        },
        {"type": "divider"},
        {
            "type": "input",
            "block_id": "gitlab_incident_summary_input",
            "element": {
                "type": "plain_text_input",
                "action_id": "gitlab.summary_input",
                "min_length": 1,
                "initial_value": incident_data.channel_name,
            },
            "label": {
                "type": "plain_text",
                "text": "Issue Summary",
                "emoji": True,
            },
        },
        {
            "type": "input",
            "block_id": "gitlab_incident_description_input",
            "element": {
                "type": "plain_text_input",
                "action_id": "gitlab.description_input",
                "min_length": 1,
                "initial_value": incident_data.description,
            },
            "label": {
                "type": "plain_text",
                "text": "Issue Description",
                "emoji": True,
            },
        },
        # TODO: Add checkbox to make the issue confidential
    ]

    ack()
    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            # View identifier
            "callback_id": "incident_create_gitlab_incident_modal",
            "title": {
                "type": "plain_text",
                "text": f"Gitlab {settings.integrations.gitlab.issue_type.title()}",
            },
            "submit": {"type": "plain_text", "text": "Create"},
            "blocks": blocks,
        },
    )


@app.view("incident_create_gitlab_incident_modal")
def handle_gitlab_incident_submission(ack, body, client):
    """
    Handles incident_create_gitlab_incident_modal
    """
    ack()
    channel_id = body.get("view").get("blocks")[0].get("block_id")
    parsed = parse_modal_values(body)

    try:
        incident_data = IncidentDatabaseInterface.get_one(
            channel_id=channel_id
        )

        issue_obj = GitLabIncident(
            incident_id=incident_data.id,
            description=parsed.get("gitlab.description_input"),
            summary=parsed.get("gitlab.summary_input"),
            status=incident_data.status,
            severity=incident_data.severity,
        )

        resp = issue_obj.new()

        if resp is not None:
            issue_link = resp.get("web_url")

            gitlab_incident_record = GitlabIssueRecord(
                id=resp.get("id"),
                iid=resp.get("iid"),
                parent=incident_data.id,
                status="Unassigned",
                url=issue_link,
            )

            with Session(engine) as session:
                session.add(gitlab_incident_record)
                session.commit()

            try:
                from incidentbot.slack.messages import BlockBuilder

                resp = client.chat_postMessage(
                    channel=channel_id,
                    blocks=BlockBuilder.gitlab_incident_message(
                        id=resp.get("id"),
                        summary=parsed.get("gitlab.summary_input"),
                        link=issue_link,
                    ),
                    text="A Gitlab issue has been created for this incident: {}".format(
                        resp.get("self")
                    ),
                )
                client.pins_add(
                    channel=resp.get("channel"),
                    timestamp=resp.get("ts"),
                )
            except Exception as error:
                logger.exception("error sending gitlab issue message", incident_id=incident_data.id, error=error)
        else:
            resp = client.chat_postMessage(
                channel=channel_id,
                text="Hmmm.. that didn't work. Check my logs for more information.",
            )
    except Exception as error:
        logger.exception("error creating gitlab issue", error=error)
