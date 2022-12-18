import config
import datetime
import logging
import re
import slack_sdk.errors

from bot.audit import log
from bot.external import epi, meetings
from bot.incident.templates import (
    build_digest_notification,
    build_incident_channel_boilerplate,
)
from bot.models.incident import (
    db_update_incident_created_at_col,
    db_update_incident_sp_ts_col,
    db_write_incident,
)
from bot.models.pager import read_pager_auto_page_targets
from bot.settings.im import (
    conference_bridge_link,
    incident_channel_topic,
)
from bot.shared import tools
from bot.slack.client import slack_web_client, slack_workspace_id
from bot.statuspage import slack as sp_slack, handler as sp_handler
from threading import Thread
from typing import Dict

logger = logging.getLogger(__name__)

# How many total characters are allowed in a Slack channel?
channel_name_length_cap = 80
# How many characters does the incident prefix take up?
channel_name_prefix_length = len("inc-20211116-")
# How long can the provided description be?
incident_description_max_length = (
    channel_name_length_cap - channel_name_prefix_length
)
# Which external providers are supported? Ones not in this list will error.
enabled_providers = [
    "auth0",
    "github",
    "heroku",
]

if not config.is_test_environment:
    from bot.slack.client import invite_user_to_channel


class Incident:
    """Instantiates an incident"""

    def __init__(self, request_parameters: Dict[str, str]):
        self.request_parameters = request_parameters
        # Log transaction
        self.log()
        # Set instance variables
        self.incident_description = self.request_parameters[
            "incident_description"
        ]
        self.channel_name = self.__format_channel_name()
        self.conference_bridge = self.__generate_conference_link()
        if not config.is_test_environment:
            self.channel = self.__create_incident_channel()
            self.channel_details = self.channel.get("channel")
            self.created_channel_details = {
                "incident_description": self.request_parameters[
                    "incident_description"
                ],
                "id": self.channel_details.get("id"),
                "name": self.channel_details.get("name"),
                "is_security_incident": self.request_parameters[
                    "is_security_incident"
                ]
                in ("True", "true", True),
            }
        else:
            self.channel_details = {}
            self.created_channel_details = {
                "name": self.channel_details.get("name"),
                "is_security_incident": False,
            }

    def log(self):
        request_log = {
            "user": self.request_parameters["user"],
            "channel": self.request_parameters["channel"],
            "incident_description": self.request_parameters[
                "incident_description"
            ],
        }
        logger.info(
            f"Request received from Slack to start a new incident: {request_log}"
        )

    def __create_incident_channel(self):
        """
        Create incident channel in Slack for an incident
        """
        try:
            # Call the conversations.create method using the WebClient
            # conversations_create requires the channels:manage bot scope
            channel = slack_web_client.conversations_create(
                # The name of the conversation
                name=self.channel_name
            )
            # Log the result which includes information like the ID of the conversation
            logger.debug(f"\n{channel}\n")
            logger.info(f"Creating incident channel: {self.channel_name}")
        except slack_sdk.errors.SlackApiError as error:
            logger.error(f"Error creating incident channel: {error}")
        return channel

    def __format_channel_name(self) -> str:
        # Remove any special characters (allow only alphanumeric)
        formatted_channel_name_suffix = re.sub(
            "[^A-Za-z0-9\s]",
            "",
            self.incident_description,
        )
        # Replace any spaces with dashes
        formatted_channel_name_suffix = formatted_channel_name_suffix.replace(
            " ", "-"
        ).lower()
        now = datetime.datetime.now()
        return f"inc-{now.year}{now.month}{now.day}{now.hour}{now.minute}-{formatted_channel_name_suffix}"

    def __generate_conference_link(self):
        if config.auto_create_zoom_meeting in ("True", "true", True):
            return meetings.ZoomMeeting().url
        else:
            return conference_bridge_link


"""
Core Functionality
"""


