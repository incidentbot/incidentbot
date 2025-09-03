import sys

from incidentbot.configuration.settings import settings, __version__
from incidentbot.models.database import (
    create_default_admin_user,
    db_verify,
    engine,
    ApplicationData,
)
from incidentbot.scheduler.core import process as TaskScheduler

from incidentbot.logging import logger
from sqlmodel import Session, select
from uvicorn import run


"""
Scheduler
"""

TaskScheduler.start()

"""
Startup
"""


def db_check():
    logger.info("Testing the database connection...")
    if not db_verify():
        logger.fatal(
            "Cannot connect to the database - check settings and try again."
        )
        sys.exit(1)


def startup_message(provider: str, workspace: str, wrap: bool = False) -> str:
    """
    Returns diagnostic info for startup or troubleshooting
    """

    msg = f"""
--------------------------------------------------------------------------------
                            incident bot {__version__}
--------------------------------------------------------------------------------
Database host:                      {settings.POSTGRES_HOST}
Incidents digest channel:           {settings.digest_channel}
Logging level:                      {settings.LOG_LEVEL}
Provider:                           {provider}
Workspace:                          {workspace}
Timezone:                           {settings.options.timezone}
--------------------------------------------------------------------------------
    """
    if wrap:
        return f"""
```
{msg}
```
        """
    else:
        return msg


def startup_tasks():
    # Database Models
    # --------------------
    # create_models()
    create_default_admin_user()

    """
    Tasks that should be run at each startup
    """

    logger.info("Running startup tasks...")

    match settings.platform:
        case "slack":
            from incidentbot.scheduler.core import (
                update_slack_channel_list,
                update_slack_user_list,
            )

            # Store Slack Channels
            # --------------------
            update_slack_channel_list()

            # Store Slack Users
            # --------------------
            update_slack_user_list()

    # Integration Tests
    # --------------------
    if (
        settings.integrations
        and settings.integrations.atlassian
        and settings.integrations.atlassian.confluence
        and settings.integrations.atlassian.confluence.enabled
    ):
        from incidentbot.confluence.api import ConfluenceApi

        api_test = ConfluenceApi()
        passes = api_test.test()
        if not passes:
            logger.fatal(
                "Could not verify Confluence parent page exists.\nYou provided: {}/{}".format(
                    settings.integrations.atlassian.confluence.space,
                    settings.integrations.atlassian.confluence.parent,
                )
            )
            sys.exit(1)

    if (
        settings.integrations
        and settings.integrations.atlassian
        and settings.integrations.atlassian.jira
        and settings.integrations.atlassian.jira.enabled
    ):
        from incidentbot.jira.api import JiraApi

        api_test = JiraApi()
        passes = api_test.test()
        if not passes:
            logger.fatal(
                "Could not verify Jira project exists.\nYou provided: {}".format(
                    settings.integrations.atlassian.jira.project,
                )
            )
            sys.exit(1)

    if (
        settings.integrations
        and settings.integrations.pagerduty
        and settings.integrations.pagerduty.enabled
    ):
        from incidentbot.pagerduty.api import PagerDutyInterface

        pagerduty_interface = PagerDutyInterface()

        if len(pagerduty_interface.test()) == 0:
            logger.fatal(
                "PagerDuty test failed: unable to retrieve oncall iterable - either no schedules exist or none were returned",
            )
            sys.exit(1)

        from incidentbot.scheduler.core import update_pagerduty_oc_data

        update_pagerduty_oc_data()

        try:
            with Session(engine) as session:
                if not session.exec(
                    select(ApplicationData).filter(
                        ApplicationData.name == "auto_page_teams"
                    )
                ).first():
                    auto_page_teams = ApplicationData(
                        name="auto_page_teams",
                        json_data={"teams": []},
                    )
                    session.add(auto_page_teams)
                    session.commit()
        except Exception as error:
            logger.error(f"Error storing auto_page_teams: {error}")


if __name__ == "__main__":
    # Database Check
    # --------------------
    db_check()

    # Startup Tests
    # --------------------
    startup_tasks()

    # Startup Message
    # --------------------

    match settings.platform:
        case "slack":
            from incidentbot.slack.client import (
                slack_workspace_id,
            )

            print(
                startup_message(provider="Slack", workspace=slack_workspace_id)
            )

    # Always check to make sure the bot user is in the digest channel
    # --------------------

    match settings.platform:
        case "slack":
            from incidentbot.slack.client import (
                check_bot_user_in_digest_channel,
            )

            check_bot_user_in_digest_channel()

    # Platform Integrations
    # --------------------

    match settings.platform:
        case "slack":
            from incidentbot.slack.handler import app as slack_app
            from slack_bolt.adapter.socket_mode import SocketModeHandler

            handler = SocketModeHandler(slack_app, settings.SLACK_APP_TOKEN)

    # API and handler Integration
    # --------------------
    from incidentbot.api.main import app

    handler.connect()
    run(app, host="0.0.0.0", port=3000)
