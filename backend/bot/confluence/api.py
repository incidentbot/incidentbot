import config
import datetime
import logging

from atlassian import Confluence

logger = logging.getLogger(__name__)


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
            config.confluence_space, config.confluence_parent_page
        ):
            logger.info("Conflluence API test passed")
            return True
        else:
            logger.error("Confluence API test failed, check credentials")
            return False
