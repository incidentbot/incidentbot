import requests

from atlassian import Jira
from incidentbot.configuration.settings import settings
from incidentbot.logging import logger


class JiraApi:
    def __init__(self):
        self.jira = Jira(
            url=settings.ATLASSIAN_API_URL,
            username=settings.ATLASSIAN_API_USERNAME,
            password=settings.ATLASSIAN_API_TOKEN,
            cloud=True,
        )

    @property
    def api(self) -> Jira:
        return self.jira

    @property
    def project_id(self) -> str:
        """
        Returns the configured Jira project's ID
        """

        return self.api.project(
            settings.integrations.atlassian.jira.project
        ).get("id")

    @property
    def issue_types(self) -> list[str]:
        """
        Returns a list of issue types
        """

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
                if settings.integrations.atlassian.jira.issue_types is None
                else settings.integrations.atlassian.jira.issue_types
            )

            return issue_types
        except requests.exceptions.HTTPError as error:
            logger.exception("error finding jira issue types", error=error)

    @property
    def priorities(self) -> list[str]:
        """
        Returns a list of priorities for issues
        """

        try:
            resp = self.jira.get_all_priorities()

            priorities = (
                [pr.get("name") for pr in resp]
                if settings.integrations.atlassian.jira.priorities is None
                else settings.integrations.atlassian.jira.priorities
            )

            return priorities
        except requests.exceptions.HTTPError as error:
            logger.exception("error finding jira priorities", error=error)

    def test(self) -> bool:
        try:
            return self.jira.get_project(
                settings.integrations.atlassian.jira.project
            ).get("id")
        except Exception as error:
            logger.exception("error authenticating to jira", error=error)
            logger.exception("please check jira configuration and try again")

    def update_issue_status(
        self,
        incident_name: str,
        incident_status: str,
    ):
        status_mapping = settings.integrations.atlassian.jira.status_mapping
        if not status_mapping:
            logger.debug("no status mapping found for jira integration")

            return

        jira_status = ""

        for status in status_mapping:
            if (
                status.get("incident_status").lower()
                == incident_status.lower()
            ):
                jira_status = status.get("jira_status")
                break

        if not jira_status:
            logger.debug(
                "no jira status found for incident status", incident_status=incident_status
            )
            return

        try:
            project = settings.integrations.atlassian.jira.project
            labels = [incident_name]
            issue_type = settings.integrations.atlassian.jira.issue_types
            logger.info(
                "updating jira issues to status", labels=labels, issue_type=issue_type, status=jira_status
            )
            issues = self.jira.jql_get_list_of_tickets(
                f"project=\"{project}\" and labels in ({','.join(labels)})"
            )

            for issue in issues:
                logger.debug(
                    "updating jira issue to status", key=issue.get("key"), status=jira_status
                )
                self.jira.set_issue_status(issue.get("key"), jira_status)
        except requests.exceptions.HTTPError as error:
            logger.exception("error updating jira issue", error=error)
