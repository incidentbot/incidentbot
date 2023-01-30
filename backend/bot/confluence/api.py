import config
import datetime
import logging

from atlassian import Confluence

logger = logging.getLogger("confluence")


class ConfluenceApi:
    def __init__(self):
        self.confluence = Confluence(
            url=config.confluence_api_url,
            username=config.confluence_api_username,
            password=config.confluence_api_token,
            cloud=True,
        )
        self.today = datetime.datetime.today().strftime("%Y-%m-%d")

    @property
    def api(self) -> Confluence:
        return self.confluence

    def test(self) -> bool:
        if self.confluence.page_exists(
            config.active.integrations.get("confluence").get("space"),
            config.active.integrations.get("confluence").get("parent"),
        ):
            logger.info("Conflluence API test passed")
            return True
        else:
            logger.error("Confluence API test failed, check credentials")
            return False
