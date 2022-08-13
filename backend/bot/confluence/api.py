import config
import datetime
import logging

from atlassian import Confluence

logger = logging.getLogger(__name__)


confluence = Confluence(
    url=config.confluence_api_url,
    username=config.confluence_api_username,
    password=config.confluence_api_token,
    cloud=True,
)

today = datetime.datetime.today().strftime("%Y-%m-%d")
