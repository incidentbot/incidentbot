import os
import secrets

from pydantic import (
    AnyUrl,
    BaseModel,
    BeforeValidator,
    computed_field,
    model_validator,
    TypeAdapter,
)
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)
from typing import Annotated, Any, Tuple, Type
from typing_extensions import Self

__version__ = "v2.1.6"

pagerduty_logo_url = "https://i.imgur.com/IVvdFCV.png"
statuspage_logo_url = "https://i.imgur.com/v4xmF6u.png"


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, list | str):
        return v

    raise ValueError(v)


"""
API
"""


class API(BaseModel):
    enabled: bool | None = False
    enable_docs_endpoint: bool | None = False
    enable_openapi_endpoint: bool | None = False
    enable_redoc_endpoint: bool | None = False
    v1_str: str | None = "/api/v1"


"""
Jobs
"""


class ScrapeForAgingIncidentsJob(BaseModel):
    """
    Model for the jobs scrape_for_aging_incidents_job field
    """

    enabled: bool = True
    ignore_statuses: list = []


class Jobs(BaseModel):
    """
    Model for the jobs field
    """

    scrape_for_aging_incidents: ScrapeForAgingIncidentsJob


"""
Options
"""


class AdditionalWelcomeMessage(BaseModel):
    """
    Model for messages that will be added to the beginning of all incidents
    """

    message: str
    pin: bool | None = False


class GroupAutoInvite(BaseModel):
    """
    Model for groups that should be auto invited to incidents
    """

    name: str
    pagerduty_escalation_policy: str | None = None
    pagerduty_escalation_priority: str | None = "low"
    severities: str | None = "all"


class Options(BaseModel):
    """
    Model for the options field
    """

    additional_welcome_messages: list[AdditionalWelcomeMessage] | None = None
    auto_invite_groups: list[GroupAutoInvite] | None = None
    channel_name_prefix: str | None = "inc"
    channel_name_date_format: str | None = "YYYY-MM-DD"
    channel_name_use_date_prefix: bool | None = False
    meeting_link: str | None = None
    pin_meeting_link_to_channel: bool = False
    skip_logs_for_user_agent: list[str] | None = None
    show_most_recent_incidents_app_home_limit: int = 5
    slack_items_pagination_per_page: int = 5
    timezone: str = "UTC"
    updates_in_threads: bool | None = False


"""
Integrations
"""


class ConfluenceIntegration(BaseModel):
    """
    Model for the confluence field
    """

    auto_create_postmortem: bool | None = False
    enabled: bool = False
    parent: str
    space: str
    template_id: int


class JiraIntegration(BaseModel):
    """
    Model for the jira field
    """

    auto_create_issue: bool = False
    auto_create_issue_type: str | None = None
    enabled: bool = False
    issue_types: list[str]
    labels: list[str] | None = None
    priorities: list[str] | None = None
    project: str
    status_mapping: list[dict[str, str]]

class GitlabIntegration(BaseModel):
    """
    Model for the gitlab field
    """

    auto_create_incident: bool = False
    auto_create_postmortem: bool | None = False
    incident_confidential: bool | None = False
    enabled: bool = False
    labels: list[str] | None = None
    security_labels: list[str] | None = None
    priorities: list[str] | None = None
    project_id: int
    status_mapping: list[dict[str, Any]]
    severity_mapping: list[dict[str, Any]]
    label_template: str | None = None
    issue_type: str | None = "incident"

    @model_validator(mode="after")
    def _validate_issue_type(self) -> Self:
        if self.issue_type is not None and self.issue_type not in ("incident", "issue"):
            raise ValueError("issue_type must be either 'incident' or 'issue'")
        return self


class StatuspageIntegrationPermissions(BaseModel):
    """
    Model for the statuspage permissions field
    """

    groups: list[str] | None = None


class StatuspageIntegration(BaseModel):
    """
    Model for the statuspage field
    """

    enabled: bool = False
    permissions: StatuspageIntegrationPermissions | None = None
    url: str


