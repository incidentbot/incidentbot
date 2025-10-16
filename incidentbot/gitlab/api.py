import gitlab

from incidentbot.configuration.settings import settings
from incidentbot.logging import logger
from typing import Optional

from .utils import (
    build_mapping_dict,
    find_issues_by_label,
    update_issue_labels,
)


class GitLabApi:
    """
    Wrapper for GitLab API interactions, including REST and GraphQL clients.
    Implements caching for the GitLab project object.
    """

    def __init__(self):
        self._project = None
        self._initialize_clients()

    def _initialize_clients(self):
        """Initializes and authenticates the REST and GraphQL clients."""
        gitlab_url = settings.GITLAB_URL
        api_token = settings.GITLAB_API_TOKEN

        self.gitlab = gitlab.Gitlab(
            url=gitlab_url,
            private_token=api_token,
        )
        self.gitlab.auth()

        self.gitlabgql = gitlab.GraphQL(
            url=gitlab_url,
            token=api_token,
        )

    @property
    def api(self) -> gitlab.Gitlab:
        """Returns the configured GitLab REST API client."""
        return self.gitlab

    @property
    def project(self):
        """
        Returns the configured GitLab project, using a cached instance if available.
        """
        if self._project:
            return self._project

        project_id = settings.integrations.gitlab.project_id
        try:
            self._project = self.gitlab.projects.get(project_id)
            return self._project
        except gitlab.exceptions.GitlabGetError as error:
            logger.error(
                f"Error getting GitLab project ID {project_id}: {error}"
            )
            return None

    @property
    def project_id(self) -> Optional[str]:
        """Returns the configured GitLab project's ID."""
        proj = self.project
        return str(proj.id) if proj else None

    @property
    def project_path(self) -> Optional[str]:
        """Returns the configured GitLab project's path_with_namespace."""
        proj = self.project
        return proj.path_with_namespace if proj else None

    @property
    def labels(self) -> list[str]:
        """
        Returns a list of available labels in the project.
        """
        proj = self.project
        if not proj:
            return []

        try:
            labels = proj.labels.list(get_all=True)
            return [label.name for label in labels]
        except gitlab.exceptions.GitlabListError as error:
            logger.error(
                f"Error listing GitLab labels for project {proj.id}: {error}"
            )
            return []

    def test(self) -> bool:
        """
        Test the GitLab connection and authentication by retrieving the project.
        """
        try:
            proj = self.project
            if proj is None or proj.id is None:
                logger.error(
                    "GitLab connection failed. Project could not be retrieved."
                )
                logger.error(
                    "Please check GitLab configuration and try again."
                )
                return False
            return True
        except Exception as error:
            logger.error(f"Unexpected error authenticating to GitLab: {error}")
            logger.error("Please check GitLab configuration and try again.")
            return False

    def _update_issues_with_mapping(
        self,
        incident_name: str,
        incident_value: str,
        mapping_list: list,
        mapping_key: str,
        gitlab_value_key: str,
        update_field: Optional[str] = None,
    ):
        """
        Generic method to update issues based on severity or status mappings.

        Args:
            incident_name: Channel name to find issues
            incident_value: Severity or status value from incident
            mapping_list: Configuration mapping list
            mapping_key: Key for incident value in mapping (e.g., 'incident_severity')
            gitlab_value_key: Key for GitLab value in mapping (e.g., 'gitlab_severity')
            update_field: Optional field to update on issue (e.g., 'state_event')
        """
        if not mapping_list:
            logger.warning(
                f"No {mapping_key} mapping found for GitLab integration."
            )
            return

        mapping_dict = build_mapping_dict(mapping_list, mapping_key)
        mapping = mapping_dict.get(incident_value.lower())

        if not mapping:
            logger.warning(
                f"No mapping found for {mapping_key}={incident_value}."
            )
            return

        gitlab_value = mapping.get(gitlab_value_key)
        gitlab_labels = mapping.get("gitlab_labels", [])

        if not gitlab_value and not gitlab_labels:
            logger.warning(
                f"No GitLab {gitlab_value_key} or labels mapped for {incident_value}."
            )
            return

        proj = self.project
        if not proj:
            logger.error("Could not retrieve GitLab project for update.")
            return

        try:
            logger.info(
                f"Updating GitLab issues with label {incident_name} to "
                f"{gitlab_value_key}={gitlab_value}, labels={gitlab_labels}."
            )

            issues = find_issues_by_label(proj, incident_name)

            if not issues:
                return  # Warning already logged by utility function

            for issue in issues:
                logger.debug(
                    f"Updating GitLab issue #{issue.iid}: "
                    f"{gitlab_value_key}={gitlab_value}, labels={gitlab_labels}."
                )

                # Update labels if specified
                if gitlab_labels:
                    updated_labels = update_issue_labels(issue, gitlab_labels)
                    issue.labels = updated_labels

                # Update specific field if requested (e.g., state_event)
                if update_field and gitlab_value:
                    setattr(issue, update_field, gitlab_value)

                issue.save()

                # For severity updates on incidents, use GraphQL
                if (
                    mapping_key == "incident_severity"
                    and settings.integrations.gitlab.issue_type == "incident"
                    and gitlab_value
                ):
                    logger.info(
                        f"Setting incident severity of #{issue.iid} to {gitlab_value}"
                    )
                    self.set_incident_severity(
                        issue_iid=issue.iid, severity=gitlab_value
                    )

        except gitlab.exceptions.GitlabUpdateError as error:
            logger.error(f"Error updating GitLab issue: {error}")
        except Exception as error:
            logger.error(f"Unexpected error updating GitLab issue: {error}")

    def update_issue_severity(
        self, incident_name: str, incident_severity: str
    ):
        """
        Updates GitLab issue/incident with the given incident name to the mapped severity.
        """
        self._update_issues_with_mapping(
            incident_name=incident_name,
            incident_value=incident_severity,
            mapping_list=settings.integrations.gitlab.severity_mapping,
            mapping_key="incident_severity",
            gitlab_value_key="gitlab_severity",
        )

    def update_issue_status(self, incident_name: str, incident_status: str):
        """
        Updates GitLab issue/incident with the given incident name to the mapped status.
        """
        self._update_issues_with_mapping(
            incident_name=incident_name,
            incident_value=incident_status,
            mapping_list=settings.integrations.gitlab.status_mapping,
            mapping_key="incident_status",
            gitlab_value_key="gitlab_status",
            update_field="state_event",
        )

    def set_incident_severity(self, issue_iid: int, severity: str) -> bool:
        """
        Sets the severity of a specific issue using the GitLab GraphQL API.

        Args:
            issue_iid: The internal ID (IID) of the issue
            severity: The severity level (CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN)

        Returns:
            True if successful, False otherwise
        """
        valid_severities = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]
        if severity not in valid_severities:
            logger.error(
                f"Invalid severity level {severity}. "
                f"Must be one of: {', '.join(valid_severities)}"
            )
            return False

        project_path = self.project_path
        if not project_path:
            logger.error(
                "Could not retrieve project path for GraphQL mutation."
            )
            return False

        query = """
        mutation updateIssuableSeverity($projectPath: ID!, $severity: IssuableSeverity!, $iid: String!) {
            issueSetSeverity(
                input: {iid: $iid, severity: $severity, projectPath: $projectPath}
            ) {
                errors
                issue {
                    iid
                    id
                    severity
                }
            }
        }
        """

        variables = {
            "iid": str(issue_iid),
            "severity": severity,
            "projectPath": project_path,
        }

        try:
            response = self.gitlabgql.execute(query, variables)

            errors = (
                response.get("data", {})
                .get("issueSetSeverity", {})
                .get("errors", [])
            )
            if errors:
                logger.error(
                    f"GraphQL error setting issue severity for #{issue_iid}: {errors}"
                )
                return False

            logger.info(
                f"Set GitLab issue #{issue_iid} severity to {severity}."
            )
            return True
        except Exception as error:
            logger.error(
                f"Error setting GitLab issue severity via GraphQL for #{issue_iid}: {error}"
            )
            return False

    def add_issue_resource_link(
        self, issue_id: int, link: str, title: Optional[str] = None
    ) -> bool:
        """
        Adds a related resource link to a specific issue using the GitLab GraphQL API.

        Args:
            issue_id: The ID (global ID) of the issue
            link: The URL to be added as a resource link
            title: Optional title/text for the link

        Returns:
            True if successful, False otherwise
        """
        mutation = """
        mutation CreateIssuableResourceLink($input: IssuableResourceLinkCreateInput!) {
            issuableResourceLinkCreate(input: $input) {
                issuableResourceLink {
                    id
                    link
                    linkType
                    linkText
                }
                errors
            }
        }
        """

        variables = {
            "input": {
                "id": f"gid://gitlab/Issue/{issue_id}",
                "link": link,
                "linkText": title,
                "linkType": "general",
            }
        }

        try:
            response = self.gitlabgql.execute(mutation, variables)

            errors = (
                response.get("data", {})
                .get("issuableResourceLinkCreate", {})
                .get("errors", [])
            )
            if errors:
                logger.error(
                    f"GraphQL error adding resource link to #{issue_id}: {errors}"
                )
                return False

            logger.info(
                f"Added resource link ({title}) to GitLab issue #{issue_id}."
            )
            return True
        except Exception as error:
            logger.error(
                f"Error adding resource link via GraphQL for #{issue_id}: {error}"
            )
            return False
