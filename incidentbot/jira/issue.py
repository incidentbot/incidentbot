import requests

from incidentbot.configuration.settings import settings
from incidentbot.jira.api import JiraApi
from incidentbot.logging import logger
from incidentbot.models.incident import IncidentDatabaseInterface


class JiraIssue:
    def __init__(
        self,
        description: str,
        incident_id: int,
        issue_type: str,
        summary: str,
    ):
        self.jira = JiraApi()
        self.incident_id = incident_id
        self.incident_data = IncidentDatabaseInterface.get_one(
            id=self.incident_id
        )

        self.description = description
        self.issue_type = issue_type
        self.labels = settings.integrations.atlassian.jira.labels + [
            self.incident_data.channel_name
        ]
        self.summary = summary

    def new(self):
        """
        Creates a Jira issue
        """

        try:
            resp = self.jira.api.issue_create(
                fields={
                    "description": self.description,
                    "issuetype": {"name": self.issue_type},
                    "labels": self.labels,
                    "project": {"id": self.jira.project_id},
                    "summary": self.summary,
                }
            )

            issue_link = (
                f"{settings.ATLASSIAN_API_URL}/browse/{resp.get('key')}"
            )

            logger.info(
                f"Created Jira issue {issue_link} for incident {self.incident_id}"
            )

            return resp
        except requests.exceptions.HTTPError as error:
            logger.error(f"Error creating Jira issue: {error}")

    def __get_priority_id(self, priority: str):
        """
        Returns a priority id by name
        """

        try:
            resp = self.jira.priorities

            return next(
                (
                    prid
                    for prid in resp
                    if prid is not None and prid == priority.lower().title()
                ),
                None,
            )
        except requests.exceptions.HTTPError as error:
            logger.error(f"Error finding Jira priority ID: {error}")
