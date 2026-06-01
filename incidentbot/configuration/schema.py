"""
Config schema models — Pydantic BaseModel classes that define the shape of
config.yaml. Imported by settings.py to build the root Settings class.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Self


# ── Jobs ──────────────────────────────────────────────────────────────────────


class ScrapeForAgingIncidentsJob(BaseModel):
    enabled: bool = True
    interval_days: int = 2
    max_age_days: int = 7
    ignore_statuses: list[str] = []


class SlackCacheJob(BaseModel):
    enabled: bool = True
    interval_minutes: int = 15


class PagerDutyOCJob(BaseModel):
    enabled: bool = True
    interval_minutes: int = 30


class Jobs(BaseModel):
    scrape_for_aging_incidents: ScrapeForAgingIncidentsJob = Field(
        default_factory=ScrapeForAgingIncidentsJob
    )
    update_slack_cache: SlackCacheJob = Field(default_factory=SlackCacheJob)
    update_pagerduty_oc_data: PagerDutyOCJob = Field(default_factory=PagerDutyOCJob)


# ── Reminders ─────────────────────────────────────────────────────────────────


class Conditions(BaseModel):
    """Conditions that must all be true for a reminder or automation to fire."""
    no_roles_claimed: bool = False
    severity_is: list[str] | None = None
    status_is: list[str] | None = None
    status_is_final: bool = False


class ReminderAction(BaseModel):
    type: Literal["send_update", "snooze", "dismiss"]
    label: str | None = None
    intervals: list[int] | None = None  # minutes, for snooze only


class Reminder(BaseModel):
    id: str
    message: str
    interval_minutes: int
    once: bool = False
    conditions: Conditions | None = None
    include_role_buttons: bool = False
    actions: list[ReminderAction] = []
    enabled: bool = True

    @field_validator("id")
    @classmethod
    def _id_no_dots(cls, v: str) -> str:
        if "." in v:
            raise ValueError("reminder id must not contain dots (used in action_id routing)")
        return v


# ── Automations ───────────────────────────────────────────────────────────────


class AutomationAction(BaseModel):
    type: Literal["invite_group", "page_pagerduty", "post_message"]
    name: str | None = None            # invite_group: group name
    escalation_policy: str | None = None  # page_pagerduty: policy ID
    priority: Literal["low", "high"] = "low"
    message: str | None = None         # post_message: text


class Automation(BaseModel):
    id: str
    trigger: Literal["on_open", "on_severity_change", "on_status_change", "on_final_status"]
    conditions: Conditions | None = None
    actions: list[AutomationAction] = []
    enabled: bool = True


# ── Options ───────────────────────────────────────────────────────────────────


class AdditionalWelcomeMessage(BaseModel):
    message: str
    pin: bool | None = False


class Options(BaseModel):
    additional_welcome_messages: list[AdditionalWelcomeMessage] | None = None
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


# ── Integrations ──────────────────────────────────────────────────────────────


class ConfluenceIntegration(BaseModel):
    auto_create_postmortem: bool | None = False
    enabled: bool = False
    parent: str
    space: str
    template_id: int


class JiraIntegration(BaseModel):
    auto_create_issue: bool = False
    auto_create_issue_type: str | None = None
    enabled: bool = False
    issue_types: list[str]
    labels: list[str] | None = None
    priorities: list[str] | None = None
    project: str
    status_mapping: list[dict[str, str]]


class GitlabIntegration(BaseModel):
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
    groups: list[str] | None = None


class StatuspageIntegration(BaseModel):
    enabled: bool = False
    permissions: StatuspageIntegrationPermissions | None = None
    url: str


class AtlassianIntegration(BaseModel):
    confluence: ConfluenceIntegration | None = None
    jira: JiraIntegration | None = None
    statuspage: StatuspageIntegration | None = None


class PhareIntegrationPermissions(BaseModel):
    groups: list[str] | None = None


class PhareIntegration(BaseModel):
    enabled: bool = False
    permissions: PhareIntegrationPermissions | None = None


class PagerDutyIntegration(BaseModel):
    enabled: bool = False


class ZoomIntegration(BaseModel):
    auto_creating_meeting: bool
    enabled: bool = False


class Integrations(BaseModel):
    atlassian: AtlassianIntegration | None = None
    pagerduty: PagerDutyIntegration | None = None
    phare: PhareIntegration | None = None
    zoom: ZoomIntegration | None = None
    gitlab: GitlabIntegration | None = None


# ── Platform ──────────────────────────────────────────────────────────────────


class MatrixSettings(BaseModel):
    homeserver: str
    user_id: str
    access_token: str
    device_id: str = "INCIDENTBOT"
    digest_room_id: str
    widget_base_url: str | None = None


# ── Root-level config objects ─────────────────────────────────────────────────


class Link(BaseModel):
    title: str
    url: str


class RoleDefinition(BaseModel):
    description: str
    is_lead: bool | None = False


class StatusDefinition(BaseModel):
    initial: bool | None = False
    final: bool | None = False
