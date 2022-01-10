import config
import logging
import logging.config
import os
import sys

from dotenv import load_dotenv
from flask import Flask
from lib.db import db
from waitress import serve

__version__ = "v1.4.0"

# Create the logging object
# This is used by submodules as well
logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=config.log_level)

# App
app = Flask(__name__)
# Import routes for Flask
import lib.core.routes
import lib.slack.slack_events
import lib.incident.routes


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
    else:
        logger.info(
            "Database connection works - checking to see if it needs to be bootstrapped..."
        )
        db.db_bootstrap()


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
--------------------------------------------------------------------------------
    """
    print(startup_message)


def templates_dir_check():
    if os.path.isdir(config.templates_directory):
        logger.info(f"Templates directory found at {config.templates_directory}.")
    else:
        logger.fatal(
            f"Templates directory not found - {config.templates_directory} was specified as the location."
        )
        exit(1)


if __name__ == "__main__":
    # Pre-flight checks
    # Check for environment variables
    config.env_check(
        [
            "INCIDENTS_DIGEST_CHANNEL",
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
    # Make sure database connection works
    db_check()
    # Make sure templates directory exists
    templates_dir_check()
    # Startup splash for confirming key options
    startup_message()
    serve(app, host="0.0.0.0", port=3000)
