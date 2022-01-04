import logging
import logging.config
import os
import sys

from dotenv import load_dotenv
from flask import Flask
from lib.db import db

__version__ = "v1.0.0"

# .env parse
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)

# Create the logging object
# This is used by submodules as well
logger = logging.getLogger(__name__)
LOGLEVEL = os.getenv("LOGLEVEL", "INFO").upper()
logging.basicConfig(stream=sys.stdout, level=LOGLEVEL)

# Where do we look for templates?
templates_directory = os.getenv("TEMPLATES_DIRECTORY", default="templates/")

# App
app = Flask(__name__)
# Import routes for Flask
import lib.core.routes
import lib.core.slack_events
import lib.incident.routes


def db_check():
    logger.info("Testing the database connection...")
    db_info = f"""
------------------------------
Database host:  {os.getenv("DATABASE_HOST")}
Database port:  {os.getenv("DATABASE_PORT")}
Database user:  {os.getenv("DATABASE_USER")}
Database name:  {os.getenv("DATABASE_NAME")}
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


def env_check(envs):
    for e in envs:
        if os.getenv(e) == "":
            logger.fatal(f"The environment variable {e} cannot be empty.")
            exit(1)
        else:
            pass
    if os.getenv("STATUSPAGE_INTEGRATION_ENABLED") == "true":
        for var in ["STATUSPAGE_API_KEY", "STATUSPAGE_PAGE_ID"]:
            if os.getenv(var) == "":
                logger.fatal(
                    f"If enabling the Statuspage integration, the {var} variable must be set."
                )
                exit(1)


def startup_message():
    startup_message = f"""
--------------------------------------------------------------------------------
                                incident bot
--------------------------------------------------------------------------------
Core functionality:
    Database host:                      {os.getenv("DATABASE_HOST")}
    Incidents digest channel:           {os.getenv("INCIDENTS_DIGEST_CHANNEL")}
    Slack workspace:                    {os.getenv("SLACK_WORKSPACE_ID")}
    Logging level:                      {LOGLEVEL}

Options:
    External providers enabled:         {os.getenv("INCIDENT_EXTERNAL_PROVIDERS_ENABLED")}
    External providers list:            {os.getenv("INCIDENT_EXTERNAL_PROVIDERS_LIST")}
    Statuspage integration enabled:     {os.getenv("STATUSPAGE_INTEGRATION_ENABLED")}
    Statuspage API key:                 {os.getenv("STATUSPAGE_API_KEY")[-4:].rjust(len(os.getenv("STATUSPAGE_API_KEY")), "*")}
    Statuspage page ID:                 {os.getenv("STATUSPAGE_PAGE_ID")[-4:].rjust(len(os.getenv("STATUSPAGE_PAGE_ID")), "*")}
--------------------------------------------------------------------------------
    """
    print(startup_message)


def templates_dir_check():
    if os.path.isdir(templates_directory):
        logger.info(f"Templates directory found at {templates_directory}.")
    else:
        logger.fatal(
            f"Templates directory not found - {templates_directory} was specified as the location."
        )
        exit(1)


if __name__ == "__main__":
    # Pre-flight checks
    # Check for environment variables
    env_check(
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
    app.run(host="0.0.0.0", port=3000)
