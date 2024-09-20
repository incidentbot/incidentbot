import datetime

from incidentbot.configuration.settings import settings
from apscheduler.job import Job
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from incidentbot.logging import logger
from incidentbot.models.incident import IncidentDatabaseInterface
from apscheduler.schedulers.background import BackgroundScheduler
from incidentbot.slack.client import (
    get_digest_channel_id,
    slack_web_client,
    store_slack_channel_list_db,
    store_slack_user_list_db,
)
from incidentbot.util import gen
from zoneinfo import ZoneInfo

configured_timezone = settings.options.timezone
jobstores = {"default": SQLAlchemyJobStore(url=settings.DATABASE_URI)}


class TaskScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            timezone=ZoneInfo(configured_timezone),
        )

    def delete_job(self, job_to_delete: str):
        try:
            self.scheduler.remove_job(job_id=job_to_delete)
        except Exception as error:
            logger.error(f"Unable to delete job {job_to_delete}: {error}")

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
        logger.info(f"Removing {num_jobs} jobs from the scheduler.")
        self.scheduler.remove_all_jobs()

    def start(self):
        logger.info("Starting task scheduler...")
        try:
            self.scheduler.start()
        except Exception as error:
            logger.error(f"Error starting task scheduler: {error}")


process = TaskScheduler()

"""
Job Definitions
"""


def scrape_for_aging_incidents():
    """
    Checks for incidents older than x days old and sends a reminder message to the
    incidents channel to check on them
    """

    logger.info("[running task scrape_for_aging_incidents]")

    # Max age, in days, of a channel before it's considered stale
    max_age = 7

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
    if (
        settings.jobs
        and settings.jobs.scrape_for_aging_incidents.ignore_statuses
    ):
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
                f"{inc.channel_id} is older than {max_age} days and will be "
                + "added to the weekly reminder"
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
        for inc in formatted_incidents:
            base_block.append(inc)
        try:
            slack_web_client.chat_postMessage(
                channel=get_digest_channel_id(), blocks=base_block
            )
        except Exception as error:
            logger.error(error)
    else:
        logger.info(
            f"Checked for incidents older than {max_age} days and did not find"
            + " any. No alert will be sent."
        )


if settings.jobs and not settings.jobs.scrape_for_aging_incidents.enabled:
    process.scheduler.add_job(
        id="scrape_for_aging_incidents",
        func=scrape_for_aging_incidents,
        trigger="interval",
        name="Look for stale incidents and inform the digest channel",
        days=2,
        replace_existing=True,
    )


def update_slack_channel_list():
    """
    Uses Slack API to fetch the list of current channels
    """

    try:
        store_slack_channel_list_db()
    except Exception as error:
        logger.error(
            f"Error updating Slack channel list information in scheduled job: {error}"
        )


process.scheduler.add_job(
    id="update_slack_channel_list",
    func=update_slack_channel_list,
    trigger="interval",
    name="Update local copy of Slack channels",
    minutes=15,
    replace_existing=True,
)


def update_slack_user_list():
    """
    Uses Slack API to fetch the list of current users
    """

    try:
        store_slack_user_list_db()
    except Exception as error:
        logger.error(
            f"Error updating Slack user list information in scheduled job: {error}"
        )


process.scheduler.add_job(
    id="update_slack_user_list",
    func=update_slack_user_list,
    trigger="interval",
    name="Update local copy of Slack users",
    minutes=15,
    replace_existing=True,
)

if (
    settings.integrations
    and settings.integrations.atlassian
    and settings.integrations.atlassian.opsgenie
    and settings.integrations.atlassian.opsgenie.enabled
):
    from incidentbot.opsgenie.api import OpsgenieAPI

    def update_opsgenie_oc_data():
        """
        Uses Opsgenie API to fetch information about on-call schedules
        """

        logger.info("[running task update_opsgenie_oc_data]")

        try:
            api = OpsgenieAPI()
            api.store_on_call_data()
        except Exception as error:
            logger.error(
                f"Error updating Opsgenie on-call information in scheduled job: {error}"
            )

    process.scheduler.add_job(
        id="update_opsgenie_oc_data",
        func=update_opsgenie_oc_data,
        trigger="interval",
        name="Update Opsgenie on-call information",
        minutes=30,
        replace_existing=True,
    )


if (
    settings.integrations
    and settings.integrations.pagerduty
    and settings.integrations.pagerduty.enabled
):
    from incidentbot.pagerduty.api import PagerDutyInterface

    pagerduty_interface = PagerDutyInterface()

    def update_pagerduty_oc_data():
        """
        Uses PagerDuty API to fetch information about on-call schedules
        """

        logger.info("[running task update_pagerduty_oc_data]")

        try:
            pagerduty_interface.store_on_call_data()
        except Exception as error:
            logger.error(
                f"Error updating PagerDuty on-call information in scheduled job: {error}"
            )

    process.scheduler.add_job(
        id="update_pagerduty_oc_data",
        func=update_pagerduty_oc_data,
        trigger="interval",
        name="Update PagerDuty on-call information",
        minutes=30,
        replace_existing=True,
    )
