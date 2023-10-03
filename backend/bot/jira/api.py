import config
import logging
import requests

from atlassian import Jira
from typing import Any, List

logger = logging.getLogger("jira")


class JiraApi:
    def __init__(self):
        self.jira = Jira(
            url=config.atlassian_api_url,
            username=config.atlassian_api_username,
            password=config.atlassian_api_token,
            cloud=True,
        )

    @property
    def api(self) -> Jira:
        return self.jira

    @property
    def issue_types(self) -> List[Any]:
        """Returns a list of issue types"""
        try:
            resp = self.jira.get_issue_types()
            return [issue_type for issue_type in resp]
        except requests.exceptions.HTTPError as error:
            logger.error(f"Error finding Jira issue types: {error}")

    @property
    def priorities(self) -> List[Any]:
        """Returns a list of priorities for issues"""
        try:
            resp = self.jira.get_all_priorities()
            return [pr for pr in resp]

        except requests.exceptions.HTTPError as error:
            logger.error(f"Error finding Jira priorities: {error}")

    def test(self) -> bool:
        try:
            return self.jira.get_project(
                config.active.integrations.get("atlassian").get("jira").get("project")
            ).get("id")
        except Exception as error:
            logger.error(f"Error authenticating to Jira: {error}")
            logger.error(f"Please check Jira configuration and try again.")
