import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

# Mock the entire slack client module and settings before importing core
mock_client = MagicMock()
mock_client.auth_test.return_value = {
    "ok": True,
    "url": "https://testworkspace.slack.com",
    "team": "test team",
    "user": "test user",
    "team_id": "test team id",
    "user_id": "test user id",
}

# Create mock options
mock_options = MagicMock()
mock_options.timezone = "UTC"

with patch("slack_sdk.WebClient", return_value=mock_client), patch(
    "incidentbot.configuration.settings.settings"
) as mock_settings, patch(
    "sqlmodel.create_engine"
) as mock_create_engine, patch(
    "apscheduler.schedulers.background.BackgroundScheduler"
) as mock_scheduler:
    # Mock settings before importing
    mock_settings.IS_TEST_ENVIRONMENT = True
    mock_settings.SLACK_BOT_TOKEN = "test-token"
    mock_settings.LOG_LEVEL = "INFO"
    mock_settings.LOG_TYPE = None
    mock_settings.DATABASE_URI = "sqlite:///:memory:"
    mock_settings.options = mock_options

    # Mock database engine
    mock_engine = MagicMock()
    mock_create_engine.return_value = mock_engine

    # Mock scheduler
    mock_scheduler_instance = MagicMock()
    mock_scheduler.return_value = mock_scheduler_instance

    from incidentbot.incident.core import format_channel_name


class TestFormatChannelName(unittest.TestCase):
    def setUp(self):
        # Mock settings
        self.settings_mock = MagicMock()
        self.settings_mock.options.channel_name_prefix = "incident"
        self.settings_mock.options.channel_name_date_format = "YYYY-MM-DD"

        # Create a patcher for settings that will be used in all tests
        self.settings_patcher = patch(
            "incidentbot.incident.core.settings", create=True
        )
        self.mock_settings = self.settings_patcher.start()
        self.mock_settings.options = self.settings_mock.options

    def tearDown(self):
        self.settings_patcher.stop()

    @patch("incidentbot.incident.core.datetime")
    def test_format_channel_name_without_date_prefix(self, mock_datetime):
        mock_datetime.now.return_value = datetime(2024, 12, 25)
        result = format_channel_name(1, "Test Description")
        self.assertEqual(result, "incident-1-test-description")

    @patch("incidentbot.incident.core.datetime")
    def test_format_channel_name_with_date_prefix(self, mock_datetime):
        mock_datetime.now.return_value = datetime(2024, 12, 25)
        result = format_channel_name(
            1, "Test Description", use_date_prefix=True
        )
        self.assertEqual(result, "incident-1-2024-12-25-test-description")

    @patch("incidentbot.incident.core.datetime")
    def test_format_channel_name_with_comms_suffix(self, mock_datetime):
        mock_datetime.now.return_value = datetime(2024, 12, 25)
        result = format_channel_name(1, "Test Description", comms=True)
        self.assertEqual(result, "incident-1-test-description-comms")

    @patch("incidentbot.incident.core.datetime")
    def test_format_channel_name_with_date_and_comms(self, mock_datetime):
        mock_datetime.now.return_value = datetime(2024, 12, 25)
        result = format_channel_name(
            1, "Test Description", use_date_prefix=True, comms=True
        )
        self.assertEqual(
            result, "incident-1-2024-12-25-test-description-comms"
        )

    def test_format_channel_name_special_characters(self):
        result = format_channel_name(1, "Test@Description!#")
        self.assertEqual(result, "incident-1-testdescription")

    def test_format_channel_name_spaces(self):
        result = format_channel_name(1, "Test Description With Spaces")
        self.assertEqual(result, "incident-1-test-description-with-spaces")


if __name__ == "__main__":
    unittest.main()
