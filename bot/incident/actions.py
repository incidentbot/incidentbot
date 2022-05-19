import config
import logging
import re
import slack_sdk.errors

from bot.confluence import rca
from bot.db import db
from bot.external import epi
from bot.scheduler import scheduler
from bot.shared import tools
from bot.slack import client as slack_client
from . import action_parameters as ap, incident
from .incident import invite_user_to_channel
from typing import Any, Dict


logger = logging.getLogger(__name__)
log_level = config.log_level


"""
Functions for handling inbound actions
"""


def add_on_call_to_channel(action_parameters: type[ap.ActionParameters]):
    """When an incoming action is incident.add_on_call_to_channel, this method
    invites a selected user to an incident channel

    Keyword arguments:
    action_parameters -- type[ap.ActionParameters] containing Slack actions data
    """
    actions = action_parameters.actions()
    p = action_parameters.parameters()
    user_id = actions["selected_option"]["value"]
    # Invite selected user
    invite_user_to_channel(p["channel_id"], user_id)


def assign_role(action_parameters: type[ap.ActionParameters]):
    """When an incoming action is incident.assign_role, this method
    assigns the role to the user provided in the input

    Keyword arguments:
    action_parameters -- type[ap.ActionParameters] containing Slack actions data
    """
    p = action_parameters.parameters()
    channel_name = p["channel_name"]

    user = action_parameters.actions()["selected_user"]
    action_value = "_".join(action_parameters.actions()["block_id"].split("_")[1:3])
    # Find the index of the block that contains info on
    # the role we want to update
    blocks = action_parameters.message_details()["blocks"]
    index = tools.find_index_in_list(blocks, "block_id", f"role_{action_value}")
    # Replace the "_none_" value in the given block
    temp_new_role_name = action_value.replace("_", " ")
    new_role_name = temp_new_role_name.title()
    blocks[index]["text"]["text"] = f"*{new_role_name}*:\n <@{user}>"
    # Update the message
    slack_client.slack_web_client.chat_update(
        channel=p["channel_id"],
        ts=p["timestamp"],
        blocks=blocks,
    )
    # Send update notification message to incident channel
    message = incident.build_role_update(p["channel_id"], new_role_name, user)
    try:
        result = slack_client.slack_web_client.chat_postMessage(**message, text="")
        if log_level == "DEBUG":
            logger.debug(f"\n{result}\n")
    except slack_sdk.errors.SlackApiError as error:
        logger.error(f"Error sending role update to the incident channel: {error}")
    # Let the user know they've been assigned the role and what to do
    dm = incident.build_user_role_notification(p["channel_id"], action_value, user)
    try:
        result = slack_client.slack_web_client.chat_postMessage(**dm, text="")
        if log_level == "DEBUG":
            logger.debug(f"\n{result}\n")
    except slack_sdk.errors.SlackApiError as error:
        logger.error(f"Error sending role description to user: {error}")
    logger.info(f"{user} was assigned {action_value} in {channel_name}")
    # Since the user was assigned the role, they should be auto invited.
    invite_user_to_channel(p["channel_id"], user)
    # Finally, updated the updated_at column
    update_incident_db_entry_ts(channel_name)


def claim_role(action_parameters: type[ap.ActionParameters]):
    """When an incoming action is incident.claim_role, this method
    assigns the role to the user that hit the claim button

    Keyword arguments:
    action_parameters -- type[ap.ActionParameters] containing Slack actions data
    """
    p = action_parameters.parameters()
    channel_name = p["channel_name"]

    action_value = action_parameters.actions()["value"]
    # Find the index of the block that contains info on
    # the role we want to update
    blocks = action_parameters.message_details()["blocks"]
    index = tools.find_index_in_list(blocks, "block_id", f"role_{action_value}")
    # Replace the "_none_" value in the given block
    temp_new_role_name = action_value.replace("_", " ")
    new_role_name = temp_new_role_name.title()
    user = p["user"]
    blocks[index]["text"]["text"] = f"*{new_role_name}*:\n <@{user}>"
    # Update the message
    slack_client.slack_web_client.chat_update(
        channel=p["channel_id"],
        ts=p["timestamp"],
        blocks=blocks,
    )
    # Send update notification message to incident channel
    message = incident.build_role_update(p["channel_id"], new_role_name, user)
    try:
        result = slack_client.slack_web_client.chat_postMessage(**message, text="")
        logger.debug(f"\n{result}\n")
    except slack_sdk.errors.SlackApiError as error:
        logger.error(f"Error sending role update to incident channel: {error}")
    # Let the user know they've been assigned the role and what to do
    dm = incident.build_user_role_notification(
        p["channel_id"],
        action_value,
        action_parameters.user_details()["id"],
    )
    try:
        result = slack_client.slack_web_client.chat_postMessage(**dm, text="")
        logger.debug(f"\n{result}\n")
    except slack_sdk.errors.SlackApiError as error:
        logger.error(f"Error sending role description to user: {error}")
    logger.info(f"{user} has claimed {action_value} in {channel_name}")
    # Finally, updated the updated_at column
    update_incident_db_entry_ts(channel_name)


