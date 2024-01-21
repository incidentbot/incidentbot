import config

from apscheduler.job import Job
from typing import Dict, List
from .client import bot_user_name, bot_user_id


def help_menu(include_header: bool = True) -> List:
    """
    Returns the formatted help menu for the bot
    """
    blocks = []
    if include_header:
        blocks.append(
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f":robot_face: {bot_user_name} Help",
                },
            },
        )
    blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"To use any of these commands, simply mention me and then provide the command listed below. For example: `<@{bot_user_id}> lsoi`",
            },
        }
    )
    commands = {
        "help": "This command that explains help options.",
        "edit": "Adjust incident settings directly in the databaase. Please read the documentation regarding the use of this command.",
        "lsoi": "List only incidents that are still *open* - as in non-resolved.",
        "ls-sp-inc": "List *open* Statuspage incidents.",
        "pager": "Return information from PagerDuty regarding who is currently on call. You may optionally page them.",
        "ping": "Ping the bot to check and see if it's alive and responding.",
        "scheduler list": "List any jobs tasked to the scheduler.",
        "scheduler delete <job_id>": "Delete a job using the ID returned by scheduler list.",
    }
    txt = ""
    for key, value in commands.items():
        txt += f"- `{key}`: {value}\n"
    blocks.append(
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": txt.strip()},
        },
    )

    return blocks


def incident_list_message(
    incidents: List, all: bool = False
) -> List[Dict[str, str]]:
    """Return a message containing details on incidents

    Keyword arguments:
    incidents -- List[Tuple] containing incident information
    all -- Bool indicating whether or not all incidents should be returned regardless of status
    """
    base_block = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":open_file_folder: Open Incidents (Most Recent)",
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
                "text": ":open_file_folder: No Open Incidents",
            },
        },
    ]
    # Check to see if there are any incidents
    if len(incidents) == 0:
        return none_found_block
    else:
        for inc in incidents:
            if all == True:
                formatted_incidents.append(
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"> <#{inc.channel_id}> *|* _ID_ *{inc.incident_id}* *|* _Severity_ *{inc.severity.upper()}* *|* _Status_ *{inc.status.title()}* *|* _Creation Time_ *{inc.created_at}*",
                        },
                    }
                )
            elif all == False:
                if inc.status != "resolved":
                    formatted_incidents.append(
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"> <#{inc.channel_id}> *|* _ID_ *{inc.incident_id}* *|* _Severity_ *{inc.severity.upper()}* *|* _Status_ *{inc.status.title()}* *|* _Creation Time_ *{inc.created_at}*",
                            },
                        }
                    )
    if len(formatted_incidents) == 0:
        return none_found_block
    else:
        for inc in formatted_incidents:
            base_block.append(inc)
    base_block.append(
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"This list is truncated to the last {config.show_most_recent_incidents_app_home_limit} most recent incidents. Raising this limit beyond the default value could result in errors due to block count limitations in the Slack API.",
                },
            ],
        }
    )

    return base_block


def job_list_message(jobs: List[Job]) -> Dict[str, str]:
    """Return a message containing details on scheduled jobs

    Keyword arguments:
    channel_id -- String containing the ID of the Slack channel to send the message to
    jobs -- List[Job] containing the list of jobs returned from the APScheduler API
    """
    base_block = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":timer_clock: Scheduled Jobs",
            },
        },
        {"type": "divider"},
    ]
    formatted_jobs = []
    none_found_block = [
        {"type": "divider"},
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":timer_clock: No Scheduled Jobs",
            },
        },
        {"type": "divider"},
    ]
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
        return base_block


def sp_incident_list_message(
    incidents: List[Dict[str, str]]
) -> List[Dict[str, str]]:
    """Return a message containing details on Statuspage incidents

    Keyword arguments:
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
    none_found_block = [
        {"type": "divider"},
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":open_file_folder: No Open Statuspage Incidents",
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

    return base_block


def new_jira_message(
    key: str, summary: str, type: str, link: str
) -> List[Dict]:
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "A Jira issue has been created for this incident.",
            },
        },
        {"type": "divider"},
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
