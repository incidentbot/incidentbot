import config
import logging
import requests

from atlassian import Jira
from typing import List

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
    def project_id(self) -> str:
        """Returns the configured Jira project's ID"""
        return self.api.project(
            config.active.integrations.get("atlassian").get("jira").get("project")
        ).get("id")

    @property
    def issue_types(self) -> List[str]:
        """Returns a list of issue types"""
        try:
            resp = self.jira.get_issue_types()

            issue_types = (
                [
                    issue_type.get("name")
                    for issue_type in resp
                    if issue_type.get("scope")
                    and issue_type.get("scope").get("project").get("id")
                    == self.project_id
                ]
                if config.active.integrations.get("atlassian")
                .get("jira")
                .get("issue_types")
                is None
                else config.active.integrations.get("atlassian")
                .get("jira")
                .get("issue_types")
            )

            return issue_types
        except requests.exceptions.HTTPError as error:
            logger.error(f"Error finding Jira issue types: {error}")

    @property
    def priorities(self) -> List[str]:
        """Returns a list of priorities for issues"""
        try:
            resp = self.jira.get_all_priorities()

            priorities = (
                [pr.get("name") for pr in resp]
                if config.active.integrations.get("atlassian")
                .get("jira")
                .get("priorities")
                is None
                else config.active.integrations.get("atlassian")
                .get("jira")
                .get("priorities")
            )

            return priorities
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
