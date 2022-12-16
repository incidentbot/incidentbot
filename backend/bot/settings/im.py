import config

from bot.models.setting import read_single_setting_value
from bot.slack.client import slack_workspace_id

"""
Parse Settings from Database
"""
defaults = {
    "incident_channel_topic": "This is the default incident channel topic. You can edit it in settings.",
    "incident_guide_link": "https://changeme.com",
    "incident_postmortems_link": "https://changeme.com",
    "slack_workspace_id": slack_workspace_id
    if not config.is_test_environment
    else "test",
    "timezone": "UTC",
    "conference_bridge_link": "https://zoom.us",
}

settings_from_db = (
    read_single_setting_value("incident_management_configuration")
    if not config.is_test_environment
    else defaults
)

incident_channel_topic = settings_from_db.get(
    "incident_channel_topic", defaults["incident_channel_topic"]
)
incident_guide_link = settings_from_db.get(
    "incident_guide_link", defaults["incident_guide_link"]
)
incident_postmortems_link = settings_from_db.get(
    "incident_postmortems_link", defaults["incident_postmortems_link"]
)
timezone = settings_from_db.get("timezone", defaults["timezone"])

conference_bridge_link = settings_from_db.get(
    "conference_bridge_link", defaults["conference_bridge_link"]
)