def export_chat_logs(action_parameters: type[ap.ActionParameters]):
    """When an incoming action is incident.export_chat_logs, this method
    fetches channel history, formats it, and returns it to the channel

    Keyword arguments:
    action_parameters -- type[ap.ActionParameters] containing Slack actions data
    """
    p = action_parameters.parameters()
    channel_id = p["channel_id"]
    channel_name = p["channel_name"]

    # Retrieve channel history and post as text attachment
    history = slack_client.get_formatted_channel_history(
        channel_id=channel_id, channel_name=channel_name
    )
    try:
        logger.info(f"Sending chat transcript to {channel_name}.")
        result = slack_client.slack_web_client.files_upload(
            channels=channel_id,
            content=history,
            filename=f"{channel_name} Chat Transcript",
            filetype="txt",
            initial_comment="As requested, here is the chat transcript. Remember - while this is useful, it will likely need cultivation before being added to a postmortem.",
            title=f"{channel_name} Chat Transcript",
        )
        logger.debug(f"\n{result}\n")
    except slack_sdk.errors.SlackApiError as error:
        logger.error(f"Error sending message and attachment to {channel_name}: {error}")


def set_incident_status(
    action_parameters: type[ap.ActionParameters] = None,
    override_dict: Dict[str, Any] = {},
):
    """When an incoming action is incident.set_incident_status, this method
    updates the status of the incident

    Keyword arguments:
    action_parameters -- type[ap.ActionParameters] containing Slack actions data
    override_dict -- Avoid using action_parameters and manually set data

    This function has two methods of providing data from Slack because we can
    also use the webapp to update features.
    """
    if override_dict != {} and action_parameters == None:
        p = override_dict
        action_value = p["action_value"]
    else:
        p = action_parameters.parameters()
        action_value = action_parameters.actions()["selected_option"]["value"]

    channel_name = p["channel_name"]
    channel_id = p["channel_id"]
    incident_data = db.db_read_incident(incident_id=p["channel_name"])
    user = action_parameters.user_details()["id"]
    # We need this for later
    all_channels = slack_client.return_slack_channel_info()
    digest_channel_index = tools.find_index_in_list(
        all_channels, "name", config.incidents_digest_channel
    )
    digest_channel_id = all_channels[digest_channel_index]["id"]
    formatted_severity = extract_attribute(
        attribute="severity",
        channel=digest_channel_id,
        oldest=incident_data.dig_message_ts,
    )

    # If set to resolved, send additional information.
    if action_value == "resolved":
        # Set up steps for RCA channel
        message_blocks = action_parameters.message_details()["blocks"]
        # Extract names of required roles
        incident_commander = extract_role_owner(
            message_blocks, "role_incident_commander"
        )
        technical_lead = extract_role_owner(message_blocks, "role_technical_lead")
        # Error out if both roles aren't claimed
        for role, person in {
            "incident commander": incident_commander,
            "technical lead": technical_lead,
        }.items():
            if person == "_none_":
                try:
                    result = slack_client.slack_web_client.chat_postMessage(
                        channel=channel_id,
                        text=f":red_circle: <@{user}> Before this incident can be marked as resolved, the *{role}* role must be assigned. Please assign it and try again.",
                    )
                except slack_sdk.errors.SlackApiError as error:
                    logger.error(
                        f"Error sending note to {channel_name} regarding missing role claim: {error}"
                    )
                return
        # Create rca channel
        rca_channel_name = f"{channel_name}-rca"
        try:
            rca_channel = slack_client.slack_web_client.conversations_create(
                name=rca_channel_name
            )
            # Log the result which includes information like the ID of the conversation
            logger.debug(f"\n{rca_channel_name}\n")
            logger.info(f"Creating rca channel: {rca_channel_name}")
        except slack_sdk.errors.SlackApiError as error:
            logger.error(f"Error creating rca channel: {error}")
        # Invite incident commander and technical lead if they weren't empty
        rcaChannelDetails = {
            "id": rca_channel["channel"]["id"],
            "name": rca_channel["channel"]["name"],
        }
        # We want real user names to tag in the rca doc
        actual_user_names = []
        for person in [incident_commander, technical_lead]:
            if person != "_none_":
                str = person.replace("<", "").replace(">", "").replace("@", "")
                invite_user_to_channel(rcaChannelDetails["id"], str)
                # Get real name of user to be used to generate RCA
                actual_user_names.append(
                    slack_client.slack_web_client.users_info(user=str)["user"][
                        "profile"
                    ]["real_name"]
                )
            else:
                logger.error(
                    f"Cannot invite {person} to rca channel because the role was not claimed."
                )
        # Format boilerplate message to rca channel
        rca_boilerplate_message_blocks = [
            {"type": "divider"},
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":white_check_mark: Incident RCA Planning",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"You have been invited to this channel to assist with planning the RCA for <#{channel_id}>. The Incident Commander should invite anyone who can help contribute to the RCA and then use this channel to plan the meeting to go over the incident.",
                },
            },
        ]
        # Generate rca template and create rca if enabled
        # Get normalized description as rca title
        if config.auto_create_rca == "true":
            rca_title = " ".join(channel_name.split("-")[2:])
            rca_link = rca.create_rca(
                rca_title=rca_title,
                incident_commander=actual_user_names[0],
                technical_lead=actual_user_names[1],
                severity=formatted_severity,
                severity_definition=tools.read_json_from_file(
                    f"{config.templates_directory}severity_levels.json"
                )[formatted_severity],
            )
            rca_boilerplate_message_blocks.extend(
                [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*I have created a base RCA document that you can build on. You can open it using the button below.*",
                        },
                    },
                    {
                        "block_id": "buttons",
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "View RCA In Confluence",
                                },
                                "style": "primary",
                                "url": rca_link,
                                "action_id": "open_rca",
                            },
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "View Incident Channel",
                                },
                                "url": f"https://{config.slack_workspace_id}.slack.com/archives/{channel_id}",
                                "action_id": "incident.join_incident_channel",
                            },
                        ],
                    },
                    {"type": "divider"},
                ]
            )
        else:
            rca_boilerplate_message_blocks.extend(
                [
                    {
                        "block_id": "buttons",
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "View Incident Channel",
                                },
                                "url": f"https://{config.slack_workspace_id}.slack.com/archives/{channel_id}",
                                "action_id": "incident.join_incident_channel",
                            },
                        ],
                    },
                    {"type": "divider"},
                ]
            )
        try:
            blocks = rca_boilerplate_message_blocks
            result = slack_client.slack_web_client.chat_postMessage(
                channel=rcaChannelDetails["id"],
                blocks=blocks,
                text="",
            )
            logger.debug(f"\n{result}\n")
        except slack_sdk.errors.SlackApiError as error:
            logger.error(f"Error sending RCA update to RCA channel: {error}")

        # Send message to incident channel
        message = incident.build_post_resolution_message(channel_id, action_value)
        try:
            result = slack_client.slack_web_client.chat_postMessage(**message, text="")
            logger.debug(f"\n{result}\n")
        except slack_sdk.errors.SlackApiError as error:
            logger.error(
                f"Error sending resolution update to incident channel {channel_name}: {error}"
            )
        # Log
        logger.info(f"Sent resolution info to {channel_name}.")

    # Also updates digest message
    new_digest_message = incident.build_updated_digest_message(
        p["channel_name"], action_value, formatted_severity
    )
    try:
        slack_client.slack_web_client.chat_update(
            channel=digest_channel_id,
            ts=incident_data.dig_message_ts,
            blocks=new_digest_message["blocks"],
            text="",
        )
    except slack_sdk.errors.SlackApiError as e:
        logger.error(
            f"Error sending status update to incident channel {channel_name}: {error}"
        )

    # Change placeholder for select to match current status in boilerplate message
    result = slack_client.slack_web_client.conversations_history(
        channel=channel_id,
        inclusive=True,
        oldest=incident_data.bp_message_ts,
        limit=1,
    )
    blocks = result["messages"][0]["blocks"]
    status_block_index = tools.find_index_in_list(blocks, "block_id", "status")
    blocks[status_block_index]["accessory"]["initial_option"] = {
        "text": {
            "type": "plain_text",
            "text": action_value.title(),
            "emoji": True,
        },
        "value": action_value,
    }
    slack_client.slack_web_client.chat_update(
        channel=p["channel_id"],
        ts=p["timestamp"],
        blocks=blocks,
    )

    # Update incident record with the status
    logger.info(
        f"Updating incident record in database with new status for {channel_name}"
    )
    try:
        db.db_update_incident_status_col(
            channel_name,
            action_value,
        )
    except Exception as error:
        logger.fatal(f"Error updating entry in database: {error}")

    # See if there's a scheduled reminder job for the incident and delete it if so
    if action_value == "resolved":
        jobs = scheduler.process.list_jobs()
        if len(jobs) > 0:
            for job in jobs:
                job_title = f"{channel_name}_updates_reminder"
                if job.id == job_title:
                    delete_job = scheduler.process.delete_job(job_title)
                    if delete_job != None:
                        logger.error(
                            f"Could not delete the job {job_title}: {delete_job}"
                        )
                    else:
                        logger.info(f"Deleted job: {job_title}")

    # If the incident is resolved, disabled the select option to change it back
    if action_value == "resolved":
        result = slack_client.slack_web_client.conversations_history(
            channel=channel_id,
            inclusive=True,
            oldest=incident_data.bp_message_ts,
            limit=1,
        )
        blocks = result["messages"][0]["blocks"]
        status_block_index = tools.find_index_in_list(blocks, "block_id", "status")
        blocks[status_block_index]["accessory"]["confirm"] = {
            "title": {
                "type": "plain_text",
                "text": "This incident is already resolved.",
            },
            "text": {
                "type": "mrkdwn",
                "text": "Since this incident has already been resolved, it shouldn't be reopened. A new incident should be started instead.",
            },
            "confirm": {"type": "plain_text", "text": "Reopen Anyway"},
            "deny": {"type": "plain_text", "text": "Go Back"},
            "style": "danger",
        }
        slack_client.slack_web_client.chat_update(
            channel=p["channel_id"],
            ts=p["timestamp"],
            blocks=blocks,
        )
    # Log
    logger.info(f"Updated incident status for {channel_name} to {action_value}.")
    message = incident.build_status_update(channel_id, action_value)
    try:
        result = slack_client.slack_web_client.chat_postMessage(**message, text="")
        logger.debug(f"\n{result}\n")
    except slack_sdk.errors.SlackApiError as error:
        logger.error(
            f"Error sending status update to incident channel {channel_name}: {error}"
        )
    # Finally, updated the updated_at column
    update_incident_db_entry_ts(channel_name)


