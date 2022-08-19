import config

from bot.models.setting import read_single_setting_value

"""
Parse Settings from Database
"""

settings_from_db = (
    read_single_setting_value("incident_management_configuration")
    if config.test_environment == "false"
    else {
        "incident_channel_topic": "test",
        "incident_guide_link": "https://test.com",
        "incident_postmortems_link": "https://test.com",
        "timezone": "UTC",
        "zoom_link": "https://test.com",
    }
)

incident_channel_topic = settings_from_db.get("incident_channel_topic", "unset")
incident_guide_link = settings_from_db.get("incident_guide_link", "unset")
incident_postmortems_link = settings_from_db.get("incident_postmortems_link", "unset")
timezone = settings_from_db.get("timezone", "UTC")
zoom_link = settings_from_db.get("zoom_link", "unset")
