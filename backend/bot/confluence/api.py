import config
import datetime

from atlassian import Confluence
from logger import logger


class ConfluenceApi:
    def __init__(self):
        self.confluence = Confluence(
            url=config.atlassian_api_url,
            username=config.atlassian_api_username,
            password=config.atlassian_api_token,
            cloud=True,
        )

    @property
    def api(self) -> Confluence:
        return self.confluence

    def test(self) -> bool:
        try:
            return self.confluence.page_exists(
                config.active.integrations.get("atlassian")
                .get("confluence")
                .get("space"),
                config.active.integrations.get("atlassian")
                .get("confluence")
                .get("parent"),
            )
        except Exception as error:
            logger.error(f"Error authenticating to Confluence: {error}")
            logger.error(
                f"Please check Confluence configuration and try again."
            )
