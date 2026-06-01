"""
Tests for _slack_call_with_retry in incidentbot/slack/client.py
"""
from unittest.mock import call, MagicMock, patch

_mock_settings = MagicMock()
_mock_settings.SLACK_BOT_TOKEN = "xoxb-test"
_mock_settings.IS_TEST_ENVIRONMENT = True
_mock_settings.LOG_LEVEL = "INFO"
_mock_settings.DATABASE_URI = "sqlite:///:memory:"

with (
    patch("incidentbot.configuration.settings.settings", _mock_settings),
    patch("sqlmodel.create_engine", return_value=MagicMock()),
    patch("slack_sdk.WebClient", return_value=MagicMock()),
):
    from incidentbot.slack.client import _slack_call_with_retry
    from slack_sdk.errors import SlackApiError


def _rate_limit_error(retry_after: int = 2) -> SlackApiError:
    resp = MagicMock()
    resp.status_code = 429
    resp.headers = {"Retry-After": str(retry_after)}
    return SlackApiError("rate limited", resp)


def _api_error(status_code: int = 500) -> SlackApiError:
    resp = MagicMock()
    resp.status_code = status_code
    return SlackApiError("server error", resp)


class TestSlackCallWithRetry:
    def test_returns_result_on_success(self):
        fn = MagicMock(return_value="ok")
        result = _slack_call_with_retry(fn, "arg1", key="val")
        assert result == "ok"
        fn.assert_called_once_with("arg1", key="val")

    def test_retries_once_on_429(self):
        fn = MagicMock(side_effect=[_rate_limit_error(1), "retried"])
        with patch("incidentbot.slack.client.time.sleep") as mock_sleep:
            result = _slack_call_with_retry(fn, "x")
        assert result == "retried"
        assert fn.call_count == 2
        mock_sleep.assert_called_once_with(1)

    def test_sleeps_for_retry_after_duration(self):
        fn = MagicMock(side_effect=[_rate_limit_error(retry_after=30), "ok"])
        with patch("incidentbot.slack.client.time.sleep") as mock_sleep:
            _slack_call_with_retry(fn)
        mock_sleep.assert_called_once_with(30)

    def test_defaults_to_five_second_sleep_when_header_missing(self):
        resp = MagicMock()
        resp.status_code = 429
        resp.headers = {}
        error = SlackApiError("rate limited", resp)
        fn = MagicMock(side_effect=[error, "ok"])
        with patch("incidentbot.slack.client.time.sleep") as mock_sleep:
            _slack_call_with_retry(fn)
        mock_sleep.assert_called_once_with(5)

    def test_reraises_non_429_slack_error(self):
        import pytest

        fn = MagicMock(side_effect=_api_error(500))
        with pytest.raises(SlackApiError):
            _slack_call_with_retry(fn)

    def test_passes_args_and_kwargs_on_retry(self):
        fn = MagicMock(side_effect=[_rate_limit_error(1), "ok"])
        with patch("incidentbot.slack.client.time.sleep"):
            _slack_call_with_retry(fn, "a", "b", k="v")
        assert fn.call_args_list == [call("a", "b", k="v"), call("a", "b", k="v")]
