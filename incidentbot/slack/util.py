from incidentbot.logging import logger
from incidentbot.models.database import IncidentRecord
from incidentbot.scheduler.core import process as TaskScheduler
from incidentbot.slack.client import (
    slack_web_client,
)
from typing import Any


def handle_comms_reminder(
    channel_id: str,
    record: IncidentRecord,
    ts: str,
    interval: int | None = None,
):
    """
    Handler for a user response for the comms reminder messages

    Parameters:
        channel_id (str): Slack channel ID for the incident
        interval (int): The interval, in minutes, to delay the message (None means delete)
        record (IncidentRecord): The database record object for the incident
        ts (str): The message timestamp for the comms reminder message
    """

    try:
        job = TaskScheduler.get_job(job_id=f"{record.slug}_comms_reminder")

        if interval is None:
            TaskScheduler.delete_job(job_to_delete=job.id)
            slack_web_client.chat_postMessage(
                channel=channel_id,
                text=":white_check_mark: Got it. I won't send any more reminders about communications for this incident.",
            )
        else:
            TaskScheduler.reschedule_job(job_id=job.id, new_minutes=interval)
            slack_web_client.chat_postMessage(
                channel=channel_id,
                text=f":white_check_mark: Got it. I'll remind the channel about communications again in *{interval} minutes*.",
            )

        slack_web_client.chat_delete(channel=channel_id, ts=ts)
    except Exception as error:
        logger.error(
            f"error rescheduling job {record.slug}_comms_reminder: {error}"
        )


def parse_modal_values(
    body: dict[str, Any],
    by_block_id: bool = False,
    by_block_id_name: str = None,
) -> dict[str, Any] | str | int | None:
    """
    Return content from interactive portions of user submitted
    modals

    Parameters:
        body (dict[str, Any]): Slack response body
        by_block_id (bool): Whether or not to parse by block id
        by_block_id_name (bool): Whether or not to parse by block id name
    """

    blocks = body.get("view").get("blocks")
    values = body.get("view").get("state").get("values")

    result = {}

    if by_block_id:
        if by_block_id_name:
            if by_block_id_name in [i.get("block_id") for i in blocks]:
                idx = [
                    v[0]
                    for v in enumerate(blocks)
                    if v[1].get("block_id") == by_block_id_name
                ][0]

                return blocks[idx]
        else:
            logger.error("must provide by_block_id_name if using by_block_id")
            return

    for _, value in values.items():
        for title, content in value.items():
            block_type = content.get("type")

            match block_type:
                case "datepicker":
                    result[title] = content.get("selected_date")
                case "multi_conversations_select":
                    result[title] = content.get("selected_conversations")
                case "multi_static_select":
                    result[title] = [
                        obj.get("value")
                        for obj in content.get("selected_options")
                    ]
                case "plain_text_input":
                    result[title] = content.get("value")
                case "static_select":
                    result[title] = content.get("selected_option").get("value")
                case "timepicker":
                    result[title] = content.get("selected_time")
                case "users_select":
                    result[title] = content.get("selected_user")

    return result
