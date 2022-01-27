import logging
import pyjokes
import random
import string

from __main__ import __version__, config, slack_events_adapter, task_scheduler
from ..db import db
from ..incident import routes as inc
from ..shared import tools
from ..statuspage import statuspage
from . import slack_tools, messages

logger = logging.getLogger(__name__)

# Error events
@slack_events_adapter.on("error")
def error_handler(err):
    print("ERROR: " + str(err))


# React
@slack_events_adapter.on("reaction_added")
def reaction_added(event_data):
    # Automatically create incident based on reaction with specific emoji
    if config.incident_auto_create_from_react_enabled == "true":
        event = event_data["event"]
        emoji = event["reaction"]
        channel = event["item"]["channel"]
        ts = event["item"]["ts"]
        # Only act if the emoji is the one we care about
        if emoji == config.incident_auto_create_from_react_emoji_name:
            # Retrieve the content of the message that was reacted to
            try:
                result = slack_tools.slack_web_client.conversations_history(
                    channel=channel, inclusive=True, oldest=ts, limit=1
                )
                message = result["messages"][0]
                message_reacted_to_content = message["text"]
            except slack_tools.errors.SlackApiError as error:
                logger.error(f"Error when trying to retrieve a message: {error}")
            request_parameters = {
                "channel": channel,
                "channel_description": f"auto-{tools.random_suffix}",
                "descriptor": f"auto-{tools.random_suffix}",
                "user": "internal_auto_create",
                "token": slack_tools.verification_token,
                "message_reacted_to_content": message_reacted_to_content,
                "original_message_timestamp": ts,
            }
            # Create an incident based on the message using the internal path
            try:
                inc.create_incident(
                    internal=True, request_parameters=request_parameters
                )
            except Exception as error:
                logger.error(f"Error when trying to create an incident: {error}")


@slack_events_adapter.on("app_mention")
def handle_mentions(event_data):
    event = event_data["event"]
    channel = event["channel"]
    # Remove the bot's user ID from the mention to parse only the text
    message = str.split(event["text"], " ")[1:]
    # React to the following messages
    if "help" in message:
        if len(message) > 1:
            pass
        else:
            resp = messages.help(channel)
            try:
                slack_tools.slack_web_client.chat_postMessage(**resp)
            except slack_tools.errors.SlackApiError as error:
                logger.error(f"Error when trying to post help message: {error}")
    elif "lsoi" in message:
        database_data = db.db_read_all_incidents()
        resp = messages.incident_list_message(channel, database_data, all=False)
        try:
            slack_tools.slack_web_client.chat_postMessage(**resp)
        except slack_tools.errors.SlackApiError as error:
            logger.error(f"Error when trying to list open incidents: {error}")
    elif "lsai" in message:
        database_data = db.db_read_all_incidents()
        resp = messages.incident_list_message(channel, database_data, all=True)
        try:
            slack_tools.slack_web_client.chat_postMessage(**resp)
        except slack_tools.errors.SlackApiError as error:
            logger.error(f"Error when trying to list all incidents: {error}")
    elif "ls spinc" in " ".join(message):
        if config.statuspage_integration_enabled == "true":
            sp_objects = statuspage.StatuspageObjects()
            sp_incidents = sp_objects.open_incidents
            resp = messages.sp_incident_list_message(channel, sp_incidents)
            try:
                slack_tools.slack_web_client.chat_postMessage(**resp)
            except slack_tools.errors.SlackApiError as error:
                logger.error(
                    f"Error when trying to list open Statuspage incidents: {error}"
                )
        else:
            messages.send_generic(
                channel_id=channel,
                text=f"The Statuspage integration is not enabled. I cannot provide information from Statuspage as a result.",
            )
    elif "tell me a joke" in " ".join(message):
        messages.send_generic(
            channel_id=channel,
            text=pyjokes.get_joke(),
        )
    elif "ping" in message:
        try:
            slack_tools.slack_web_client.chat_postMessage(
                channel=channel,
                text="pong",
            )
        except slack_tools.errors.SlackApiError as error:
            logger.error(f"Error when trying to respond to a ping: {error}")
    elif "version" in message:
        messages.send_generic(
            channel_id=channel, text=f"I am currently running version: {__version__}"
        )
    elif "scheduler" in message:
        if message[1] == "list":
            jobs = task_scheduler.list_jobs()
            resp = messages.job_list_message(channel, jobs)
            try:
                slack_tools.slack_web_client.chat_postMessage(**resp)
            except slack_tools.errors.SlackApiError as error:
                logger.error(f"Error when trying to list scheduled tasks: {error}")
        elif message[1] == "delete":
            if len(message) < 3:
                messages.send_generic(
                    channel_id=channel, text="Please provide the ID of a job to delete."
                )
            else:
                job_title = message[2]
                delete_job = task_scheduler.delete_job(job_title)
                if delete_job != None:
                    slack_tools.slack_web_client.chat_postMessage(
                        channel=channel,
                        text=f"Could not delete the job {job_title}: {delete_job}",
                    )
                else:
                    try:
                        slack_tools.slack_web_client.chat_postMessage(
                            channel=channel,
                            text=f"Deleted job {job_title}. Please note that this job will be rescheduled the next time this application starts unless it is removed from source code.",
                        )
                    except slack_tools.errors.SlackApiError as error:
                        logger.error(
                            f"Error when trying to list scheduled tasks: {error}"
                        )
        else:
            requested = " ".join(message)
            messages.i_dont_know(channel, requested)
    else:
        requested = " ".join(message)
        messages.i_dont_know(channel, requested)
