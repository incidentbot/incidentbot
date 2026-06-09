import os
import sys

from incidentbot.configuration.settings import settings
from incidentbot.logging import logger
from incidentbot.models.database import db_verify
from incidentbot.version import APP_VERSION


def db_check() -> None:
    if not db_verify():
        logger.fatal("cannot connect to the database - check settings and try again")
        sys.exit(1)


def startup_tasks() -> None:
    match settings.platform:
        case "slack":
            from incidentbot.scheduler.core import (
                update_slack_channel_list,
                update_slack_user_list,
            )

            update_slack_channel_list()
            update_slack_user_list()

    if (
        settings.integrations
        and settings.integrations.atlassian
        and settings.integrations.atlassian.confluence
        and settings.integrations.atlassian.confluence.enabled
    ):
        from incidentbot.confluence.api import ConfluenceApi

        if not ConfluenceApi().test():
            logger.fatal(
                "could not verify confluence parent page exists",
                space=settings.integrations.atlassian.confluence.space,
                parent=settings.integrations.atlassian.confluence.parent,
            )
            sys.exit(1)

    if (
        settings.integrations
        and settings.integrations.atlassian
        and settings.integrations.atlassian.jira
        and settings.integrations.atlassian.jira.enabled
    ):
        from incidentbot.jira.api import JiraApi

        if not JiraApi().test():
            logger.fatal(
                "could not verify jira project exists",
                project=settings.integrations.atlassian.jira.project,
            )
            sys.exit(1)

    if (
        settings.integrations
        and settings.integrations.pagerduty
        and settings.integrations.pagerduty.enabled
    ):
        from incidentbot.models.database import engine, ApplicationData
        from incidentbot.pagerduty.api import PagerDutyInterface
        from incidentbot.scheduler.core import update_pagerduty_oc_data
        from sqlmodel import Session, select

        pagerduty_interface = PagerDutyInterface()
        if len(pagerduty_interface.test()) == 0:
            logger.fatal(
                "pagerduty test failed: unable to retrieve oncall iterable — "
                "either no schedules exist or none were returned"
            )
            sys.exit(1)

        update_pagerduty_oc_data()

        try:
            with Session(engine) as session:
                if not session.exec(
                    select(ApplicationData).filter(
                        ApplicationData.name == "auto_page_teams"
                    )
                ).first():
                    session.add(
                        ApplicationData(name="auto_page_teams", json_data={"teams": []})
                    )
                    session.commit()
        except Exception as error:
            logger.error("error storing auto_page_teams", error=error)

    if (
        settings.integrations
        and settings.integrations.gitlab
        and settings.integrations.gitlab.enabled
    ):
        from incidentbot.gitlab.api import GitLabApi

        if not GitLabApi().test():
            logger.fatal(
                "could not verify gitlab project exists",
                project_id=settings.integrations.gitlab.project_id,
            )
            sys.exit(1)


def init_platform() -> None:
    match settings.platform:
        case "slack":
            from incidentbot.platform import init_adapter
            from incidentbot.platform.slack import SlackAdapter

            init_adapter(SlackAdapter())
        case "matrix":
            from incidentbot.platform import init_adapter
            from incidentbot.platform.matrix import MatrixAdapter

            init_adapter(MatrixAdapter(settings.matrix))


def connect_platform() -> None:
    """Start the platform event listener in a background thread (non-blocking)."""
    match settings.platform:
        case "slack":
            from incidentbot.slack.handler import app as slack_app
            from slack_bolt.adapter.socket_mode import SocketModeHandler

            SocketModeHandler(slack_app, settings.SLACK_APP_TOKEN).connect()
        case "matrix":
            from incidentbot.matrix.handler import MatrixHandler
            from incidentbot.platform import get_adapter

            MatrixHandler(
                get_adapter().client,
                digest_room_id=settings.matrix.digest_room_id,
                widget_base_url=settings.matrix.widget_base_url,
            ).start()


def post_startup_checks() -> None:
    match settings.platform:
        case "slack":
            from incidentbot.slack.client import check_bot_user_in_digest_channel

            check_bot_user_in_digest_channel()


def emit_startup_log() -> None:
    match settings.platform:
        case "slack":
            from incidentbot.slack.client import slack_workspace_id

            workspace = slack_workspace_id
        case "matrix":
            workspace = settings.matrix.homeserver
        case _:
            workspace = "unknown"

    if not os.getenv("SECRET_KEY"):
        logger.warning(
            "SECRET_KEY is not set — widget tokens will be invalidated on every restart; "
            "set SECRET_KEY to a stable value in your environment"
        )

    extra = {}
    if settings.ENABLE_API_DOCS:
        extra["api_docs"] = "http://localhost:3000/api/v1/docs"

    logger.info(
        "started",
        version=APP_VERSION,
        platform=settings.platform,
        workspace=workspace,
        digest_channel=settings.digest_channel,
        database_host=settings.POSTGRES_HOST,
        log_level=settings.LOG_LEVEL,
        timezone=settings.options.timezone,
        **extra,
    )
