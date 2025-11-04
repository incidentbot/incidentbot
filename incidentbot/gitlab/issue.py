import gitlab

from incidentbot.configuration.settings import settings
from incidentbot.gitlab.api import GitLabApi
from incidentbot.logging import logger
from incidentbot.models.incident import IncidentDatabaseInterface
from typing import Optional, Dict, Any

from .utils import (
    get_severity_label_mapping,
    map_severity,
    format_channel_label,
    find_issue_by_label,
    get_initial_status_labels,
)


class GitLabIncident:
    """
    Handles the creation and updating of a GitLab incident / issue
    based on external incident data.
    """

    def __init__(
        self,
        description: str,
        incident_id: int,
        status: str,
        severity: str,
        summary: str,
    ):
        self.gitlab_api = GitLabApi()
        self.incident_id = incident_id

        self.incident_data = IncidentDatabaseInterface.get_one(
            id=self.incident_id
        )

        self.description = description
        self.status = status
        self.summary = summary
        self.severity = map_severity(severity)

        # Build labels list
        channel_label = format_channel_label(self.incident_data.channel_name)
        severity_labels = get_severity_label_mapping().get(
            severity.lower(), []
        )
        self.labels = (
            settings.integrations.gitlab.labels
            + [channel_label]
            + severity_labels
        )

        logger.info(
            f"Severity input {severity} mapped to GitLab severity {self.severity}"
        )

    def _get_incident_by_channel_name(self):
        """
        Finds the primary GitLab incident associated with this external incident.
        Uses the unique channel_name label to identify the incident.
        """
        proj = self.gitlab_api.project
        if not proj:
            logger.error(
                "Could not retrieve GitLab project for incident search."
            )
            return None

        return find_issue_by_label(
            proj,
            self.incident_data.channel_name,
            issue_type=settings.integrations.gitlab.issue_type or "incident",
        )

    def _add_resource_link(
        self, incident_id: int, incident_iid: int, link: str, title: str
    ):
        """Helper to add a resource link to a GitLab issue."""
        try:
            self.gitlab_api.add_issue_resource_link(
                issue_id=incident_id,
                link=link,
                title=title,
            )
        except Exception as error:
            logger.error(
                f"Error linking '{title}' to GitLab issue #{incident_iid} ({incident_id}): {error}"
            )

    def new(self) -> Optional[Dict[str, Any]]:
        """
        Creates a new GitLab issue and optionally adds related links/severity.
        Returns a dictionary with incident details if successful, None otherwise.
        """
        proj = self.gitlab_api.project
        if not proj:
            logger.error(
                "Could not retrieve GitLab project to create incident."
            )
            return None

        # Build complete labels list
        labels = self._build_new_issue_labels()

        # Create the Issue/Incident
        try:
            incident = proj.issues.create(
                {
                    "title": self.summary,
                    "description": self.description,
                    "labels": labels,
                    "issue_type": settings.integrations.gitlab.issue_type
                    or "incident",
                    "confidential": settings.integrations.gitlab.incident_confidential
                    or False,
                }
            )
        except gitlab.exceptions.GitlabCreateError as error:
            logger.error(f"Error creating GitLab issue: {error}")
            return None
        except Exception as error:
            logger.error(
                f"Unexpected error during GitLab issue creation: {error}"
            )
            return None

        # Post-creation actions (severity and links for incidents only)
        if settings.integrations.gitlab.issue_type == "incident":
            self._configure_incident_specifics(incident)

        logger.info(
            f"Created GitLab issue #{incident.iid} ({incident.web_url}) "
            f"for external incident {self.incident_id} with severity {self.severity}."
        )

        return {
            "id": incident.id,
            "iid": incident.iid,
            "web_url": incident.web_url,
            "severity": self.severity,
        }

    def _build_new_issue_labels(self) -> list:
        """Builds the complete list of labels for a new issue."""
        labels = self.labels.copy()

        # Add initial investigating status labels
        initial_status_labels = get_initial_status_labels()
        if initial_status_labels:
            logger.info("Adding 'Investigating' status labels to new issue.")
            labels.extend(initial_status_labels)

        # Add security labels if applicable
        if (
            self.incident_data.is_security_incident
            and settings.integrations.gitlab.security_labels
        ):
            logger.info("Adding security labels to GitLab issue.")
            labels.extend(settings.integrations.gitlab.security_labels)

        return labels

    def _configure_incident_specifics(self, incident):
        """
        Configures incident-specific settings (severity and resource links).
        Only called for issue_type='incident'.
        """
        incident_id = incident.id
        incident_iid = incident.iid

        # Set incident severity
        try:
            self.gitlab_api.set_incident_severity(
                issue_iid=incident_iid, severity=self.severity
            )
        except Exception as error:
            logger.warning(
                f"Error setting severity for GitLab issue #{incident_iid}: {error}"
            )

        # Link the primary Slack channel
        self._add_resource_link(
            incident_id=incident_id,
            incident_iid=incident_iid,
            link=self.incident_data.link,
            title="Slack Channel for Incident",
        )

        # Link additional comms channel if provided
        if self.incident_data.additional_comms_channel_link:
            logger.info("Linking additional comms channel to GitLab issue.")
            self._add_resource_link(
                incident_id=incident_id,
                incident_iid=incident_iid,
                link=self.incident_data.additional_comms_channel_link,
                title="Additional Comms Channel",
            )

    def update_status(self, status: str) -> Optional[Dict[str, Any]]:
        """
        Updates the paging status and state (open/closed) of the incident.
        Status should be one of: triggered, acknowledged, resolved.
        """
        incident = self._get_incident_by_channel_name()
        if not incident:
            return None  # Error logged in helper method

        # Only incidents support status updates
        if settings.integrations.gitlab.issue_type != "incident":
            logger.info(
                "Skipping status update as issue_type is not 'incident'."
            )
            return None

        input_status = status.lower()

        try:
            # Update labels to reflect status
            status_labels = ["triggered", "acknowledged", "resolved"]

            # Remove existing status labels and add the new one
            current_labels = [
                label
                for label in incident.labels
                if label.lower() not in status_labels
            ]
            current_labels.append(input_status)

            incident.labels = current_labels

            # Close the incident if resolved
            if input_status == "resolved":
                incident.state_event = "close"

            incident.save()

            logger.info(
                f"Updated GitLab issue #{incident.iid} status to {input_status}."
            )

            return {
                "id": incident.id,
                "iid": incident.iid,
                "status": input_status,
            }
        except gitlab.exceptions.GitlabUpdateError as error:
            logger.error(
                f"Error updating GitLab issue status for #{incident.iid}: {error}"
            )
            return None
        except Exception as error:
            logger.error(
                f"Unexpected error updating GitLab issue status for #{incident.iid}: {error}"
            )
            return None
