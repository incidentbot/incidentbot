import config
import requests

from bot.jira.api import JiraApi, logger
from bot.models.incident import db_read_incident


class JiraIssue:
    def __init__(
        self,
        incident_id: str,
        description: str,
        issue_type: str,
        priority: str,
        summary: str,
    ):
        self.jira = JiraApi()
        self.exec = self.jira.api
        self.incident_id = incident_id
        self.incident_data = db_read_incident(channel_id=self.incident_id)

        self.description = description
        self.issue_type = issue_type
        self.labels = (
            config.active.integrations.get("atlassian")
            .get("jira")
            .get("labels")
        ) + [self.incident_data.channel_name]
        self.priority = priority
        self.project_id = self.exec.project(
            config.active.integrations.get("atlassian")
            .get("jira")
            .get("project")
        ).get("id")
        self.summary = summary

    def new(self):
        """Creates a Jira issue"""
        priority_id = self.__get_priority_id(priority=self.priority)
        try:
            resp = self.exec.issue_create(
                fields={
                    "description": self.description,
                    "issuetype": {"id": self.issue_type},
                    "labels": self.labels,
                    "priority": {"id": priority_id},
                    "project": {"id": self.project_id},
                    "summary": self.summary,
                }
            )
            return resp
        except requests.exceptions.HTTPError as error:
            logger.error(f"Error creating Jira issue: {error}")

    def __get_priority_id(self, priority: str):
        """Returns a priority id by name"""
        try:
            resp = self.exec.get_all_priorities()
            return next(
                (
                    pr.get("id")
                    for pr in resp
                    if pr.get("name") is not None
                    and pr.get("name") == priority.lower().title()
                ),
                # Set a priority of 3 if the lookup fails
                "3",
            )
        except requests.exceptions.HTTPError as error:
            logger.error(f"Error finding Jira priority ID: {error}")