def reload_status_message(action_parameters: type[ap.ActionParameters]):
    """When an incoming action is incident.reload_status_message, this method
    checks an external provider's status page for updates

    Keyword arguments:
    action_parameters -- type[ap.ActionParameters] containing Slack actions data
    """
    p = action_parameters.parameters()
    ts = action_parameters.message_details()["ts"]
    channel_id = p["channel_id"]
    channel_name = p["channel_name"]
    provider = action_parameters.actions()["value"]

    # Fetch latest Status to format message
    ext_incidents = epi.ExternalProviderIncidents(
        provider=provider,
        days_back=5,
        slack_channel=channel_id,
    )
    # Delete existing message and repost
    try:
        result = slack_client.slack_web_client.chat_delete(
            channel=channel_id,
            ts=ts,
        )
        logger.debug(f"\n{result}\n")
    except slack_sdk.errors.SlackApiError as error:
        logger.error(
            f"Error deleting external provider message from channel {channel_name}: {error}"
        )
    # Post new message
    try:
        result = slack_client.slack_web_client.chat_postMessage(
            **ext_incidents.slack_message(),
            text="",
        )
        logger.debug(f"\n{result}\n")
    except slack_sdk.errors.SlackApiError as error:
        logger.error(
            f"Error sending external provider message to incident channel {channel_name}: {error}"
        )
    logger.info(
        f"Updated external provider message for {provider} in channel {channel_name}"
    )


