import os
import secrets
from typing import Literal

from pydantic import computed_field, Field, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)
from typing import Self

from incidentbot.configuration.schema import (
    Automation,
    Integrations,
    Jobs,
    Link,
    MatrixSettings,
    Metrics,
    Options,
    Reminder,
    ReminderAction,
    Conditions,
    RoleDefinition,
    StatusDefinition,
)


pagerduty_logo_url = "https://i.imgur.com/IVvdFCV.png"
statuspage_logo_url = "https://i.imgur.com/v4xmF6u.png"


_DEFAULT_REMINDERS: list[Reminder] = [
    Reminder(
        id="comms_reminder",
        message="Time to send a status update?",
        interval_minutes=30,
        actions=[
            ReminderAction(type="send_update", label="Send Update"),
            ReminderAction(type="snooze", intervals=[30, 60, 90]),
            ReminderAction(type="dismiss", label="Stop Reminders"),
        ],
    ),
    Reminder(
        id="role_watcher",
        message="No roles have been assigned yet — please review and claim as needed.",
        interval_minutes=10,
        once=True,
        conditions=Conditions(no_roles_claimed=True),
        include_role_buttons=True,
        actions=[ReminderAction(type="dismiss", label="Dismiss")],
    ),
]


class Settings(BaseSettings):
    # ── YAML config fields ────────────────────────────────────────────────────

    digest_channel: str = "incidents"
    enable_pinned_images: bool = True
    icons: dict[str, dict[str, str]] = {
        "slack": {
            "channel": ":slack:",
            "components": ":jigsaw:",
            "description": ":mag_right:",
            "impact": ":chart_with_upwards_trend:",
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
    integrations: Integrations | None = None
    jobs: Jobs = Field(default_factory=Jobs)
    matrix: MatrixSettings | None = None
    metrics: Metrics = Field(default_factory=Metrics)
    reminders: list[Reminder] = Field(default_factory=lambda: list(_DEFAULT_REMINDERS))
    automations: list[Automation] = Field(default_factory=list)
    links: list[Link] | None = None
    options: Options | None = Options()
    pin_content_reacji: str = "pushpin"
    platform: Literal["slack", "matrix"] = "slack"
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
            "description": "The purpose of the Communications Liaison is to be the primary individual in charge of notifying our customers of the current conditions, and informing the Incident Commander of any relevant feedback from customers as the incident progresses.\n\nIt's important for the rest of the command staff to be able to focus on the problem at hand, rather than worrying about crafting messages to customers.\nYour job as Communications Liaison is to listen to the call, watch the incident Slack room, and track incoming customer support requests, keeping track of what's going on and how far the incident is progressing (still investigating vs close to resolution).\n\nThe Incident Commander will instruct you to notify customers of the incident and keep them updated at various points throughout the call. You will be required to craft the message, gain approval from the IC, and then disseminate that message to customers.\n\nMore information: https://response.pagerduty.com/training/customer_liaison/",
        },
    }
    root_slash_command: str = "/incidentbot"
    severities: dict[str, str] = {
        "sev1": "This signifies a critical production scenario that impacts most or all users with a major impact on SLAs. This is an all-hands-on-deck scenario that requires swift action to restore operation. Customers must be notified.",
        "sev2": "This signifies a significant production degradation scenario impacting a large portion of users.",
        "sev3": "This signifies a minor production scenario that may or may not result in degradation. This situation is worth coordination to resolve quickly but does not indicate a critical loss of service for users.",
        "sev4": "This signifies an ongoing investigation. This incident has not been promoted to SEV3 yet, indicating there may be little to no impact, but the situation warrants a closer look. This is diagnostic in nature. This is the default setting for a new incident.",
    }
    components: list[str] | None = ["Component1", "Component2", "Component3", "Component4"]
    statuses: dict[str, StatusDefinition] = {
        "investigating": {"initial": True},
        "identified": {},
        "monitoring": {},
        "resolved": {"final": True},
    }

    # ── Environment variable fields ───────────────────────────────────────────

    SECRET_KEY: str = secrets.token_urlsafe(32)

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

    PAGERDUTY_API_TOKEN: str | None = None
    PAGERDUTY_API_USERNAME: str | None = None

    SLACK_APP_TOKEN: str | None = None
    SLACK_BOT_TOKEN: str | None = None
    SLACK_USER_TOKEN: str | None = None

    MATRIX_HOMESERVER: str | None = None
    MATRIX_USER_ID: str | None = None
    MATRIX_ACCESS_TOKEN: str | None = None
    MATRIX_DEVICE_ID: str | None = None
    MATRIX_DIGEST_ROOM_ID: str | None = None
    MATRIX_WIDGET_BASE_URL: str | None = None

    PHARE_API_KEY: str | None = None
    PHARE_PROJECT_ID: int | None = None

    STATUSPAGE_API_KEY: str | None = None
    STATUSPAGE_PAGE_ID: str | None = None

    ZOOM_ACCOUNT_ID: str | None = None
    ZOOM_CLIENT_ID: str | None = None
    ZOOM_CLIENT_SECRET: str | None = None

    GITLAB_URL: str | None = None
    GITLAB_API_TOKEN: str | None = None

    API_KEY: str | None = None
    ENABLE_API_DOCS: bool = False

    IS_MIGRATION: bool | None = False
    IS_TEST_ENVIRONMENT: bool | None = False

    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
        yaml_file=os.getenv("CONFIG_FILE_PATH", "config.yaml"),
    )

    def _check_required_var(self, var_name: str, value: str | None) -> None:
        if not value:
            raise ValueError(f"The value of {var_name} cannot be empty.")

    def _check_required_integration_var(
        self, var_name: str, value: str | None, integration: str
    ) -> None:
        if not value:
            raise ValueError(
                f"The value of {var_name} cannot be empty when enabling the {integration} integration."
            )

    def _resolve_matrix_settings(self) -> MatrixSettings | None:
        matrix_env_values = {
            "homeserver": self.MATRIX_HOMESERVER,
            "user_id": self.MATRIX_USER_ID,
            "access_token": self.MATRIX_ACCESS_TOKEN,
            "device_id": self.MATRIX_DEVICE_ID,
            "digest_room_id": self.MATRIX_DIGEST_ROOM_ID,
            "widget_base_url": self.MATRIX_WIDGET_BASE_URL,
        }

        if not self.matrix and not any(matrix_env_values.values()):
            return None

        matrix_values = self.matrix.model_dump() if self.matrix else {}
        for key, value in matrix_env_values.items():
            if value is not None:
                matrix_values[key] = value

        return MatrixSettings(**matrix_values)

    @model_validator(mode="after")
    def _check_required_vars(self) -> Self:
        self._check_required_var("POSTGRES_DB", self.POSTGRES_DB)
        self._check_required_var("POSTGRES_HOST", self.POSTGRES_HOST)
        self._check_required_var("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)
        self._check_required_var("POSTGRES_PORT", str(self.POSTGRES_PORT))
        self._check_required_var("POSTGRES_USER", self.POSTGRES_USER)

        if self.platform == "matrix":
            self.matrix = self._resolve_matrix_settings()

        from pydantic import TypeAdapter

        skip_platform_check = TypeAdapter(bool).validate_python(
            self.IS_MIGRATION
        ) or TypeAdapter(bool).validate_python(self.IS_TEST_ENVIRONMENT)

        if not skip_platform_check:
            if self.platform == "slack":
                self._check_required_var("SLACK_APP_TOKEN", self.SLACK_APP_TOKEN)
                self._check_required_var("SLACK_BOT_TOKEN", self.SLACK_BOT_TOKEN)
                self._check_required_var("SLACK_USER_TOKEN", self.SLACK_USER_TOKEN)
            elif self.platform == "matrix":
                if not self.matrix:
                    raise ValueError(
                        "Matrix configuration is required when platform = 'matrix'."
                    )
                self._check_required_var("matrix.homeserver", self.matrix.homeserver)
                self._check_required_var("matrix.user_id", self.matrix.user_id)
                self._check_required_var(
                    "matrix.access_token", self.matrix.access_token
                )
                self._check_required_var(
                    "matrix.digest_room_id", self.matrix.digest_room_id
                )

            atlassian = self.integrations and self.integrations.atlassian

            if atlassian and atlassian.confluence and atlassian.confluence.enabled:
                self._check_required_integration_var(
                    "ATLASSIAN_API_URL", self.ATLASSIAN_API_URL, "Confluence"
                )
                self._check_required_integration_var(
                    "ATLASSIAN_API_USERNAME", self.ATLASSIAN_API_USERNAME, "Confluence"
                )
                self._check_required_integration_var(
                    "ATLASSIAN_API_TOKEN", self.ATLASSIAN_API_TOKEN, "Confluence"
                )

            if atlassian and atlassian.jira and atlassian.jira.enabled:
                self._check_required_integration_var(
                    "ATLASSIAN_API_URL", self.ATLASSIAN_API_URL, "Jira"
                )
                self._check_required_integration_var(
                    "ATLASSIAN_API_USERNAME", self.ATLASSIAN_API_USERNAME, "Jira"
                )
                self._check_required_integration_var(
                    "ATLASSIAN_API_TOKEN", self.ATLASSIAN_API_TOKEN, "Jira"
                )

            if atlassian and atlassian.statuspage and atlassian.statuspage.enabled:
                self._check_required_integration_var(
                    "STATUSPAGE_API_KEY", self.STATUSPAGE_API_KEY, "Statuspage"
                )
                self._check_required_integration_var(
                    "STATUSPAGE_PAGE_ID", self.STATUSPAGE_PAGE_ID, "Statuspage"
                )

            if (
                self.integrations
                and self.integrations.pagerduty
                and self.integrations.pagerduty.enabled
            ):
                self._check_required_integration_var(
                    "PAGERDUTY_API_USERNAME", self.PAGERDUTY_API_USERNAME, "PagerDuty"
                )
                self._check_required_integration_var(
                    "PAGERDUTY_API_TOKEN", self.PAGERDUTY_API_TOKEN, "PagerDuty"
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

            if (
                self.integrations
                and self.integrations.phare
                and self.integrations.phare.enabled
            ):
                self._check_required_integration_var(
                    "PHARE_API_KEY", self.PHARE_API_KEY, "Phare"
                )

        return self

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            env_settings,
            YamlConfigSettingsSource(settings_cls),
            dotenv_settings,
        )


settings = Settings()
