import logging
import requests

from __main__ import app, config
from flask import request
from slack import errors
from threading import Thread
from typing import Dict
from ..db import db
from ..external import epi
from ..slack import slack_tools
from ..statuspage import slack as spslack, statuspage
from .incident import (
    Incident,
    build_digest_notification,
    build_topic,
    build_incident_channel_boilerplate,
)

logger = logging.getLogger(__name__)

# How many total characters are allowed in a Slack channel?
channel_name_length_cap = 80
# How many characters does the incident prefix take up?
channel_name_prefix_length = len("inc-20211116-")
# How long can the provided description be?
channel_description_max_length = channel_name_length_cap - channel_name_prefix_length
# Which external providers are supported? Ones not in this list will error.
enabled_providers = [
    "auth0",
    "github",
    "heroku",
]


# Route for handling inboud requests to create incidents
@app.route("/hooks/incident", methods=["POST"])
def incident():
    # Parse parameters from request
    request_parameters = {
        "channel": request.form.get("channel_name"),
        "channel_description": request.form.get("text"),
        "descriptor": request.form.get("text"),
        "response_url": request.form.get("response_url"),
        "user": request.form.get("user_name"),
        "token": request.form.get("token"),
        "created_from_web": request.form.get("created_from_web", default=False),
    }
    # Pass to method to create incident
    resp = create_incident(request_parameters)
    # View methods must return, so this gets sent back to the user
    return resp


def create_incident(
    request_parameters: Dict[str, str],
    internal: bool = False,
) -> str:
    """
    Create an incident
    """
    if request_parameters["token"] == slack_tools.verification_token or internal:
        """
        Return formatted incident channel name
        Typically inc-datefmt-topic
        """
        channel_description = request_parameters["channel_description"]
        channel = request_parameters["channel"]
        descriptor = request_parameters["descriptor"]
        user = request_parameters["user"]

        if channel_description != "":
            if len(channel_description) < channel_description_max_length:
                incident = Incident(
                    request_data={
                        "descriptor": descriptor,
                        "channel": channel,
                        "user": user,
                    }
                )
                fmt_channel_name = incident.return_channel_name()

                """
                Create incident channel
                """
                try:
                    # Call the conversations.create method using the WebClient
                    # conversations_create requires the channels:manage bot scope
                    channel = slack_tools.slack_web_client.conversations_create(
                        # The name of the conversation
                        name=fmt_channel_name
                    )
                    # Log the result which includes information like the ID of the conversation
                    logger.debug(f"\n{channel}\n")
                    logger.info(f"Creating incident channel: {fmt_channel_name}")
                except errors.SlackApiError as error:
                    logger.error(f"Error creating incident channel: {error}")

                # Used by subsequent actions.
                createdChannelDetails = {
                    "id": channel["channel"]["id"],
                    "name": channel["channel"]["name"],
                }

                """
                Notify incidents digest channel (#incidents)
                """
                digest_message_content = build_digest_notification(
                    createdChannelDetails
                )
                try:
                    digest_message = slack_tools.slack_web_client.chat_postMessage(
                        **digest_message_content
                    )
                    logger.debug(f"\n{digest_message}\n")
                except errors.SlackApiError as error:
                    logger.error(
                        f"Error sending message to incident digest channel: {error}"
                    )
                logger.info(
                    f"Sending message to digest channel for: {fmt_channel_name}"
                )

                """
                Set incident channel topic
                """
                topic_boilerplate = build_topic()
                try:
                    topic = slack_tools.slack_web_client.conversations_setTopic(
                        channel=channel["channel"]["id"],
                        topic=topic_boilerplate,
                    )
                    logger.debug(f"\n{topic}\n")
                except errors.SlackApiError as error:
                    logger.error(f"Error setting incident channel topic: {error}")

                """
                Send boilerplate info to incident channel
                """
                bp_message_content = build_incident_channel_boilerplate(
                    createdChannelDetails
                )
                try:
                    bp_message = slack_tools.slack_web_client.chat_postMessage(
                        **bp_message_content
                    )
                    logger.debug(f"\n{bp_message}\n")
                except errors.SlackApiError as error:
                    logger.error(f"Error sending message to incident channel: {error}")
                # Pin the boilerplate message to the channel for quick access.
                slack_tools.slack_web_client.pins_add(
                    channel=createdChannelDetails["id"],
                    timestamp=bp_message["ts"],
                )

                """
                Write incident entry to database
                """
                logger.info(
                    f"Writing incident entry to database for {fmt_channel_name}..."
                )
                try:
                    db.db_write_incident(
                        fmt_channel_name,
                        channel["channel"]["id"],
                        channel["channel"]["name"],
                        "investigating",
                        "sev4",
                        bp_message["ts"],
                        digest_message["ts"],
                    )
                except Exception as error:
                    logger.fatal(f"Error writing entry to database: {error}")

                # Handle optionals in a thread to avoid breaking the 3000ms limit for Slack slash commands
                thr = Thread(
                    target=handle_incident_optional_features,
                    args=[request_parameters, createdChannelDetails, internal],
                )
                thr.start()

                # Return for view method
                temp_channel_id = createdChannelDetails["id"]
                return f"I've created the incident channel: <#{temp_channel_id}>"
            else:
                return f"Total channel length cannot exceed 80 characters. Please use a short description less than {channel_description_max_length} characters. You used {len(channel_description)}."
        else:
            return "Please provide a short description for the channel. For example: /incident foo"
    else:
        return "Tokens don't match."


