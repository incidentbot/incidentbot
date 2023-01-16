import logging
import os
import yaml

from dotenv import load_dotenv
from typing import Dict, List

__version__ = "v1.0.1"

# .env parse
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)
log_level = os.getenv("LOGLEVEL", "INFO").upper()

# Create the logging object
# This is used by submodules as well
logger = logging.getLogger(__name__)


"""
Global Variables
"""
is_test_environment = os.getenv("TEST_ENVIRONMENT", default="false") in (
    "True",
    "true",
    True,
)


class Configuration:
    def __init__(self):
        self.filepath = (
            os.getenv("CONFIG_FILE_PATH", default="config.yaml")
            if not is_test_environment
            else "config-test.yaml"
        )
        with open(self.filepath, "r") as yamlfile:
            self.live = yaml.load(yamlfile, Loader=yaml.FullLoader)

    @property
    def all(self) -> Dict:
        return self.live

    @property
    def digest_channel(self) -> str:
        return self.live["digest_channel"]

    @property
    def integrations(self) -> Dict:
        return self.live["integrations"]

    @property
    def links(self) -> Dict:
        return self.live["links"]

    @property
    def options(self) -> Dict:
        return self.live["options"]

    @property
    def platform(self) -> str:
        return self.live["platform"]

    @property
    def roles(self) -> Dict[str, str]:
        return self.live["roles"]

    @property
    def severities(self) -> Dict[str, str]:
        return self.live["severities"]

    @property
    def statuses(self) -> List:
        return self.live["statuses"]


active = Configuration()

"""
Database Settings
"""
database_host = os.getenv("POSTGRES_HOST")
database_name = os.getenv("POSTGRES_DB")
database_password = os.getenv("POSTGRES_PASSWORD")
database_port = os.getenv("POSTGRES_PORT")
database_user = os.getenv("POSTGRES_USER")
database_url = f"postgresql://{database_user}:{database_password}@{database_host}:{database_port}/{database_name}"

"""
Slack
"""
slack_app_token = os.getenv("SLACK_APP_TOKEN")
slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
slack_user_token = os.getenv("SLACK_USER_TOKEN")

"""
Statuspage Module
"""
statuspage_api_key = os.getenv("STATUSPAGE_API_KEY", default="")
statuspage_integration_enabled = os.getenv(
    "STATUSPAGE_INTEGRATION_ENABLED", default="false"
)
statuspage_page_id = os.getenv("STATUSPAGE_PAGE_ID", default="")

"""
Confluence
"""
confluence_api_url = os.getenv("CONFLUENCE_API_URL", default="")
confluence_api_username = os.getenv("CONFLUENCE_API_USERNAME", default="")
confluence_api_token = os.getenv("CONFLUENCE_API_TOKEN", default="")

"""
PagerDuty
"""
pagerduty_api_username = os.getenv("PAGERDUTY_API_USERNAME", default="")
pagerduty_api_token = os.getenv("PAGERDUTY_API_TOKEN", default="")

"""
External
"""
zoom_account_id = os.getenv("ZOOM_ACCOUNT_ID", default="")
zoom_client_id = os.getenv("ZOOM_CLIENT_ID", default="")
zoom_client_secret = os.getenv("ZOOM_CLIENT_SECRET", default="")

"""
Web Application
"""
jwt_secret_key = os.getenv("JWT_SECRET_KEY")
default_admin_password = os.getenv("DEFAULT_WEB_ADMIN_PASSWORD")
flask_debug_mode = os.getenv("FLASK_DEBUG_MODE_ENABLED", default="false") in (
    "True",
    "true",
    True,
)

"""
Helper Methods
"""


def env_check(required_envs: List[str]):
    """Check for the existence of required env vars

    Keyword arguments:
    required_envs -- List[str] containing vars to check
    """
    logger.info("Running env check...")
    for e in required_envs:
        if os.getenv(e) == "":
            logger.fatal(f"The environment variable {e} cannot be empty.")
            exit(1)
    if "zoom" in active.integrations:
        for var in [
            "ZOOM_ACCOUNT_ID",
            "ZOOM_CLIENT_ID",
            "ZOOM_CLIENT_SECRET",
        ]:
            if os.getenv(var) == "":
                logger.fatal(
                    f"If enabling Zoom meeting auto-create, the {var} variable must be set."
                )
                exit(1)
    if "confluence" in active.integrations and active.integrations.get(
        "confluence"
    ).get("auto_create_rca"):
        for var in [
            "CONFLUENCE_API_URL",
            "CONFLUENCE_API_USERNAME",
            "CONFLUENCE_API_TOKEN",
        ]:
            if os.getenv(var) == "":
                logger.fatal(
                    f"If enabling the Confluence integration to auto create an RCA, the {var} variable must be set."
                )
                exit(1)
    if active.options.get("create_from_reaction"):
        if active.options.get("create_from_reaction").get("reacji") is None:
            logger.fatal(
                f"If enabling auto create via react, the reacji field in config.yaml should be set."
            )
            exit(1)
    if active.options.get("auto_invite_groups").get("enabled"):
        if active.options.get("auto_invite_groups").get("groups") is None:
            logger.fatal(
                f"If enabling auto group invite, the groups field in config.yaml should be set."
            )
            exit(1)
    if "pagerduty" in active.integrations:
        for var in [
            "PAGERDUTY_API_USERNAME",
            "PAGERDUTY_API_TOKEN",
        ]:
            if os.getenv(var) == "":
                logger.fatal(
                    f"If enabling the PagerDuty integration, the {var} variable must be set."
                )
                exit(1)
    if "statuspage" in active.integrations:
        for var in [
            "STATUSPAGE_API_KEY",
            "STATUSPAGE_PAGE_ID",
            "STATUSPAGE_URL",
        ]:
            if os.getenv(var) == "":
                logger.fatal(
                    f"If enabling the Statuspage integration, the {var} variable must be set."
                )
                exit(1)


def startup_message(workspace: str, wrap: bool = False) -> str:
    """
    Returns diagnostic info for startup or troubleshooting
    """
    msg = f"""
--------------------------------------------------------------------------------
                            incident bot {__version__}
--------------------------------------------------------------------------------
Core functionality:
    Database host:                      {database_host}
    Incidents digest channel:           {active.digest_channel}
    Slack workspace:                    {workspace}
    Logging level:                      {log_level}
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
