from incidentbot.configuration.settings import settings
from incidentbot.incident.conditions import evaluate
from incidentbot.incident.event import EventLogHandler
from incidentbot.logging import logger
from incidentbot.pagerduty.api import PagerDutyInterface
from incidentbot.platform import get_adapter


def run(trigger: str, record) -> None:
    """
    Dispatch all enabled automations whose trigger and conditions match.

    Parameters:
        trigger: one of on_open | on_severity_change | on_status_change | on_final_status
        record: IncidentRecord
    """
    if not settings.automations:
        return

    for automation in settings.automations:
        if not automation.enabled:
            continue

        # on_final_status fires when trigger is on_status_change AND status is final
        if automation.trigger == "on_final_status":
            if trigger != "on_status_change":
                continue
            from incidentbot.configuration.settings import settings as s
            final_statuses = {name for name, cfg in s.statuses.items() if cfg.final}
            if record.status not in final_statuses:
                continue
        elif automation.trigger != trigger:
            continue

        if not evaluate(automation.conditions, record):
            continue

        for action in automation.actions:
            _execute(action, record)


def _execute(action, record) -> None:
    match action.type:
        case "invite_group":
            _invite_group(action, record)
        case "invite_user":
            _invite_user(action, record)
        case "page_pagerduty":
            _page_pagerduty(action, record)
        case "post_message":
            _post_message(action, record)
        case _:
            logger.warning("unknown automation action type", type=action.type)


def _invite_group(action, record) -> None:
    adapter = get_adapter()
    members = adapter.get_group_members_by_name(action.name)
    if not members:
        logger.warning("automation invite_group: group not found or empty", group=action.name)
        return
    try:
        adapter.invite_users(room_id=record.channel_id, user_ids=members)
        EventLogHandler.create(
            event=f"Group {action.name} was invited via automation",
            incident_id=record.id,
            incident_slug=record.slug,
            source="system",
        )
    except Exception as error:
        logger.exception("automation invite_group failed", group=action.name, error=error)


def _invite_user(action, record) -> None:
    if not action.user:
        logger.warning("automation invite_user: no user configured")
        return
    adapter = get_adapter()
    try:
        adapter.invite_user(room_id=record.channel_id, user_id=action.user)
        EventLogHandler.create(
            event=f"User {action.user} was invited via automation",
            incident_id=record.id,
            incident_slug=record.slug,
            source="system",
        )
    except Exception as error:
        logger.exception("automation invite_user failed", user=action.user, error=error)


def _page_pagerduty(action, record) -> None:
    if not (
        settings.integrations
        and settings.integrations.pagerduty
        and settings.integrations.pagerduty.enabled
    ):
        logger.warning("automation page_pagerduty: pagerduty integration not enabled")
        return

    try:
        interface = PagerDutyInterface(escalation_policy=action.escalation_policy)
        interface.page(
            priority=action.priority,
            channel_name=record.channel_name,
            channel_id=record.channel_id,
            paging_user="auto",
        )
        EventLogHandler.create(
            event=f"PagerDuty escalation policy {action.escalation_policy} paged via automation",
            incident_id=record.id,
            incident_slug=record.slug,
            source="system",
        )
    except Exception as error:
        logger.exception("automation page_pagerduty failed", policy=action.escalation_policy, error=error)


def _post_message(action, record) -> None:
    adapter = get_adapter()
    try:
        adapter.send_text(room_id=record.channel_id, text=action.message)
    except Exception as error:
        logger.exception("automation post_message failed", error=error)
