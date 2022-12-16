import config
import logging


from bot.models.setting import read_single_setting_value
from bot.settings.im import (
    incident_guide_link,
    incident_postmortems_link,
)
from bot.shared import tools
from bot.slack.client import slack_workspace_id
from typing import Any, Dict

logger = logging.getLogger(__name__)


def build_digest_notification(
    created_channel_details: Dict[str, Any],
    severity: str,
    conference_bridge: str,
) -> Dict[str, str]:
    """Formats the notification that will be
    sent to the digest channel

    Returns dict[str, str] containing the formatted message
    to be sent to Slack
    """
    if created_channel_details["is_security_incident"]:
        header = ":fire::lock::fire_engine: New Security Incident"
    else:
        header = ":fire::fire_engine: New Incident"
    variables = {
        "header_var_placeholder": header,
        "channel_description_var_placeholder": created_channel_details[
            "incident_description"
        ],
        "channel_id_var_placeholder": config.incidents_digest_channel,
        "channel_name_var_placeholder": created_channel_details["name"],
        "slack_workspace_id_var_placeholder": slack_workspace_id,
        "severity_var_placeholder": severity.upper(),
        "incident_guide_link_var_placeholder": incident_guide_link,
        "incident_postmortems_link_var_placeholder": incident_postmortems_link,
        "conference_bridge_link_var_placeholder": conference_bridge,
    }
    return tools.render_json(
        f"{config.templates_directory}incident_digest_notification.json",
        variables,
    )


def build_incident_channel_boilerplate(
    created_channel_details: Dict[str, Any], severity: str
) -> Dict[str, str]:
    """Formats the boilerplate messaging that will
    be added to all newly created incident channels.
    """
    variables = {
        "channel_id_var_placeholder": created_channel_details["id"],
        "severity_var_placeholder": severity.upper(),
        "incident_guide_link_var_placeholder": incident_guide_link,
        "incident_postmortems_link_var_placeholder": incident_postmortems_link,
    }
    return tools.render_json(
        f"{config.templates_directory}incident_channel_boilerplate.json",
        variables,
    )


def build_post_resolution_message(channel: str, status: str) -> Dict[str, str]:
    """Formats the notification that will be
    sent when the incident is resolved

    Args:
        channel: str
        status: str

    Returns dict[str, str] containing the formatted message
    to be sent to Slack
    """
    variables = {
        "channel_id_var_placeholder": channel,
        "incident_guide_link_var_placeholder": incident_guide_link,
        "incident_postmortems_link_var_placeholder": incident_postmortems_link,
    }
    return tools.render_json(
        f"{config.templates_directory}incident_resolution_message.json",
        variables,
    )


def build_public_status_update(
    incident_id: str,
    impacted_resources: str,
    message: str,
    timestamp: str = tools.fetch_timestamp(),
):
    """Returns the blocks required for a public status update for a
    given incident
    """
    header = ":warning: Incident Update"

    variables = {
        "header_var_placeholder": header,
        "timestamp_var_placeholder": timestamp,
        "incident_id_var_placeholder": incident_id,
        "impacted_resources_var_placeholder": impacted_resources,
        "message_var_placeholder": message,
    }
    return tools.render_json(
        f"{config.templates_directory}incident_public_status_update.json",
        variables,
    )


def build_role_update(channel: str, role: str, user: str) -> Dict[str, str]:
    """Formats the notification that will be
    sent when a role is claimed

    Args:
        channel: str
        role: str
        user: str

    Returns dict[str, str] containing the formatted message
    to be sent to Slack
    """
    variables = {
        "channel_id_var_placeholder": channel,
        "user_var_placeholder": user,
        "role_var_placeholder": role,
    }
    return tools.render_json(
        f"{config.templates_directory}incident_role_update.json", variables
    )


def build_severity_update(channel: str, severity: str) -> Dict[str, str]:
    """Formats the notification that will be
    sent when severity changes

    Args:
        channel: str
        severity: str

    Returns dict[str, str] containing the formatted message
    to be sent to Slack
    """
    severity_descriptions = read_single_setting_value("severity_levels")
    variables = {
        "channel_id_var_placeholder": channel,
        "severity_var_placeholder": severity.upper(),
        "severity_description_var_placeholder": severity_descriptions[
            severity
        ],
    }
    return tools.render_json(
        f"{config.templates_directory}incident_severity_update.json", variables
    )


def build_status_update(channel: str, status: str) -> Dict[str, str]:
    """Formats the notification that will be
    sent when status changes

    Args:
        channel: str
        status: str

    Returns dict[str, str] containing the formatted message
    to be sent to Slack
    """
    variables = {
        "channel_id_var_placeholder": channel,
        "status_var_placeholder": status.title(),
    }
    return tools.render_json(
        f"{config.templates_directory}incident_status_update.json", variables
    )


def build_updated_digest_message(
    incident_id: str,
    incident_description: str,
    status: str,
    severity: str,
    is_security_incident: bool,
    conference_bridge: str,
) -> Dict[str, list]:
    """Returns the blocks required for the initial incidents
    digest message with edits so we can update it when the status
    changes
    """
    incident_reacji_header = (
        ":fire::lock::fire_engine:"
        if is_security_incident
        else ":fire::fire_engine:"
    )
    incident_type = "Security Incident" if is_security_incident else "Incident"
    if status == "resolved":
        header = (
            f":white_check_mark: Resolved {incident_type} :white_check_mark:"
        )
        message = "This incident has been resolved. You can still check out the channel for context."
    else:
        header = f"{incident_reacji_header} Ongoing {incident_type}"
        message = "This incident is in progress. Current status is listed here. Join the channel for more information."
    variables = {
        "header_var_placeholder": header,
        "incident_description_var_placeholder": incident_description,
        "incident_id_var_placeholder": incident_id,
        "status_var_placeholder": status.title(),
        "severity_var_placeholder": severity.upper(),
        "message_var_placeholder": message,
        "slack_workspace_id_var_placeholder": slack_workspace_id,
        "incident_guide_link_var_placeholder": incident_guide_link,
        "incident_postmortems_link_var_placeholder": incident_postmortems_link,
        "conference_bridge_link_var_placeholder": conference_bridge,
    }
    return tools.render_json(
        f"{config.templates_directory}incident_digest_notification_update.json",
        variables,
    )


def build_user_role_notification(channel_id: str, role: str, user: str):
    """Returns the blocks required for messaging a user w/r/t
    details about their role when they are assigned a role
    during an incident
    """
    role_descriptions = read_single_setting_value("role_definitions")
    variables = {
        "channel_name_var_placeholder": channel_id,
        "role_description_var_placeholder": role_descriptions[role],
        "role_var_placeholder": role.replace("_", " ").title(),
        "user_var_placeholder": user,
    }
    return tools.render_json(
        f"{config.templates_directory}incident_user_role_dm.json", variables
    )
