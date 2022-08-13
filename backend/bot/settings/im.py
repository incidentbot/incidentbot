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
        "zoom_link": "https://test.com",
    }
)

incident_channel_topic = settings_from_db["incident_channel_topic"]
incident_guide_link = settings_from_db["incident_guide_link"]
incident_postmortems_link = settings_from_db["incident_postmortems_link"]
zoom_link = settings_from_db["zoom_link"]