def set_severity(
    action_parameters: type[ap.ActionParameters] = None,
    override_dict: Dict[str, Any] = {},
):
    """When an incoming action is incident.set_severity, this method
    updates the severity of the incident

    Keyword arguments:
    action_parameters -- type[ap.ActionParameters] containing Slack actions data
    override_dict -- Avoid using action_parameters and manually set data

    This function has two methods of providing data from Slack because we can
    also use the webapp to update features.
    """
    if override_dict != {} and action_parameters == None:
        p = override_dict
        action_value = p["action_value"]
    else:
        p = action_parameters.parameters()
        action_value = action_parameters.actions()["selected_option"]["value"]

    channel_name = p["channel_name"]
    channel_id = p["channel_id"]
    incident_data = db.db_read_incident(incident_id=p["channel_name"])

    # Also updates digest message
    channels = slack_client.return_slack_channel_info()
    index = tools.find_index_in_list(channels, "name", config.incidents_digest_channel)
    digest_channel_id = channels[index]["id"]
    # Retrieve the existing value of status since we need to put that back
    formatted_status = extract_attribute(
        attribute="status",
        channel=digest_channel_id,
        oldest=incident_data.dig_message_ts,
    )
    new_digest_message = incident.build_updated_digest_message(
        p["channel_name"], formatted_status, action_value
    )
    try:
        slack_client.slack_web_client.chat_update(
            channel=digest_channel_id,
            ts=incident_data.dig_message_ts,
            blocks=new_digest_message["blocks"],
        )
    except slack_sdk.errors.SlackApiError as error:
        logger.error(
            f"Error sending severity update to incident channel {channel_name}: {error}"
        )

    # Change placeholder for select to match current status in boilerplate message
    result = slack_client.slack_web_client.conversations_history(
        channel=channel_id,
        inclusive=True,
        oldest=incident_data.bp_message_ts,
        limit=1,
    )
    blocks = result["messages"][0]["blocks"]
    sev_blocks_index = tools.find_index_in_list(blocks, "block_id", "severity")
    blocks[sev_blocks_index]["accessory"]["initial_option"] = {
        "text": {
            "type": "plain_text",
            "text": action_value.upper(),
            "emoji": True,
        },
        "value": action_value,
    }
    slack_client.slack_web_client.chat_update(
        channel=p["channel_id"],
        ts=p["timestamp"],
        blocks=blocks,
    )

    # Update incident record with the severity
    logger.info(
        f"Updating incident record in database with new severity for {channel_name}"
    )
    try:
        db.db_update_incident_severity_col(
            channel_name,
            action_value,
        )
    except Exception as error:
        logger.fatal(f"Error updating entry in database: {error}")

    # If SEV1/2, we need to start a timer to remind the channel about sending status updates
    if action_value == "sev1" or action_value == "sev2":
        logger.info(f"Adding job because action was {action_value}")
        scheduler.add_incident_scheduled_reminder(
            channel_name=channel_name,
            channel_id=channel_id,
            severity=action_value,
        )

    # Final notification
    message = incident.build_severity_update(
        channel_id, action_value
    )  # build severity update
    try:
        result = slack_client.slack_web_client.chat_postMessage(**message, text="")
        logger.debug(f"\n{result}\n")
    except slack_sdk.errors.SlackApiError as error:
        logger.error(
            f"Error sending severity update to incident channel {channel_name}: {error}"
        )
    # Log
    logger.info(f"Updated incident severity for {channel_name} to {action_value}.")
    # Finally, updated the updated_at column
    update_incident_db_entry_ts(channel_name)


