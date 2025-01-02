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

    def fetch_template(self, template_id: int) -> TemplateResponse:
        """
        Fetches the body of a Confluence template
        """

        try:
            response = self.confluence.get_content_template(template_id)
        except ApiError as error:
            logger.error(
                f"Could not find Confluence template with ID {template_id}: {error}"
            )

            return None
        except HTTPError as error:
            logger.error(
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
            return self.confluence.page_exists(
                settings.integrations.atlassian.confluence.space,
                settings.integrations.atlassian.confluence.parent,
            )
        except Exception as error:
            logger.error(f"Error authenticating to Confluence: {error}")
            logger.error(
                "Please check Confluence configuration and try again."
            )
