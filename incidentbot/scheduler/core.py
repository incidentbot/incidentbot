import datetime

from incidentbot.configuration.settings import settings
from apscheduler.job import Job
from incidentbot.logging import logger
from incidentbot.models.incident import IncidentDatabaseInterface
from apscheduler.schedulers.background import BackgroundScheduler
from incidentbot.util import gen
from zoneinfo import ZoneInfo

configured_timezone = settings.options.timezone


class TaskScheduler:
    def __init__(self):
        # Use the default in-memory job store — all jobs are interval-based and
        # do not need to survive a restart, so there is no value in persisting
        # them to the database.
        self.scheduler = BackgroundScheduler(
            timezone=ZoneInfo(configured_timezone),
        )

    def delete_job(self, job_to_delete: str):
        try:
            self.scheduler.remove_job(job_id=job_to_delete)
        except Exception as error:
            logger.exception("unable to delete job", job=job_to_delete, error=error)

    def get_job(self, job_id: str) -> Job:
        return self.scheduler.get_job(job_id=job_id)

    def list_jobs(self) -> list[Job]:
        return self.scheduler.get_jobs()

    def reschedule_job(self, job_id: str, new_minutes: int) -> Job:
        return self.scheduler.reschedule_job(
            job_id=job_id,
            trigger="interval",
            minutes=new_minutes,
        )

    def remove_jobs(self):
        jobs = self.list_jobs()
        num_jobs = len(jobs)
        logger.info("removing jobs from the scheduler", count=num_jobs)
        self.scheduler.remove_all_jobs()

    def start(self):
        logger.info("starting task scheduler")
        try:
            self.scheduler.start()
        except Exception as error:
            logger.exception("error starting task scheduler", error=error)


process = TaskScheduler()

"""
Job Definitions
"""


def scrape_for_aging_incidents():
    """
    Checks for incidents older than x days old and sends a reminder message to the
    incidents channel to check on them
    """

    logger.info("running task scrape_for_aging_incidents")

    # Max age, in days, of a channel before it's considered stale
    max_age = settings.jobs.scrape_for_aging_incidents.max_age_days

    # Base block to build message on
    base_block = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": ":wave: Hi there! The following incidents have been "
                + f"open for {max_age} days. Lets double check them and make "
                "sure their statuses are up to date. :hourglass_flowing_sand:",
            },
        },
        {"type": "divider"},
    ]

    # Find open incidents and append them to a list to add to the message if they're older
    # than the max age
    open_incidents = IncidentDatabaseInterface.list_all()

    # Exclude statuses if provided
    if settings.jobs.scrape_for_aging_incidents.ignore_statuses:
        open_incidents = [
            i
            for i in open_incidents
            if i.status
            not in settings.jobs.scrape_for_aging_incidents.ignore_statuses
        ]

    formatted_incidents = []
    for inc in open_incidents:
        created_at = datetime.datetime.strptime(
            inc.created_at, gen.timestamp_fmt
        )
        now = datetime.datetime.now()
        time_open = now - created_at
        old = datetime.timedelta(days=max_age) < time_open
        if old:
            logger.info(
                "incident is older than max age and will be added to the weekly reminder",
                channel_id=inc.channel_id,
                max_age_days=max_age,
            )

            formatted_incidents.append(
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Incident Name:* <#{inc.channel_id}>",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Current Severity:* {inc.severity.upper()}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Creation Time:* {inc.created_at}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Current Status:* {inc.status.title()}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Time Open:* {time_open}",
                        },
                    ],
                }
            )
            formatted_incidents.append({"type": "divider"})
    if len(formatted_incidents) > 0:
        from incidentbot.slack.client import (
            get_digest_channel_id,
            slack_web_client,
        )

        for inc in formatted_incidents:
            base_block.append(inc)
        try:
            slack_web_client.chat_postMessage(
                channel=get_digest_channel_id(), blocks=base_block
            )
        except Exception as error:
            logger.exception(error)
    else:
        logger.info(
            "checked for aging incidents and did not find any, no alert will be sent",
            max_age_days=max_age,
        )


if settings.jobs.scrape_for_aging_incidents.enabled:
    process.scheduler.add_job(
        id="scrape_for_aging_incidents",
        func=scrape_for_aging_incidents,
        trigger="interval",
        name="Look for stale incidents and inform the digest channel",
        days=settings.jobs.scrape_for_aging_incidents.interval_days,
        replace_existing=True,
    )


def update_slack_channel_list():
    """
    Uses Slack API to fetch the list of current channels
    """
    from incidentbot.slack.client import store_slack_channel_list_db

    try:
        store_slack_channel_list_db()
    except Exception as error:
        logger.exception(
            "error updating slack channel list information in scheduled job", error=error
        )


def update_slack_user_list():
    """
    Uses Slack API to fetch the list of current users
    """
    from incidentbot.slack.client import store_slack_user_list_db

    try:
        store_slack_user_list_db()
    except Exception as error:
        logger.exception(
            "error updating slack user list information in scheduled job", error=error
        )


if settings.platform == "slack" and settings.jobs.update_slack_cache.enabled:
    process.scheduler.add_job(
        id="update_slack_channel_list",
        func=update_slack_channel_list,
        trigger="interval",
        name="Update local copy of Slack channels",
        minutes=settings.jobs.update_slack_cache.interval_minutes,
        replace_existing=True,
    )

    process.scheduler.add_job(
        id="update_slack_user_list",
        func=update_slack_user_list,
        trigger="interval",
        name="Update local copy of Slack users",
        minutes=settings.jobs.update_slack_cache.interval_minutes,
        replace_existing=True,
    )

if (
    settings.integrations
    and settings.integrations.pagerduty
    and settings.integrations.pagerduty.enabled
    and settings.jobs.update_pagerduty_oc_data.enabled
):
    from incidentbot.pagerduty.api import PagerDutyInterface

    pagerduty_interface = PagerDutyInterface()

    def update_pagerduty_oc_data():
        """
        Uses PagerDuty API to fetch information about on-call schedules
        """

        logger.info("running task update_pagerduty_oc_data")

        try:
            pagerduty_interface.store_on_call_data()
        except Exception as error:
            logger.exception(
                "error updating pagerduty on-call information in scheduled job", error=error
            )

    process.scheduler.add_job(
        id="update_pagerduty_oc_data",
        func=update_pagerduty_oc_data,
        trigger="interval",
        name="Update PagerDuty on-call information",
        minutes=settings.jobs.update_pagerduty_oc_data.interval_minutes,
        replace_existing=True,
    )
