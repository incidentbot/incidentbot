import logging
import os

from __main__ import app
from flask import request
from slack import errors
from ..db import db
from ..core import slack_tools
from ..external import external
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
    "github",
    "heroku",
]


@app.route("/hooks/incident", methods=["POST"])
def incident():
    if request.form["token"] == slack_tools.verification_token:
        """
        Return formatted incident channel name
        Typically inc-datefmt-topic
        """
        channel_description = request.form["text"]
        if channel_description != "":
            if len(channel_description) < channel_description_max_length:
                return_message = """
                """
                incident = Incident(
                    request_data={
                        "descriptor": request.form["text"],
                        "channel": request.form.get("channel_name"),
                        "user": request.form.get("user_name"),
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
                channel_name = createdChannelDetails["name"]
                logger.info(f"Sending message to digest channel for: {channel_name}")

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
                logger.info(f"Writing incident entry to database for {channel_name}...")
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

                """
                Invite required participants (optional)
                """
                if os.getenv("INCIDENT_AUTO_GROUP_INVITE_ENABLED") == "true":
                    groups = slack_tools.all_workspace_groups["usergroups"]
                    group_to_invite = os.getenv("INCIDENT_AUTO_GROUP_INVITE_GROUP_NAME")
                    if len(groups) == 0:
                        logger.error(
                            f"Error when inviting mandatory users: looked for group {group_to_invite} but did not find it."
                        )
                        return_message = (
                            return_message
                            + f"\nI tried to invite the group {group_to_invite} but I was unable to. Does that group exist?"
                        )
                    else:
                        try:
                            required_participants_group = [
                                g for g in groups if g["name"] == group_to_invite
                            ][0]["id"]
                            required_participants_group_members = (
                                slack_tools.slack_web_client.usergroups_users_list(
                                    usergroup=required_participants_group,
                                )
                            )["users"]
                        except Exception as error:
                            logger.error(
                                f"Error when inviting mandatory users: {error}"
                            )
                        try:
                            invite = slack_tools.slack_web_client.conversations_invite(
                                channel=channel["channel"]["id"],
                                users=",".join(required_participants_group_members),
                            )
                            logger.debug(f"\n{invite}\n")
                        except errors.SlackApiError as error:
                            logger.error(
                                f"Error when inviting mandatory users: {error}"
                            )
                        return_message = (
                            return_message
                            + f"\nI invited the group {group_to_invite} to the channel."
                        )

                """
                External provider statuses (optional)
                """
                if os.getenv("INCIDENT_EXTERNAL_PROVIDERS_ENABLED") == "true":
                    providers = str.split(
                        str.lower(os.getenv("INCIDENT_EXTERNAL_PROVIDERS_LIST")), ","
                    )
                    for p in providers:
                        if p not in enabled_providers:
                            logger.error(
                                f"Error sending external provider message to incident channel: {p} is not a valid provider - options are {enabled_providers}"
                            )
                            return_message = (
                                return_message
                                + f"\nI was unable status updates for the following provider - verify compatibility: {p}"
                            )
                        else:
                            pu_message_content = (
                                external.build_incident_channel_provider_updates(
                                    createdChannelDetails["id"], p
                                )
                            )
                            try:
                                pu_message = (
                                    slack_tools.slack_web_client.chat_postMessage(
                                        **pu_message_content
                                    )
                                )
                                logger.debug(f"\n{pu_message}\n")
                            except errors.SlackApiError as error:
                                logger.error(
                                    f"Error sending external provider message to incident channel: {error}"
                                )
                            return_message = (
                                return_message
                                + f"\nI've posted status updates for the following provider: {p}"
                            )

                """
                Post prompt for creating Statuspage incident
                """
                if os.getenv("STATUSPAGE_INTEGRATION_ENABLED") == "true":
                    sp_components = statuspage.StatuspageComponents()
                    sp_components_list = sp_components.list_of_names()
                    sp_starter_message_content = spslack.return_new_incident_message(
                        createdChannelDetails["id"], sp_components_list
                    )
                    try:
                        sp_starter_message = (
                            slack_tools.slack_web_client.chat_postMessage(
                                **sp_starter_message_content
                            )
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
                            fmt_channel_name,
                            sp_starter_message["ts"],
                        )
                    except Exception as error:
                        logger.fatal(f"Error writing entry to database: {error}")

                """
                Notify user who ran command
                """
                return_message = (
                    return_message
                    + "\nI've created the incident channel: <#{}>".format(
                        createdChannelDetails["id"]
                    )
                )
                return return_message
            else:
                return f"Total channel length cannot exceed 80 characters. Please use a short description less than {channel_description_max_length} characters. You used {len(channel_description)}."
        else:
            return "Please provide a short description for the channel. For example: /incident foo"
    else:
        return "Tokens don't match."
