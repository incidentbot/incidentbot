import datetime
import mimetypes
import re
import uuid
from pathlib import Path

from incidentbot.configuration.settings import settings
from incidentbot.confluence.api import ConfluenceApi
from incidentbot.exceptions import PostmortemException
from incidentbot.models.database import (
    IncidentEvent,
    IncidentParticipant,
    IncidentRecord,
)
from incidentbot.logging import logger
from requests.exceptions import HTTPError


class IncidentPostmortem:
    def __init__(
        self,
        incident: IncidentRecord,
        participants: list[IncidentParticipant],
        timeline: list[IncidentEvent],
        title: str,
    ):
        self.parent_page = settings.integrations.atlassian.confluence.parent
        self.space = settings.integrations.atlassian.confluence.space
        self.incident = incident
        self.participants = participants
        self.timeline = timeline
        self.title = title

        self.confluence = ConfluenceApi()
        self.exec = self.confluence.api

    def create(self) -> str | None:
        """
        Creates a postmortem page and returns the created page's URL
        """

        try:
            parent_page_id = self.exec.get_page_id(
                self.space, self.parent_page
            )
            logger.info(
                "creating postmortem in confluence",
                title=self.title,
                space=self.space,
                parent=self.parent_page,
            )

            # Fetch template content
            template = self.confluence.fetch_template(
                settings.integrations.atlassian.confluence.template_id
            )
            if template:
                # Get original template body
                html = template.body

                # !ib-inject-description
                html = html.replace(
                    "!ib-inject-description", self.incident.description
                )
                # !ib-inject-duration
                html = html.replace(
                    "!ib-inject-duration",
                    self.__get_duration(),
                )
                # !ib-inject-impact
                html = html.replace("!ib-inject-impact", self.incident.impact)
                # !ib-inject-components
                html = html.replace(
                    "!ib-inject-components", self.incident.components
                )
                # !ib-inject-severity
                html = html.replace(
                    "!ib-inject-severity", self.incident.severity
                )
                # !ib-inject-created-at
                html = html.replace(
                    "!ib-inject-created-at", str(self.incident.created_at)
                )
                # !ib-inject-updated-at
                html = html.replace(
                    "!ib-inject-updated-at", str(self.incident.updated_at)
                )
                # !ib-inject-participants
                html = html.replace(
                    "!ib-inject-participants", self.__generate_participants()
                )

                # Create postmortem doc
                if self.exec.page_exists(
                    space=self.space, title=self.parent_page
                ):
                    try:
                        self.exec.create_page(
                            self.space,
                            self.title,
                            html,
                            parent_id=parent_page_id,
                            type="page",
                            representation="storage",
                            editor="v2",
                        )
                        created_page_id = self.exec.get_page_id(
                            self.space, self.title
                        )
                        created_page_info = self.exec.get_page_by_id(
                            page_id=created_page_id
                        )
                        url = (
                            created_page_info["_links"]["base"]
                            + created_page_info["_links"]["webui"]
                        )
                    except HTTPError as error:
                        logger.exception(
                            "error creating postmortem page", error=error
                        )
                        raise PostmortemException(error) from error

                    try:
                        # Replace timeline tag if one exists
                        page = self.exec.get_page_by_id(
                            created_page_id, "body.storage"
                        )
                        html = page.get("body").get("storage").get("value")
                        html = html.replace(
                            "!ib-inject-timeline",
                            self.__generate_timeline(created_page_id),
                        )

                        self.exec.update_page(
                            created_page_id,
                            page.get("title"),
                            html,
                            parent_id=parent_page_id,
                            type="page",
                            representation="storage",
                        )

                        return url
                    except HTTPError as error:
                        logger.exception(
                            "error updating postmortem page", error=error
                        )
                        raise PostmortemException(error) from error
                else:
                    logger.error(
                        "could not create postmortem page - does the parent page exist"
                    )
                    raise PostmortemException(
                        "Couldn't create postmortem page, does the parent page exist?"
                    )
            else:
                return None
        except Exception as error:
            logger.exception("error generating postmortem", error=error)

    def __generate_participants(self) -> str:
        """
        Generates the postmortem section for participants detail
        """

        base = f'<table data-table-width="760" data-layout="default" ac:local-id="{str(uuid.uuid4())}"><tbody><tr><th><p><strong>Role</strong></p></th><th><p><strong>User</strong></p></th></tr>'
        all_items_formatted = ""
        for item in self.participants:
            all_items_formatted += f"<tr><td><p>{item.role.replace("_", " ").title()}</p></td><td><p>{item.user_name}</p></td></tr>"
        base += all_items_formatted
        base += "</tbody></table>"

        return base

    def __generate_timeline(self, created_page_id: str) -> str:
        """
        Generates the postmortem section for timeline detail
        """

        base = f'<table data-table-width="760" data-layout="default" ac:local-id="{str(uuid.uuid4())}"><tbody><tr><th><p><strong>Timestamp</strong></p></th><th><p><strong>Event</strong></p></th></tr>'
        all_items_formatted = ""
        existing_attachments = self.__get_existing_attachment_names(
            created_page_id
        )
        for item in self.timeline:
            if item.image is not None:
                attachment_name = self.__build_image_attachment_name(item)
                legacy_attachment_name = item.title or attachment_name
                attachment_name_to_render = attachment_name

                if attachment_name in existing_attachments:
                    pass
                elif legacy_attachment_name in existing_attachments:
                    # Compatibility for older postmortems that used raw item titles.
                    attachment_name_to_render = legacy_attachment_name
                else:
                    try:
                        # Attach content to document
                        self.exec.attach_content(
                            comment=item.title,
                            content=item.image,
                            content_type=item.mimetype,
                            name=attachment_name,
                            page_id=created_page_id,
                            space=settings.integrations.atlassian.confluence.space,
                            title=attachment_name,
                        )
                        existing_attachments.add(attachment_name)
                    except Exception as error:
                        logger.error(
                            "error attaching file to postmortem",
                            title=item.title,
                            attachment=attachment_name,
                            page_id=created_page_id,
                            error=str(error),
                        )
                        all_items_formatted += (
                            f"<tr><td><p>{item.created_at}</p></td>"
                            + "<td><p>Image attachment failed to synchronize: "
                            + f"{item.title}</p></td></tr>"
                        )
                        continue

                all_items_formatted += (
                    f"<tr><td><p>{item.created_at}</p></td>"
                    + '<td><p /><ac:image ac:align="center" ac:layout="center" '
                    + f'ac:alt="{item.title}"><ri:attachment ri:filename="'
                    + f'{attachment_name_to_render}" ri:version-at-save="1" '
                    + "/></ac:image><p /></td></tr>"
                )
            else:
                all_items_formatted += f"<tr><td><p>{item.created_at}</p></td><td><p>{item.text}</p></td></tr>"
        all_items_formatted += (
            "<tr><td><p>&hellip;</p></td><td><p>&hellip;</p></td></tr>"
        )
        base += all_items_formatted
        base += "</tbody></table>"

        return base

    def __build_image_attachment_name(self, item: IncidentEvent) -> str:
        original_title = (item.title or "pinned-image").strip()
        stem = Path(original_title).stem or "pinned-image"
        stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-.")
        if not stem:
            stem = "pinned-image"

        suffix = ""
        raw_suffix = Path(original_title).suffix.lower()
        if raw_suffix and re.fullmatch(r"\.[a-z0-9]+", raw_suffix):
            suffix = raw_suffix
        elif item.mimetype:
            guessed = mimetypes.guess_extension(item.mimetype)
            if isinstance(guessed, str):
                suffix = guessed.lower()

        unique_source = item.message_ts or str(item.id) or "unknown"
        unique_source = re.sub(r"[^A-Za-z0-9._-]+", "-", unique_source).strip(
            "-"
        )
        if not unique_source:
            unique_source = "unknown"

        return f"{stem}-{unique_source}{suffix}"

    def __get_existing_attachment_names(self, page_id: str) -> set[str]:
        names: set[str] = set()
        get_attachments = getattr(
            self.exec, "get_attachments_from_content", None
        )
        if not callable(get_attachments):
            return names

        start = 0
        limit = 250

        while True:
            try:
                response = get_attachments(
                    page_id=page_id, start=start, limit=limit
                )
            except TypeError:
                response = get_attachments(page_id, start=start, limit=limit)
            except Exception as error:
                logger.error(
                    "unable to list existing attachments for postmortem page",
                    page_id=page_id,
                    error=str(error),
                )
                return names

            if not isinstance(response, dict):
                return names

            results = response.get("results")
            if not isinstance(results, list):
                return names

            for entry in results:
                if not isinstance(entry, dict):
                    continue
                title = entry.get("title")
                if isinstance(title, str) and title:
                    names.add(title)

            if len(results) < limit:
                return names
            start += limit

    def __get_duration(self) -> str:
        duration = datetime.datetime.now() - self.incident.created_at
        seconds = duration.seconds
        hours = seconds // 3600
        minutes = (seconds // 60) % 60

        return f"{hours}h{minutes}m"
