import datetime
import logging

from __main__ import config
from ..shared import tools
from typing import Dict

logger = logging.getLogger(__name__)


class Incident:
    """Instantiates an incident"""

    def __init__(self, request_data: Dict[str, str]):
        self.d = request_data
        self.log()

    def log(self):
        request_log = {
            "user": self.d["user"],
            "channel": self.d["channel"],
            "descriptor": self.d["descriptor"],
        }
        logger.info(
            f"Request received from Slack to start a new incident: {request_log}"
        )

    def return_channel_name(self) -> str:
        # Replace any spaces with dashes
        descriptor = self.d["descriptor"].replace(" ", "-").lower()
        now = datetime.datetime.now()
        return f"inc-{now.year}{now.month}{now.day}{now.hour}{now.minute}-{descriptor}"


def build_digest_notification(createdChannelDetails: Dict[str, str]) -> Dict[str, str]:
    """Formats the notification that will be
    sent to the digest channel

    Args:
        createdChannelDetails: dict[str, str]
        Expects: id, name

    Returns dict[str, str] containing the formatted message
    to be sent to Slack
    """
    variables = {
        "channel_id_var_placeholder": config.incidents_digest_channel,
        "channel_name_var_placeholder": createdChannelDetails["name"],
        "slack_workspace_id_var_placeholder": config.slack_workspace_id,
        "incident_guide_link_var_placeholder": config.incident_guide_link,
        "incident_postmortems_link_var_placeholder": config.incident_postmortems_link,
    }
    return tools.render_json(
        f"{config.templates_directory}incident_digest_notification.json", variables
    )


def build_incident_channel_boilerplate(
    createdChannelDetails: Dict[str, str]
) -> Dict[str, str]:
    """Formats the boilerplate messaging that will
    be added to all newly created incident channels.
    """
    variables = {
        "channel_id_var_placeholder": createdChannelDetails["id"],
        "incident_guide_link_var_placeholder": config.incident_guide_link,
        "incident_postmortems_link_var_placeholder": config.incident_postmortems_link,
    }
    return tools.render_json(
        f"{config.templates_directory}incident_channel_boilerplate.json", variables
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
        "incident_guide_link_var_placeholder": config.incident_guide_link,
        "incident_postmortems_link_var_placeholder": config.incident_postmortems_link,
    }
    return tools.render_json(
        f"{config.templates_directory}incident_resolution_message.json", variables
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
    severity_descriptions = {
        "sev1": "This signifies a critical production scenario that impacts most or all users with a major impact to SLAs. This is an all hands on deck scenario that requires swift action to restore operation.",
        "sev2": "This signifies a major production degradation scenario impacting a large portion of users.",
        "sev3": "This signifies a minor production scenario that may or may not be resulting in degradation. This situation is worth coordination to resolve quickly, but does not indicate critical loss of service for users.",
        "sev4": "This signifies an ongoing investigation. This incident has not been promoted to SEV3 yet, indicating there may be little to no impact but the situation warrants a closer look. This is diagnostic in nature.",
    }
    variables = {
        "channel_id_var_placeholder": channel,
        "severity_var_placeholder": severity.upper(),
        "severity_description_var_placeholder": severity_descriptions[severity],
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


def build_topic() -> str:
    """Formats the boilerplate messaging that will
    be used as the incident channel topic
    """
    return config.incident_channel_topic


def build_updated_digest_message(
    incident_id: str, status: str, severity: str
) -> Dict[str, list]:
    """Returns the blocks required for the initial incidents
    digest message with edits so we can update it when the status
    changes
    """
    if status == "resolved":
        header = ":white_check_mark: Resolved Incident :white_check_mark:"
        message = "This incident has been resolved. You can still check out the archived channel for context."
    else:
        header = ":bangbang: Ongoing Incident :bangbang:"
        message = "This incident is in progress. Current status is listed here. Join the channel for more information."

    variables = {
        "header_var_placeholder": header,
        "incident_id_var_placeholder": incident_id,
        "status_var_placeholder": status.title(),
        "severity_var_placeholder": severity.upper(),
        "message_var_placeholder": message,
        "slack_workspace_id_var_placeholder": config.slack_workspace_id,
        "incident_guide_link_var_placeholder": config.incident_guide_link,
        "incident_postmortems_link_var_placeholder": config.incident_postmortems_link,
    }
    return tools.render_json(
        f"{config.templates_directory}incident_digest_notification_update.json",
        variables,
    )


def build_user_role_notification(
    channel_id: str, role: str, user: str
) -> Dict[str, str]:
    """Returns the blocks required for messaging a user w/r/t
    details about their role when they are assigned a role
    during an incident
    """
    role_descriptions = {
        "incident_commander": "The Incident Commander is the decision maker during a major incident, delegating tasks and listening to input from subject matter experts in order to bring the incident to resolution. They become the highest ranking individual on any major incident call, regardless of their day-to-day rank. Their decisions made as commander are final.\\n\\nYour job as an Incident Commander is to listen to the call and to watch the incident Slack room in order to provide clear coordination, recruiting others to gather context and details. You should not be performing any actions or remediations, checking graphs, or investigating logs. Those tasks should be delegated.\\n\\nAn IC should also be considering next steps and backup plans at every opportunity, in an effort to avoid getting stuck without any clear options to proceed and to keep things moving towards resolution.\\n\\nMore information: https://response.pagerduty.com/training/incident_commander/",
        "communications_liaison": "The purpose of the Communications Liaison is to be the primary individual in charge of notifying our customers of the current conditions, and informing the Incident Commander of any relevant feedback from customers as the incident progresses.\\n\\nIt's important for the rest of the command staff to be able to focus on the problem at hand, rather than worrying about crafting messages to customers.\\n\\nYour job as Communications Liaison is to listen to the call, watch the incident Slack room, and track incoming customer support requests, keeping track of what's going on and how far the incident is progressing (still investigating vs close to resolution).\\n\\nThe Incident Commander will instruct you to notify customers of the incident and keep them updated at various points throughout the call. You will be required to craft the message, gain approval from the IC, and then disseminate that message to customers.\\n\\nMore information: https://response.pagerduty.com/training/customer_liaison/",
        "technical_lead": "The Technical Lead drives technical discovery of an incident throughout the process and will be called on by the Incident Commander to assist with figuring out what has happened, how to fix it, and who to call on as Subject Matter Experts.",
    }
    variables = {
        "channel_name_var_placeholder": channel_id,
        "role_description_var_placeholder": role_descriptions[role],
        "role_var_placeholder": role.replace("_", " ").title(),
        "user_var_placeholder": user,
    }
    return tools.render_json(
        f"{config.templates_directory}incident_user_role_dm.json", variables
    )
