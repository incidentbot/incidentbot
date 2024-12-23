import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
from incidentbot.incident.core import format_channel_name

class TestFormatChannelName(unittest.TestCase):
    def setUp(self):
        # Mock settings
        self.settings_mock = MagicMock()
        self.settings_mock.options.channel_name_prefix = "incident"
        self.settings_mock.options.channel_name_date_format = "YYYY-MM-DD"

    @patch("incidentbot.incident.core.settings", create=True)
    @patch("incidentbot.incident.core.datetime")
    def test_format_channel_name_without_date_prefix(
        self, mock_datetime, mock_settings
    ):
        mock_settings.options = self.settings_mock.options
        mock_datetime.now.return_value = datetime(2024, 12, 25)
        result = format_channel_name(1, "Test Description")
        self.assertEqual(result, "incident-1-test-description")

    @patch("incidentbot.incident.core.settings", create=True)
    @patch("incidentbot.incident.core.datetime")
    def test_format_channel_name_with_date_prefix(
        self, mock_datetime, mock_settings
    ):
        mock_settings.options = self.settings_mock.options
        mock_datetime.now.return_value = datetime(2024, 12, 25)
        result = format_channel_name(1, "Test Description", useDatePrefix=True)
        self.assertEqual(result, "incident-1-2024-12-25-test-description")

    @patch("incidentbot.incident.core.settings", create=True)
    @patch("incidentbot.incident.core.datetime")
    def test_format_channel_name_with_comms_suffix(
        self, mock_datetime, mock_settings
    ):
        mock_settings.options = self.settings_mock.options
        mock_datetime.now.return_value = datetime(2024, 12, 25)
        result = format_channel_name(1, "Test Description", comms=True)
        self.assertEqual(result, "incident-1-test-description-comms")

    @patch("incidentbot.incident.core.settings", create=True)
    @patch("incidentbot.incident.core.datetime")
    def test_format_channel_name_with_date_and_comms(
        self, mock_datetime, mock_settings
    ):
        mock_settings.options = self.settings_mock.options
        mock_datetime.now.return_value = datetime(2024, 12, 25)
        result = format_channel_name(
            1, "Test Description", useDatePrefix=True, comms=True)
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
