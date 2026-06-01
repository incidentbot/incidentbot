from incidentbot.configuration.settings import settings
from incidentbot.incident.conditions import evaluate
from incidentbot.logging import logger
from incidentbot.models.incident import IncidentDatabaseInterface
from incidentbot.scheduler.core import process as TaskScheduler
from incidentbot.slack.client import slack_web_client
from incidentbot.slack.messages import BlockBuilder
from slack_sdk.errors import SlackApiError


def _job_id(slug: str, reminder_id: str) -> str:
    return f"{slug}_{reminder_id}"


def run_reminder(channel_id: str, reminder_id: str) -> None:
    """Generic APScheduler job function for all configured reminders."""
    reminder = next((r for r in settings.reminders if r.id == reminder_id), None)
    if not reminder or not reminder.enabled:
        return

    record = IncidentDatabaseInterface.get_one(channel_id=channel_id)
    if not record:
        return

    if not evaluate(reminder.conditions, record):
        return

    try:
        slack_web_client.chat_postMessage(
            channel=channel_id,
            blocks=BlockBuilder.reminder_message(reminder, record.slug),
            text=reminder.message,
        )
    except SlackApiError as error:
        logger.exception("error sending reminder message", reminder=reminder_id, error=error)
        return

    if reminder.once:
        try:
            job = TaskScheduler.get_job(job_id=_job_id(record.slug, reminder_id))
            if job:
                TaskScheduler.delete_job(job.id)
        except Exception as error:
            logger.exception("error removing once-only reminder job", reminder=reminder_id, error=error)


def register_reminder_jobs(record) -> None:
    """Register APScheduler interval jobs for all enabled reminders."""
    for reminder in settings.reminders:
        if not reminder.enabled:
            continue
        try:
            TaskScheduler.scheduler.add_job(
                id=_job_id(record.slug, reminder.id),
                func=run_reminder,
                args=[record.channel_id, reminder.id],
                trigger="interval",
                name=_job_id(record.slug, reminder.id),
                minutes=reminder.interval_minutes,
                replace_existing=True,
            )
        except Exception as error:
            logger.exception("error registering reminder job", reminder=reminder.id, error=error)


def cancel_reminder_jobs(slug: str) -> None:
    """Remove all reminder jobs for an incident (called on final status)."""
    for reminder in settings.reminders:
        job_id = _job_id(slug, reminder.id)
        try:
            job = TaskScheduler.get_job(job_id=job_id)
            if job:
                TaskScheduler.delete_job(job_to_delete=job.id)
        except Exception as error:
            logger.exception("error removing reminder job", reminder=reminder.id, error=error)


def handle_snooze(channel_id: str, reminder_id: str, minutes: int, ts: str) -> None:
    """Reschedule a reminder job and acknowledge in channel."""
    record = IncidentDatabaseInterface.get_one(channel_id=channel_id)
    if not record:
        return

    job_id = _job_id(record.slug, reminder_id)
    try:
        job = TaskScheduler.get_job(job_id=job_id)
        if job:
            TaskScheduler.reschedule_job(job_id=job.id, new_minutes=minutes)
        slack_web_client.chat_postMessage(
            channel=channel_id,
            text=f":white_check_mark: Got it. I'll remind the channel again in *{minutes} minutes*.",
        )
        slack_web_client.chat_delete(channel=channel_id, ts=ts)
    except Exception as error:
        logger.exception("error snoozing reminder", reminder=reminder_id, error=error)


def handle_dismiss(channel_id: str, reminder_id: str, ts: str) -> None:
    """Permanently cancel a reminder job and acknowledge in channel."""
    record = IncidentDatabaseInterface.get_one(channel_id=channel_id)
    if not record:
        return

    job_id = _job_id(record.slug, reminder_id)
    try:
        job = TaskScheduler.get_job(job_id=job_id)
        if job:
            TaskScheduler.delete_job(job_to_delete=job.id)
        slack_web_client.chat_postMessage(
            channel=channel_id,
            text=":white_check_mark: Got it. I won't send any more reminders for this incident.",
        )
        slack_web_client.chat_delete(channel=channel_id, ts=ts)
    except Exception as error:
        logger.exception("error dismissing reminder", reminder=reminder_id, error=error)