class AtlassianIntegration(BaseModel):
    """
    Model for the atlaassian field
    """

    confluence: ConfluenceIntegration | None = None
    jira: JiraIntegration | None = None
    statuspage: StatuspageIntegration | None = None


class PagerDutyIntegration(BaseModel):
    """
    Model for the pagerduty field
    """

    enabled: bool = False


class ZoomIntegration(BaseModel):
    """
    Model for the zoom field
    """

    auto_creating_meeting: bool
    enabled: bool = False


class Integrations(BaseModel):
    """
    Model for the integrations field
    """

    atlassian: AtlassianIntegration | None = None
    pagerduty: PagerDutyIntegration | None = None
    zoom: ZoomIntegration | None = None
    gitlab: GitlabIntegration | None = None


"""
Root
"""


class Link(BaseModel):
    """
    Model for the links field
    """

    title: str
    url: str


class MaintenanceWindows(BaseModel):
    """
    Model for the maintenance_windows field
    """

    components: list[str]
    statuses: list[str] | None = ["Scheduled", "In Progress", "Complete"]


class RoleDefinition(BaseModel):
    """
    Model for defining roles for incident participants
    """

    description: str
    is_lead: bool | None = False


class StatusDefinition(BaseModel):
    """
    Model for defining statuses for incidents
    """

    initial: bool | None = False
    final: bool | None = False


