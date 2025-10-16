import gitlab
import datetime
import re

from incidentbot.configuration.settings import settings
from incidentbot.gitlab.api import GitLabApi
from incidentbot.exceptions import PostmortemException
from incidentbot.models.database import (
    IncidentEvent,
    IncidentParticipant,
    IncidentRecord,
)
from incidentbot.logging import logger
from typing import Optional, Dict

from .utils import find_issue_by_label


class IncidentPostmortem:
    """
    Generates and posts a markdown postmortem comment on the corresponding
    GitLab incident (issue).
    """

    def __init__(
        self,
        incident: IncidentRecord,
        participants: list[IncidentParticipant],
        timeline: list[IncidentEvent],
        title: str,
    ):
        self.incident = incident
        self.participants = participants
        self.timeline = timeline
        self.title = title
        self.gitlab_api = GitLabApi()

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Sanitizes a filename for use in GitLab."""
        filename = re.sub(r"[^\w\s\-\.]", "_", filename)
        filename = re.sub(r"\s+", "_", filename)
        if "." not in filename:
            filename += ".png"
        return filename

    @staticmethod
    def _get_duration(
        created_at: datetime.datetime, updated_at: datetime.datetime
    ) -> str:
        """Calculates the duration of the incident."""
        end_time = updated_at if updated_at else datetime.datetime.now()
        duration: datetime.timedelta = end_time - created_at

        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        return f"{hours}h {minutes}m {seconds}s"

    def _get_target_gitlab_issue(self):
        """
        Finds the primary GitLab incident (issue) associated with this IncidentRecord.
        Note: Uses raw channel_name without template for backward compatibility.
        """
        proj = self.gitlab_api.project
        if not proj:
            logger.error("Could not retrieve GitLab project for postmortem.")
            return None

        # Use raw channel_name (no template) to match how original postmortem worked
        return find_issue_by_label(
            proj,
            self.incident.channel_name,
            issue_type=settings.integrations.gitlab.issue_type,
        )

    def create(self) -> Optional[str]:
        """
        Creates a postmortem as a comment on the GitLab incident and returns the comment URL.
        """
        incident_issue = self._get_target_gitlab_issue()

        if not incident_issue:
            logger.error(
                "Could not find corresponding GitLab issue for postmortem."
            )
            return None  # Error logged in helper method

        proj = self.gitlab_api.project  # Project is guaranteed to be in cache
        logger.info(
            f"Creating postmortem comment for {self.title} on GitLab issue #{incident_issue.iid}..."
        )

        try:
            # Upload timeline images first and get their markdown references
            image_references = self._upload_timeline_images(
                proj, incident_issue.iid
            )

            # Generate postmortem content
            content = self._generate_postmortem_content(image_references)

            # Create a note (comment) on the incident
            note = incident_issue.notes.create({"body": content})

            url = f"{settings.GITLAB_URL}/{proj.path_with_namespace}/-/issues/{incident_issue.iid}#note_{note.id}"

            logger.info(f"Created postmortem comment on incident: {url}")
            return url

        except gitlab.exceptions.GitlabCreateError as error:
            logger.error(f"Error creating postmortem comment: {error}")
            raise PostmortemException(error)
        except PostmortemException:
            raise
        except Exception as error:
            logger.error(
                f"Unexpected error during postmortem creation: {error}"
            )
            raise PostmortemException(error)

    def _generate_postmortem_content(
        self, image_references: Dict[str, str]
    ) -> str:
        """Generates postmortem content in markdown format."""
        duration_str = self._get_duration(
            self.incident.created_at, self.incident.updated_at
        )

        content_parts = [
            f"## 📋 Post-Mortem: {self.title}\n\n",
            "---\n\n",
            "### Incident Overview\n\n",
            f"Description: {self.incident.description or 'N/A'}\n\n",
            f"Severity: {self.incident.severity or 'N/A'}\n\n",
            f"Duration: {duration_str}\n\n",
            f"Impact: {self.incident.impact or 'N/A'}\n\n",
            f"Components: {self.incident.components or 'N/A'}\n\n",
            f"Created At: {self.incident.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n",
            f"Updated At: {self.incident.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.incident.updated_at else 'N/A'}\n\n",
            "---\n\n",
            "### 👥 Participants\n\n",
            self._generate_participants(),
            "\n---\n\n",
            "### ⏱️ Timeline\n\n",
            self._generate_timeline(image_references),
            "\n---\n\n",
            "### 📝 Action Items\n\n",
            "*To be filled in by the team*\n\n",
            "### 🔍 Root Cause Analysis\n\n",
            "*To be filled in by the team*\n\n",
            "### 🛠️ Preventive Measures\n\n",
            "*To be filled in by the team*\n\n",
        ]

        return "".join(content_parts)

    def _generate_participants(self) -> str:
        """Generates the postmortem section for participants (markdown table)."""
        if not self.participants:
            return "*No participants recorded.*\n"

        rows = ["| Role | User |", "|------|------|"]

        for participant in self.participants:
            role = " ".join(
                word.capitalize() for word in participant.role.split("_")
            )
            rows.append(f"| {role} | {participant.user_name} |")

        return "\n".join(rows) + "\n"

    def _generate_timeline(self, image_references: Dict[str, str]) -> str:
        """Generates the postmortem section for timeline (markdown table)."""
        if not self.timeline:
            return "*No timeline events recorded.*\n"

        rows = ["| Timestamp | Event |", "|-----------|-------|"]

        for event in self.timeline:
            timestamp = event.created_at.strftime("%Y-%m-%d %H:%M:%S")

            if event.image is not None and event.title in image_references:
                # Use the markdown reference from uploaded image
                markdown_ref = image_references[event.title]
                rows.append(f"| {timestamp} | {markdown_ref} |")
            elif event.text:
                # Escape markdown table pipe characters
                event_text = event.text.replace("\n", " ").replace("|", "\\|")
                rows.append(f"| {timestamp} | {event_text} |")

        return "\n".join(rows) + "\n"

    def _upload_timeline_images(
        self, proj, incident_iid: int
    ) -> Dict[str, str]:
        """
        Uploads images from timeline events to the GitLab project.
        Returns a dict mapping event titles to their markdown references.
        """
        image_references = {}
        proj_id = proj.id

        for event in self.timeline:
            if event.image is None:
                continue

            filename = self._sanitize_filename(event.title)

            try:
                files = {"file": (filename, event.image, event.mimetype)}

                response = self.gitlab_api.api.http_post(
                    f"/projects/{proj_id}/uploads", files=files
                )

                if response:
                    markdown = response.get("markdown", "")
                    if markdown:
                        image_references[event.title] = markdown
                        logger.info(
                            f"Uploaded image {filename} for issue #{incident_iid}."
                        )
                    else:
                        logger.warning(
                            f"Upload succeeded but no markdown returned for {filename}."
                        )
                else:
                    logger.error(
                        f"Failed to upload image {filename} for issue #{incident_iid}. "
                        "Response was empty."
                    )

            except gitlab.exceptions.GitlabHttpError as error:
                logger.error(
                    f"HTTP error uploading file {event.title} to project {proj_id}: {error}"
                )
            except Exception as error:
                logger.error(
                    f"Unexpected error uploading file {event.title}: {error}"
                )

        return image_references
