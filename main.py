import config
import logging
import logging.config
import sys
import tzlocal

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from flask import Flask
from lib.db import db
from lib.scheduler import tasks
from slackeventsapi import SlackEventAdapter
from waitress import serve

__version__ = "v1.9.1"

# Create the logging object
# This is used by submodules as well
logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=config.log_level)

# Flask configuration
class FlaskConfig:
    SCHEDULER_API_ENABLED = True
    SCHEDULER_JOBSTORES = {
        "default": SQLAlchemyJobStore(
            url=config.database_url, tablename="apscheduler_jobs"
        )
    }
    SCHEDULER_TIMEZONE = str(tzlocal.get_localzone())


# App
app = Flask(__name__)
## Load Configuration
app.config.from_object(FlaskConfig())
## Initialize Task Scheduler
task_scheduler = tasks.TaskScheduler(app=app)
## Slack Events Adapter
slack_events_adapter = SlackEventAdapter(
    config.slack_signing_secret,
    "/slack/events",
    server=app,
)

# Import routes for Flask
import lib.core.routes
import lib.slack.slack_events
import lib.incident.routes

if config.web_interface_enabled == "true":
    import lib.core.webapp

    lib.core.webapp.create_default_admin_account()


def db_check():
    logger.info("Testing the database connection...")
    db_info = f"""
------------------------------
Database host:  {config.database_host}
Database port:  {config.database_port}
Database user:  {config.database_user}
Database name:  {config.database_name}
------------------------------
    """
    print(db_info)
    if not db.db_verify():
        logger.fatal("Cannot connect to the database - check settings and try again.")
        exit(1)


def startup_message():
    startup_message = f"""
--------------------------------------------------------------------------------
                                incident bot
--------------------------------------------------------------------------------
Core functionality:
    Database host:                      {config.database_host}
    Incidents digest channel:           {config.incidents_digest_channel}
    Slack workspace:                    {config.slack_workspace_id}
    Logging level:                      {config.log_level}

Options:
    Auto group invite enabled:          {config.incident_auto_group_invite_enabled}
    Auto group invite group name:       {config.incident_auto_group_invite_group_name}
    External providers enabled:         {config.incident_external_providers_enabled}
    External providers list:            {config.incident_external_providers_list}
    React to create incident enabled:   {config.incident_auto_create_from_react_enabled}
    React emoji:                        {config.incident_auto_create_from_react_emoji_name}
    Statuspage integration enabled:     {config.statuspage_integration_enabled}
    Statuspage API key:                 {config.statuspage_api_key[-4:].rjust(len(config.statuspage_api_key), "*")}
    Statuspage page ID:                 {config.statuspage_page_id[-4:].rjust(len(config.statuspage_page_id), "*")}
    Web interface enabled:              {config.web_interface_enabled}
--------------------------------------------------------------------------------
    """
    print(startup_message)


if __name__ == "__main__":
    # Pre-flight checks
    ## Check for environment variables
    config.env_check(
        required_envs=[
            "INCIDENTS_DIGEST_CHANNEL",
            "INCIDENT_GUIDE_LINK",
            "INCIDENT_POSTMORTEMS_LINK",
            "INCIDENT_CHANNEL_TOPIC",
            "SLACK_SIGNING_SECRET",
            "SLACK_BOT_TOKEN",
            "SLACK_VERIFICATION_TOKEN",
            "SLACK_WORKSPACE_ID",
            "DATABASE_HOST",
            "DATABASE_NAME",
            "DATABASE_USER",
            "DATABASE_PASSWORD",
            "DATABASE_PORT",
        ]
    )
    ## Make sure database connection works
    db_check()
    ## Make sure templates directory exists and all templates are present
    config.slack_template_check(
        required_templates=[
            "incident_channel_boilerplate.json",
            "incident_digest_notification_update.json",
            "incident_digest_notification.json",
            "incident_resolution_message.json",
            "incident_role_update.json",
            "incident_severity_update.json",
            "incident_status_update.json",
            "incident_user_role_dm.json",
        ]
    )
    ## Start scheduler and add scheduled tasks
    task_scheduler.start()
    tasks.job_definitions(task_scheduler.scheduler)
    ## Startup splash for confirming key options
    startup_message()
    serve(app, host="0.0.0.0", port=3000)