"""
Utility Functions
"""


def extract_role_owner(message_blocks: Dict[Any, Any], block_id: str) -> str:
    """
    Takes message blocks and a block_id and returns information specific
    to one of the role blocks
    """
    index = tools.find_index_in_list(message_blocks, "block_id", block_id)
    return message_blocks[index]["text"]["text"].split("\n")[1].replace(" ", "")


def extract_attribute(
    attribute: str,
    channel: str,
    oldest: Any,
) -> str:
    """
    References existing data in the digest message
    """
    try:
        result = slack_client.slack_web_client.conversations_history(
            channel=channel,
            inclusive=True,
            oldest=oldest,
            limit=1,
        )
        message = result["messages"][0]
        index = tools.find_index_in_list(
            message["blocks"], "block_id", f"digest_channel_{attribute}"
        )
        current = message["blocks"][index]["text"]["text"]
        regex = "\*(.*?)\*"
        return re.search(regex, current).group(1).replace("*", "").lower()
    except slack_sdk.errors.SlackApiError as error:
        logger.error(
            f"Error retrieving current {attribute} from digest message: {error}"
        )


def update_incident_db_entry_ts(channel_id: str):
    """
    Updates the updated_at column on an incident's database entry
    """
    try:
        db.db_update_incident_updated_at_col(
            incident_id=channel_id,
            updated_at=tools.fetch_timestamp(),
        )
    except Exception as error:
        logger.fatal(f"Error updating incident entry with update timestamp: {error}")
