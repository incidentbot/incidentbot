import logging

from . import slack_tools
from apscheduler.job import Job
from typing import Dict, List

logger = logging.getLogger(__name__)

bot_user_id = slack_tools.slack_web_client.auth_test()["user_id"]
bot_user_name = str.replace(
    slack_tools.slack_web_client.auth_test()["user"], "_", " "
).title()


def help(channel_id: str) -> List[str]:
    """Return the help menu

    Keyword arguments:
    channel_id -- String containing the ID of the Slack channel to send the message to
    """
    base_block = [
        {"type": "divider"},
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f":robot_face: {bot_user_name} Help",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"To use any of these commands, simply mention me and then provide the command listed below. For example: `<@{bot_user_id}> lsai`",
            },
        },
        {"type": "divider"},
    ]
    commands = {
        "help": "This command that explains help options.",
        "lsai": "List *all* incidents regardless of status.",
        "lsoi": "List only incidents that are still *open* - as in non-resolved.",
        "ls spinc": "List *open* Statuspage incidents (if the integration is enabled)",
        "ping": "Ping the bot to check and see if it's alive and responding.",
        "scheduler list": "List any jobs tasked to the scheduler.",
        "scheduler delete <job_id>": "Delete a job using the ID returned by scheduler list.",
        "version": "Have the bot respond with current application version.",
    }
    for key, value in commands.items():
        base_block.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{key}:* {value}",
                },
            },
        )
    return {
        "channel": channel_id,
        "blocks": base_block,
    }


def i_dont_know(channel_id: str, requested: str):
    """Response with generic message indicating that the bot does not know
    a provided command.

    Keyword arguments:
    channel_id -- String containing the ID of the Slack channel to send the message to
    requested -- String containing the command that was provided that doesn't exist
    """
    try:
        slack_tools.slack_web_client.chat_postMessage(
            channel=channel_id,
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"Sorry, I don't know the command *{requested}* yet.",
                    },
                },
            ],
        )
    except slack_tools.errors.SlackApiError as error:
        logger.error(f"Error when trying to state a command doesn't exist: {error}")


def incident_list_message(
    channel_id: str, incidents: List, all: bool = False
) -> Dict[str, str]:
    """Return a message containing details on incidents

    Keyword arguments:
    channel_id -- String containing the ID of the Slack channel to send the message to
    incidents -- List[Tuple] containing incident information
    all -- Bool indicating whether or not all incidents should be returned regardless of status
    """
    base_block = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": ":open_file_folder: Open Incidents"},
        },
        {"type": "divider"},
    ]
    formatted_incidents = []
    none_found_block = {
        "channel": channel_id,
        "blocks": [
            {"type": "divider"},
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":open_file_folder: No Open Incidents",
                },
            },
            {"type": "divider"},
        ],
    }
    # Check to see if there are any incidents
    if len(incidents) == 0:
        return none_found_block
    else:
        for inc in incidents:
            if all == True:
                formatted_incidents.append(
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*ID:* <#{inc.channel_id}>",
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Severity:* {inc.severity.upper()}",
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Status:* {inc.status.title()}",
                            },
                        ],
                    }
                )
                formatted_incidents.append({"type": "divider"})
            elif all == False:
                if inc.status != "resolved":
                    formatted_incidents.append(
                        {
                            "type": "section",
                            "fields": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"*ID:* <#{inc.channel_id}>",
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Severity:* {inc.severity.upper()}",
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Status:* {inc.status.title()}",
                                },
                            ],
                        }
                    )
                    formatted_incidents.append({"type": "divider"})
    if len(formatted_incidents) == 0:
        return none_found_block
    else:
        for inc in formatted_incidents:
            base_block.append(inc)
        return {
            "channel": channel_id,
            "blocks": base_block,
        }


def send_generic(channel_id: str, text: str):
    """Send a generic text response to a Slack channel

    Keyword arguments:
    channel_id -- String containing the ID of the Slack channel to send the message to
    text -- String containing the message content
    """
    try:
        slack_tools.slack_web_client.chat_postMessage(
            channel=channel_id,
            text=text,
        )
    except slack_tools.errors.SlackApiError as error:
        logger.error(
            f"Error sending generic message to Slack channel {channel_id}: {error}"
        )


def sp_incident_list_message(
    channel_id: str, incidents: List[Dict[str, str]]
) -> Dict[str, str]:
    """Return a message containing details on Statuspage incidents

    Keyword arguments:
    channel_id -- String containing the ID of the Slack channel to send the message to
    incidents -- List[Dict[str, str]] containing Statuspage incident information
    """
    base_block = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":open_file_folder: Open Statuspage Incidents",
            },
        },
        {"type": "divider"},
    ]
    formatted_incidents = []
    none_found_block = {
        "channel": channel_id,
        "blocks": [
            {"type": "divider"},
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":open_file_folder: No Open Statuspage Incidents",
                },
            },
            {"type": "divider"},
        ],
    }
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
            if inc["status"] != "resolved":
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
            base_block.append(inc)
        return {
            "channel": channel_id,
            "blocks": base_block,
        }


def job_list_message(channel_id: str, jobs: List[Job]) -> Dict[str, str]:
    """Return a message containing details on scheduled jobs

    Keyword arguments:
    channel_id -- String containing the ID of the Slack channel to send the message to
    jobs -- List[Job] containing the list of jobs returned from the APScheduler API
    """
    base_block = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": ":timer_clock: Scheduled Jobs"},
        },
        {"type": "divider"},
    ]
    formatted_jobs = []
    none_found_block = {
        "channel": channel_id,
        "blocks": [
            {"type": "divider"},
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":timer_clock: No Scheduled Jobs",
                },
            },
            {"type": "divider"},
        ],
    }
    # Check to see if there are any scheduled jobs
    if len(jobs) == 0:
        return none_found_block
    else:
        for job in jobs:
            formatted_jobs.append(
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Name:* {job.name}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*ID:* {job.id}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Next Run:* {job.next_run_time}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Function:* {job.func}",
                        },
                    ],
                }
            )
            formatted_jobs.append({"type": "divider"})
    if len(formatted_jobs) == 0:
        return none_found_block
    else:
        for job in formatted_jobs:
            base_block.append(job)
        return {
            "channel": channel_id,
            "blocks": base_block,
        }