def create_incident(
    request_parameters: Dict[str, str],
    internal: bool = False,
) -> str:
    """
    Create an incident
    """

    """
    Return formatted incident channel name
    Typically inc-datefmt-topic
    """
    incident_description = request_parameters["incident_description"]
    user = request_parameters["user"]
    severity = request_parameters["severity"] or "sev4"
    if incident_description != "":
        if len(incident_description) < incident_description_max_length:
            incident = Incident(request_parameters)
            created_channel_details = incident.created_channel_details
            """
            Notify incidents digest channel (#incidents)
            """
            digest_message_content = build_digest_notification(
                created_channel_details, severity, incident.conference_bridge
            )
            try:
                digest_message = slack_web_client.chat_postMessage(
                    **digest_message_content,
                    text="",
                )
                logger.debug(f"\n{digest_message}\n")
            except slack_sdk.errors.SlackApiError as error:
                logger.error(
                    f"Error sending message to incident digest channel: {error}"
                )
            logger.info(
                "Sending message to digest channel for: {}".format(
                    created_channel_details["name"]
                )
            )
            """
            Set incident channel topic
            """
            topic_boilerplate = incident_channel_topic
            try:
                topic = slack_web_client.conversations_setTopic(
                    channel=created_channel_details["id"],
                    topic=topic_boilerplate,
                )
                logger.debug(f"\n{topic}\n")
            except slack_sdk.errors.SlackApiError as error:
                logger.error(f"Error setting incident channel topic: {error}")
            """
            Send boilerplate info to incident channel
            """
            bp_message_content = build_incident_channel_boilerplate(
                created_channel_details, severity
            )
            try:
                bp_message = slack_web_client.chat_postMessage(
                    **bp_message_content,
                    text="",
                )
                logger.debug(f"\n{bp_message}\n")
            except slack_sdk.errors.SlackApiError as error:
                logger.error(
                    f"Error sending message to incident channel: {error}"
                )
            # Pin the boilerplate message to the channel for quick access.
            slack_web_client.pins_add(
                channel=created_channel_details["id"],
                timestamp=bp_message["ts"],
            )
            """
            Post conference link in the channel upon creation
            """
            try:
                conference_bridge_message = slack_web_client.chat_postMessage(
                    channel=created_channel_details["id"],
                    text="",
                    blocks=[
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": ":busts_in_silhouette: Please join the conference here.",
                            },
                        },
                        {"type": "divider"},
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"{incident.conference_bridge}",
                            },
                        },
                    ],
                )
                slack_web_client.pins_add(
                    channel=created_channel_details["id"],
                    timestamp=conference_bridge_message["message"]["ts"],
                )
            except slack_sdk.errors.SlackApiError as error:
                logger.error(
                    f"Error sending conference bridge link to channel: {error}"
                )
            """
            Write incident entry to database
            """
            logger.info(
                "Writing incident entry to database for {}...".format(
                    created_channel_details["name"]
                )
            )
            try:
                db_write_incident(
                    incident_id=created_channel_details["name"],
                    channel_id=created_channel_details["id"],
                    channel_name=created_channel_details["name"],
                    status="investigating",
                    severity=severity,
                    bp_message_ts=bp_message["ts"],
                    dig_message_ts=digest_message["ts"],
                    is_security_incident=created_channel_details[
                        "is_security_incident"
                    ],
                    channel_description=created_channel_details[
                        "incident_description"
                    ],
                    conference_bridge=incident.conference_bridge,
                )
            except Exception as error:
                logger.fatal(f"Error writing entry to database: {error}")
            # Tag the incident with initial creation timestamp in human readable format
            try:
                db_update_incident_created_at_col(
                    incident_id=created_channel_details["name"],
                    created_at=tools.fetch_timestamp(),
                )
            except Exception as error:
                logger.fatal(
                    f"Error updating incident entry with creation timestamp: {error}"
                )
            # Handle optionals in a thread to avoid breaking the 3000ms limit for Slack slash commands
            thr = Thread(
                target=handle_incident_optional_features,
                args=[request_parameters, created_channel_details, internal],
            )
            thr.start()
            # Invite the user who opened the channel to the channel.
            invite_user_to_channel(created_channel_details["id"], user)
            # Return for view method
            temp_channel_id = created_channel_details["id"]

            # Write audit log
            log.write(
                incident_id=created_channel_details["name"],
                event="Incident created.",
                user=user,
            )
            return f"I've created the incident channel: <#{temp_channel_id}>"
        else:
            return f"Total channel length cannot exceed 80 characters. Please use a short description less than {incident_description_max_length} characters. You used {len(incident_description)}."
    else:
        return "Please provide a description for the channel."


