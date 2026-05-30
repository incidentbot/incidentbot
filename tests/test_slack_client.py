import importlib
from unittest.mock import MagicMock, patch

mock_web_client = MagicMock()
mock_web_client.auth_test.return_value = {
    "ok": True,
    "url": "https://testworkspace.slack.com",
    "team": "test team",
    "user": "test user",
    "team_id": "test team id",
    "user_id": "test user id",
}

mock_options = MagicMock()
mock_options.include_private_channels = False

with patch("slack_sdk.WebClient", return_value=mock_web_client), patch(
    "incidentbot.configuration.settings.settings"
) as mock_settings, patch("sqlmodel.create_engine"), patch(
    "apscheduler.schedulers.background.BackgroundScheduler"
):
    mock_settings.IS_TEST_ENVIRONMENT = True
    mock_settings.SLACK_BOT_TOKEN = "test-token"
    mock_settings.LOG_LEVEL = "INFO"
    mock_settings.LOG_TYPE = None
    mock_settings.DATABASE_URI = "sqlite:///:memory:"
    mock_settings.options = mock_options

    slack_client = importlib.import_module("incidentbot.slack.client")
    slack_client = importlib.reload(slack_client)
    slack_client.slack_web_client = mock_web_client


def _set_channel_list_response():
    mock_web_client.conversations_list.reset_mock()
    mock_web_client.conversations_list.return_value = {
        "channels": [],
        "response_metadata": {"next_cursor": ""},
    }


def test_get_channel_list_defaults_to_public_channel():
    _set_channel_list_response()
    mock_options.include_private_channels = False

    slack_client.get_channel_list()

    assert mock_web_client.conversations_list.called
    assert (
        mock_web_client.conversations_list.call_args.kwargs["types"]
        == "public_channel"
    )


def test_get_channel_list_can_include_private_channels():
    _set_channel_list_response()
    mock_options.include_private_channels = True

    slack_client.get_channel_list()

    assert mock_web_client.conversations_list.called
    assert (
        mock_web_client.conversations_list.call_args.kwargs["types"]
        == "public_channel,private_channel"
    )
