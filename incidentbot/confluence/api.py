from atlassian import Confluence
from atlassian.errors import ApiError
from incidentbot.configuration.settings import settings
from incidentbot.logging import logger
from pydantic import BaseModel
from requests import HTTPError
from typing import Any


class TemplateResponse(BaseModel):
    """
    A model to represent a Confluence template
    """

    name: str
    labels: list[Any] | None = None
    body: str


class ConfluenceApi:
    def __init__(self):
        self.confluence = Confluence(
            url=settings.ATLASSIAN_API_URL,
            username=settings.ATLASSIAN_API_USERNAME,
            password=settings.ATLASSIAN_API_TOKEN,
            cloud=True,
        )

    @property
    def api(self) -> Confluence:
        return self.confluence

    def get_page_id(self, space: str, title: str) -> str | None:
        spaces = self.confluence.get("api/v2/spaces", params={"keys": space})["results"]
        if not spaces:
            return None
        pages = self.confluence.get(
            "api/v2/pages",
            params={"space-id": spaces[0]["id"], "title": title, "status": "current"},
        )["results"]
        return pages[0]["id"] if pages else None

    def page_exists(self, space: str, title: str) -> bool:
        return self.get_page_id(space, title) is not None

    def get_page_by_id(self, page_id: str) -> dict:
        return self.confluence.get(
            f"api/v2/pages/{page_id}", params={"body-format": "storage"}
        )

    def create_page(self, title: str, body: str, parent_id: str) -> dict:
        parent = self.get_page_by_id(parent_id)
        return self.confluence.post(
            "api/v2/pages",
            data={
                "spaceId": parent["spaceId"],
                "parentId": parent_id,
                "status": "current",
                "title": title,
                "body": {"representation": "storage", "value": body},
            },
        )

    def update_page(self, page: dict, body: str) -> dict:
        return self.confluence.put(
            f"api/v2/pages/{page['id']}",
            data={
                "id": page["id"],
                "status": "current",
                "title": page["title"],
                "body": {"representation": "storage", "value": body},
                "version": {"number": page["version"]["number"] + 1},
            },
        )

    def attach_content(
        self, content: bytes, name: str, content_type: str, page_id: str, comment: str
    ) -> dict:
        # Upload directly to avoid the deprecated attachment-list endpoint.
        return self.confluence.put(
            f"rest/api/content/{page_id}/child/attachment",
            data={"comment": comment, "minorEdit": "true"},
            headers={"X-Atlassian-Token": "nocheck", "Accept": "application/json"},
            files={"file": (name, content, content_type)},
        )

    def fetch_template(self, template_id: int) -> TemplateResponse:
        """
        Fetches the body of a Confluence template
        """

        try:
            response = self.confluence.get_content_template(template_id)
        except ApiError as error:
            logger.exception(
                f"Could not find Confluence template with ID {template_id}: {error}"
            )

            return None
        except HTTPError as error:
            logger.exception(
                f"Error fetching template body from Confluence for template id {template_id}: {error}"
            )

            return None

        return TemplateResponse(
            name=response.get("name"),
            labels=[label["label"] for label in response.get("labels", [])],
            body=response.get("body").get("storage").get("value"),
        )

    def test(self) -> bool:
        try:
            return self.page_exists(
                settings.integrations.atlassian.confluence.space,
                settings.integrations.atlassian.confluence.parent,
            )
        except Exception as error:
            logger.exception("error authenticating to confluence", error=error)
            logger.exception(
                "please check confluence configuration and try again"
            )