def handle_incident_optional_features(
    request_parameters: Dict[str, str],
    created_channel_details: Dict[str, str],
    internal: bool = False,
):
    """
    For new incidents, handle optional features
    """
    channel_id = created_channel_details["id"]
    channel_name = created_channel_details["name"]

    """
    Invite required participants (optional)
    """
    if config.incident_auto_group_invite_enabled in ("True", "true", True):
        all_groups = slack_web_client.all_workspace_groups["usergroups"]
        group_to_invite = config.incident_auto_group_invite_group_name
        if len(all_groups) == 0:
            logger.error(
                f"Error when inviting mandatory users: looked for group {group_to_invite} but did not find it."
            )
        else:
            try:
                required_participants_group = [
                    g for g in all_groups if g["handle"] == group_to_invite
                ][0]["id"]
                required_participants_group_members = (
                    slack_web_client.usergroups_users_list(
                        usergroup=required_participants_group,
                    )
                )["users"]
            except Exception as error:
                logger.error(
                    f"Error when formatting automatic invitees group name: {error}"
                )
            try:
                invite = slack_web_client.conversations_invite(
                    channel=channel_id,
                    users=",".join(required_participants_group_members),
                )
                logger.debug(f"\n{invite}\n")
                # Write audit log
                log.write(
                    incident_id=created_channel_details["name"],
                    event=f"Group {required_participants_group} invited to the incident channel automatically.",
                )
            except slack_sdk.errors.SlackApiError as error:
                logger.error(f"Error when inviting mandatory users: {error}")

    """
    External provider statuses (optional)
    """
    if config.incident_external_providers_enabled in ("True", "true", True):
        for p in config.incident_external_providers_list:
            ext_incidents = epi.ExternalProviderIncidents(
                provider=p,
                days_back=5,
                slack_channel=channel_id,
            )
            if p not in enabled_providers:
                logger.error(
                    f"Error sending external provider message to incident channel: {p} is not a valid provider - options are {enabled_providers}"
                )
            else:
                try:
                    pu_message = slack_web_client.chat_postMessage(
                        **ext_incidents.slack_message(),
                        text="",
                    )
                    logger.debug(f"\n{pu_message}\n")
                except slack_sdk.errors.SlackApiError as error:
                    logger.error(
                        f"Error sending external provider message to incident channel: {error}"
                    )

    """
    Post prompt for creating Statuspage incident (optional)
    """
    if config.statuspage_integration_enabled in ("True", "true", True):
        sp_components = sp_handler.StatuspageComponents()
        sp_components_list = sp_components.list_of_names()
        sp_starter_message_content = sp_slack.return_new_incident_message(
            channel_id, sp_components_list
        )
        try:
            sp_starter_message = slack_web_client.chat_postMessage(
                **sp_starter_message_content,
                text="",
            )
            slack_web_client.pins_add(
                channel=channel_id,
                timestamp=sp_starter_message["ts"],
            )
        except slack_sdk.errors.SlackApiError as error:
            logger.error(
                f"Error sending Statuspage prompt to the incident channel {channel_name}: {error}"
            )
        logger.info(f"Sending Statuspage prompt to {channel_name}.")
        # Update incident record with the Statuspage starter message timestamp
        logger.info(
            "Updating incident record in database with Statuspage message timestamp."
        )
        try:
            db_update_incident_sp_ts_col(
                channel_name,
                sp_starter_message["ts"],
            )
        except Exception as error:
            logger.fatal(f"Error writing entry to database: {error}")

    """
    If this is an internal incident, parse additional values
    """
    if internal and config.incident_auto_create_from_react_enabled in (
        "True",
        "true",
        True,
    ):
        original_channel = request_parameters["channel"]
        original_message_timestamp = request_parameters[
            "original_message_timestamp"
        ]
        formatted_timestamp = str.replace(original_message_timestamp, ".", "")
        link_to_message = f"https://{slack_workspace_id}.slack.com/archives/{original_channel}/p{formatted_timestamp}"
        try:
            slack_web_client.chat_postMessage(
                channel=channel_id,
                text="",
                blocks=[
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": ":warning: This incident was created via a reaction to a message.",
                        },
                    },
                    {"type": "divider"},
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"Here is a link to the original message: <{link_to_message}>",
                        },
                    },
                ],
            )
        except slack_sdk.errors.SlackApiError as error:
            logger.error(
                f"Error sending additional information to the incident channel {channel_name}: {error}"
            )
        logger.info(f"Sending additional information to {channel_name}.")
        # Message the channel where the react request came from to inform
        # regarding incident channel creation
        try:
            slack_web_client.chat_postMessage(
                channel=original_channel,
                text="",
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"I've created the incident channel as requested: <#{channel_id}>",
                        },
                    },
                ],
            )
        except slack_sdk.errors.SlackApiError as error:
            logger.error(
                f"Error when trying to let {channel_name} know about an auto created incident: {error}"
            )
    """
    Page groups that are required to be automatically paged (optional)
    """
    if config.pagerduty_integration_enabled in ("True", "true", True):
        from bot.pagerduty import api as pd_api

        auto_page_targets = read_pager_auto_page_targets()
        if len(auto_page_targets) != 0:
            for i in auto_page_targets:
                for k, v in i.items():
                    logger.info(
                        f"Creating page for {k} since this team was included in auto_page_targets..."
                    )
                    # Write audit log
                    log.write(
                        incident_id=created_channel_details["name"],
                        event=f"Created PagerDuty incident for team {k}.",
                    )
                    pd_api.page(
                        ep_name=v,
                        priority="low",
                        channel_name=created_channel_details["name"],
                        channel_id=created_channel_details["id"],
                        paging_user="auto",
                    )