def response_helper(response_url: str, response: str, incident_id: str):
    response_json = {
        "text": response,
    }
    resp = requests.post(response_url, json=response_json)
    logger.info(
        f"Sending via response_url during bootstrap for {incident_id}: {resp.text}"
    )


def handle_incident_optional_features(
    request_parameters: Dict[str, str],
    createdChannelDetails: Dict[str, str],
    internal: bool = False,
):
    """
    For new incidents, handle optional features
    """
    channel_id = createdChannelDetails["id"]
    channel_name = createdChannelDetails["name"]
    created_from_web = request_parameters["created_from_web"]
    if internal or created_from_web:
        pass
    else:
        response_helper(
            response_url=request_parameters["response_url"],
            response=f"I will continue to work on options in the background if any were enabled. I'm here if you need me!",
            incident_id=channel_name,
        )

    """
    Invite required participants (optional)
    """
    if config.incident_auto_group_invite_enabled == "true":
        all_groups = slack_tools.all_workspace_groups["usergroups"]
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
                    slack_tools.slack_web_client.usergroups_users_list(
                        usergroup=required_participants_group,
                    )
                )["users"]
            except Exception as error:
                logger.error(
                    f"Error when formatting automatic invitees group name: {error}"
                )
            try:
                invite = slack_tools.slack_web_client.conversations_invite(
                    channel=channel_id,
                    users=",".join(required_participants_group_members),
                )
                logger.debug(f"\n{invite}\n")
            except errors.SlackApiError as error:
                logger.error(f"Error when inviting mandatory users: {error}")

    """
    External provider statuses (optional)
    """
    if config.incident_external_providers_enabled == "true":
        providers = str.split(str.lower(config.incident_external_providers_list), ",")
        for p in providers:
            ext_incidents = epi.ExternalProviderIncidents(
                provider=p,
                days_back=5,
                slack_channel=channel_id,
            )
            if p not in enabled_providers:
                logger.error(
                    f"Error sending external provider message to incident channel: {p} is not a valid provider - options are {enabled_providers}"
                )
                if internal or created_from_web:
                    pass
                else:
                    response_helper(
                        response_url=request_parameters["response_url"],
                        response=f"I was unable to send status updates for the following provider - verify compatibility: {p}",
                        incident_id=channel_name,
                    )
            else:
                try:
                    pu_message = slack_tools.slack_web_client.chat_postMessage(
                        **ext_incidents.slack_message()
                    )
                    logger.debug(f"\n{pu_message}\n")
                except errors.SlackApiError as error:
                    logger.error(
                        f"Error sending external provider message to incident channel: {error}"
                    )

    """
    Post prompt for creating Statuspage incident
    """
    if config.statuspage_integration_enabled == "true":
        sp_components = statuspage.StatuspageComponents()
        sp_components_list = sp_components.list_of_names()
        sp_starter_message_content = spslack.return_new_incident_message(
            channel_id, sp_components_list
        )
        try:
            sp_starter_message = slack_tools.slack_web_client.chat_postMessage(
                **sp_starter_message_content
            )
        except errors.SlackApiError as error:
            logger.error(
                f"Error sending Statuspage prompt to the incident channel {channel_name}: {error}"
            )
        logger.info(f"Sending Statuspage prompt to {channel_name}.")
        # Update incident record with the Statuspage starter message timestamp
        logger.info(
            "Updating incident record in database with Statuspage message timestamp."
        )
        try:
            db.db_update_incident_sp_ts_col(
                channel_name,
                sp_starter_message["ts"],
            )
        except Exception as error:
            logger.fatal(f"Error writing entry to database: {error}")

    """
    If this is an internal incident, parse additional values
    """
    if internal and config.incident_auto_create_from_react_enabled == "true":
        original_channel = request_parameters["channel"]
        original_message_timestamp = request_parameters["original_message_timestamp"]
        formatted_timestamp = str.replace(original_message_timestamp, ".", "")
        link_to_message = f"https://${config.slack_workspace_id}.slack.com/archives/{original_channel}/p{formatted_timestamp}"
        try:
            slack_tools.slack_web_client.chat_postMessage(
                channel=channel_id,
                blocks=[
                    {"type": "divider"},
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
        except errors.SlackApiError as error:
            logger.error(
                f"Error sending additional information to the incident channel {channel_name}: {error}"
            )
        logger.info(f"Sending additional information to {channel_name}.")
        # Message the channel where the react request came from to inform
        # regarding incident channel creation
        try:
            slack_tools.slack_web_client.chat_postMessage(
                channel=original_channel,
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
        except errors.SlackApiError as error:
            logger.error(
                f"Error when trying to let {channel_name} know about an auto created incident: {error}"
            )