class Settings(BaseSettings):
    """
    Root settings model
    """

    """
    yaml
    """

    api: API | None = API()
    digest_channel: str = "incidents"
    emails_enabled: bool = False
    enable_pinned_images: bool = True
    icons: dict[str, dict[str, str]] = {
        "slack": {
            "channel": ":slack:",
            "components": ":jigsaw:",
            "description": ":mag_right:",
            "impact": ":chart_with_upwards_trend:",
            "maintenance": ":hammer_and_wrench:",
            "meeting": ":busts_in_silhouette:",
            "postmortem": ":book:",
            "role": ":bust_in_silhouette:",
            "status": ":fire_extinguisher:",
            "stopwatch": ":stopwatch:",
            "severity": ":rotating_light:",
            "task": ":ballot_box_with_check:",
            "update": ":incoming_envelope:",
        },
    }
    initial_comms_reminder_minutes: int = 30
    initial_role_watcher_minutes: int = 10
    integrations: Integrations | None = None
    jobs: Jobs | None = None
    links: list[Link] | None = None
    maintenance_windows: MaintenanceWindows | None = None
    options: Options | None = Options()
    pin_content_reacji: str = "pushpin"
    platform: str = "slack"
    roles: dict[str, RoleDefinition] = {
        "incident_commander": {
            "description": "The Incident Commander is the decision maker during a major incident, delegating tasks and listening to input from subject matter experts in order to bring the incident to resolution. They become the highest ranking individual on any major incident call, regardless of their day-to-day rank. Their decisions made as commander are final.\n\nYour job as an Incident Commander is to listen to the call and to watch the incident Slack room in order to provide clear coordination, recruiting others to gather context and details. You should not be performing any actions or remediations, checking graphs, or investigating logs. Those tasks should be delegated.\n\nAn IC should also be considering next steps and backup plans at every opportunity, in an effort to avoid getting stuck without any clear options to proceed and to keep things moving towards resolution.\n\nMore information: https://response.pagerduty.com/training/incident_commander/",
            "is_lead": True,
        },
        "scribe": {
            "description": "The purpose of the Scribe is to maintain a timeline of key events during an incident, documenting actions, and keeping track of any follow-up items that will need to be addressed.\n\nMore information: https://response.pagerduty.com/training/scribe/",
        },
        "subject_matter_expert": {
            "description": "A Subject Matter Expert (SME) is a domain expert or designated owner of a component or service that is part of the software stack. These are critical members of the incident response process that play pivotal roles in identifying and resolving individual components of impacted ecosystems.\n\nMore information: https://response.pagerduty.com/training/subject_matter_expert/",
        },
        "communications_liaison": {
            "description": "The purpose of the Communications Liaison is to be the primary individual in charge of notifying our customers of the current conditions, and informing the Incident Commander of any relevant feedback from customers as the incident progresses.\n\nIt's important for the rest of the command staff to be able to focus on the problem at hand, rather than worrying about crafting messages to customers.\nYour job as Communications Liaison is to listen to the call, watch the incident Slack room, and track incoming customer support requests, keeping track of what's going on and how far the incident is progressing (still investigating vs close to resolution).\n\nThe Incident Commander will instruct you to notify customers of the incident and keep them updated at various points throughout the call. You will be required to craft the message, gain approval from the IC, and then disseminate that message to customers.\n\nMore information: https://response.pagerduty.com/training/customer_liaison/"
        },
    }
    root_slash_command: str = "/incidentbot"
    severities: dict[str, str] = {
        "sev1": "This signifies a critical production scenario that impacts most or all users with a major impact on SLAs. This is an all-hands-on-deck scenario that requires swift action to restore operation. Customers must be notified.",
        "sev2": "This signifies a significant production degradation scenario impacting a large portion of users.",
        "sev3": "This signifies a minor production scenario that may or may not result in degradation. This situation is worth coordination to resolve quickly but does not indicate a critical loss of service for users.",
        "sev4": "This signifies an ongoing investigation. This incident has not been promoted to SEV3 yet, indicating there may be little to no impact, but the situation warrants a closer look. This is diagnostic in nature. This is the default setting for a new incident.",
    }
    statuses: dict[str, StatusDefinition] = {
        "investigating": {
            "initial": True,
        },
        "identified": {},
        "monitoring": {},
        "resolved": {
            "final": True,
        },
    }

    """
    .env
    """

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    SECRET_KEY: str = secrets.token_urlsafe(32)

    DOMAIN: str = "localhost"
    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None

    EMAILS_FROM_EMAIL: str | None = None
    EMAILS_FROM_NAME: str | None = None
    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48

    FIRST_SUPERUSER: str = "admin@example.com"
    FIRST_SUPERUSER_PASSWORD: str = "changethis"

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []

    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PASSWORD: str
    POSTGRES_PORT: int
    POSTGRES_USER: str

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URI(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    ATLASSIAN_API_URL: str | None = None
    ATLASSIAN_API_USERNAME: str | None = None
    ATLASSIAN_API_TOKEN: str | None = None

    BETTERSTACK_UPTIME_API_TOKEN: str | None = None

    PAGERDUTY_API_TOKEN: str | None = None
    PAGERDUTY_API_USERNAME: str | None = None

    SLACK_APP_TOKEN: str | None = None
    SLACK_BOT_TOKEN: str | None = None
    SLACK_USER_TOKEN: str | None = None

    STATUSPAGE_API_KEY: str | None = None
    STATUSPAGE_PAGE_ID: str | None = None

    ZOOM_ACCOUNT_ID: str | None = None
    ZOOM_CLIENT_ID: str | None = None
    ZOOM_CLIENT_SECRET: str | None = None

    GITLAB_URL: str | None = None
    GITLAB_API_TOKEN: str | None = None

    IS_MIGRATION: bool | None = False
    IS_TEST_ENVIRONMENT: bool | None = False

    LOG_LEVEL: str = "INFO"
    LOG_TYPE: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def server_host(self) -> str:
        # Use HTTPS for anything other than local development
        if self.ENVIRONMENT == "local":
            return f"http://{self.DOMAIN}"
        return f"https://{self.DOMAIN}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        yaml_file=os.getenv("CONFIG_FILE_PATH", "config.yaml"),
    )

    def _check_required_var(self, var_name: str, value: str | None) -> None:
        if not value:
            message = f"The value of {var_name} cannot be empty."
            raise ValueError(message)

    def _check_required_integration_var(
        self, var_name: str, value: str | None, integration: str
    ) -> None:
        if not value:
            message = f"The value of {var_name} cannot be empty when enabling the {integration} integration."
            raise ValueError(message)

    @model_validator(mode="after")
    def _check_required_vars(self) -> Self:
        self._check_required_var("POSTGRES_DB", self.POSTGRES_DB)
        self._check_required_var("POSTGRES_HOST", self.POSTGRES_HOST)
        self._check_required_var("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)
        self._check_required_var("POSTGRES_PORT", self.POSTGRES_PORT)
        self._check_required_var("POSTGRES_USER", self.POSTGRES_USER)

        if not (
            TypeAdapter(bool).validate_python(self.IS_MIGRATION)
            or TypeAdapter(bool).validate_python(self.IS_TEST_ENVIRONMENT)
        ):
            self._check_required_var("SLACK_APP_TOKEN", self.SLACK_APP_TOKEN)
            self._check_required_var("SLACK_BOT_TOKEN", self.SLACK_BOT_TOKEN)
            self._check_required_var("SLACK_USER_TOKEN", self.SLACK_USER_TOKEN)

            if (
                self.integrations
                and self.integrations.atlassian
                and self.integrations.atlassian.confluence
                and self.integrations.atlassian.confluence.enabled
            ):
                self._check_required_integration_var(
                    "ATLASSIAN_API_URL", self.ATLASSIAN_API_URL, "Confluence"
                )
                self._check_required_integration_var(
                    "ATLASSIAN_API_USERNAME",
                    self.ATLASSIAN_API_USERNAME,
                    "Confluence",
                )
                self._check_required_integration_var(
                    "ATLASSIAN_API_TOKEN",
                    self.ATLASSIAN_API_TOKEN,
                    "Confluence",
                )

            if (
                self.integrations
                and self.integrations.atlassian
                and self.integrations.atlassian.jira
                and self.integrations.atlassian.jira.enabled
            ):
                self._check_required_integration_var(
                    "ATLASSIAN_API_URL", self.ATLASSIAN_API_URL, "Jira"
                )
                self._check_required_integration_var(
                    "ATLASSIAN_API_USERNAME",
                    self.ATLASSIAN_API_USERNAME,
                    "Jira",
                )
                self._check_required_integration_var(
                    "ATLASSIAN_API_TOKEN", self.ATLASSIAN_API_TOKEN, "Jira"
                )

            if (
                self.integrations
                and self.integrations.atlassian
                and self.integrations.atlassian.statuspage
                and self.integrations.atlassian.statuspage.enabled
            ):
                self._check_required_integration_var(
                    "STATUSPAGE_API_KEY", self.STATUSPAGE_API_KEY, "Statuspage"
                )
                self._check_required_integration_var(
                    "STATUSPAGE_PAGE_ID",
                    self.STATUSPAGE_PAGE_ID,
                    "Statuspage",
                )

            if (
                self.integrations
                and self.integrations.pagerduty
                and self.integrations.pagerduty.enabled
            ):
                self._check_required_integration_var(
                    "PAGERDUTY_API_USERNAME",
                    self.PAGERDUTY_API_USERNAME,
                    "PagerDuty",
                )
                self._check_required_integration_var(
                    "PAGERDUTY_API_TOKEN",
                    self.PAGERDUTY_API_TOKEN,
                    "PagerDuty",
                )

            if (
                self.integrations
                and self.integrations.zoom
                and self.integrations.zoom.enabled
            ):
                self._check_required_integration_var(
                    "ZOOM_ACCOUNT_ID", self.ZOOM_ACCOUNT_ID, "Zoom"
                )
                self._check_required_integration_var(
                    "ZOOM_CLIENT_ID", self.ZOOM_CLIENT_ID, "Zoom"
                )
                self._check_required_integration_var(
                    "ZOOM_CLIENT_SECRET", self.ZOOM_CLIENT_SECRET, "Zoom"
                )

            if (
                self.integrations
                and self.integrations.gitlab
                and self.integrations.gitlab.enabled
            ):
                self._check_required_integration_var(
                    "GITLAB_URL", self.GITLAB_URL, "Gitlab"
                )
                self._check_required_integration_var(
                    "GITLAB_API_TOKEN", self.GITLAB_API_TOKEN, "Gitlab"
                )

        return self

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (
            env_settings,
            YamlConfigSettingsSource(settings_cls),
            dotenv_settings,
        )


settings = Settings()
