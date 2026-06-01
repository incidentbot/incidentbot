"""
Tests for incidentbot/util/widget_token.py
"""
import pytest
from unittest.mock import MagicMock, patch

_mock_settings = MagicMock()
_mock_settings.SECRET_KEY = "test-secret-key-32-chars-minimum!"

with patch("incidentbot.configuration.settings.settings", _mock_settings):
    import incidentbot.util.widget_token as _mod
    from incidentbot.util.widget_token import (
        build_widget_url,
        generate_widget_token,
        verify_widget_token,
    )


class TestGenerateAndVerify:
    def test_round_trip(self):
        token = generate_widget_token("!room:example.com")
        payload = verify_widget_token(token)
        assert payload["room_id"] == "!room:example.com"
        assert payload["type"] == "widget"

    def test_returns_string(self):
        assert isinstance(generate_widget_token("!x:y"), str)

    def test_different_rooms_produce_different_tokens(self):
        t1 = generate_widget_token("!room1:example.com")
        t2 = generate_widget_token("!room2:example.com")
        assert t1 != t2


class TestVerifyWidgetToken:
    def test_raises_on_wrong_secret(self):
        import jwt

        token = generate_widget_token("!room:example.com")
        with patch.object(_mod, "settings") as s:
            s.SECRET_KEY = "completely-different-secret-key!"
            with pytest.raises(jwt.InvalidTokenError):
                verify_widget_token(token)

    def test_raises_on_wrong_type(self):
        import jwt

        bad = jwt.encode(
            {"type": "not_widget", "room_id": "!x:y"},
            "test-secret-key-32-chars-minimum!",
            algorithm="HS256",
        )
        with pytest.raises(jwt.InvalidTokenError):
            verify_widget_token(bad)

    def test_raises_on_garbage_token(self):
        import jwt

        with pytest.raises(jwt.InvalidTokenError):
            verify_widget_token("not.a.real.token")

    def test_raises_on_empty_token(self):
        import jwt

        with pytest.raises(jwt.InvalidTokenError):
            verify_widget_token("")


class TestBuildWidgetUrl:
    def test_contains_room_id(self):
        url = build_widget_url("https://bot.example.com", "/widget/incident", "!r:x", "w1")
        assert "roomId=!r:x" in url

    def test_contains_widget_id(self):
        url = build_widget_url("https://bot.example.com", "/widget/incident", "!r:x", "widget-99")
        assert "widgetId=widget-99" in url

    def test_strips_trailing_slash_from_base(self):
        url = build_widget_url("https://bot.example.com/", "/widget/incident", "!r:x", "w1")
        assert "https://bot.example.com/widget/incident" in url

    def test_contains_signed_token(self):
        url = build_widget_url("https://bot.example.com", "/widget/incident", "!r:x", "w1")
        assert "token=" in url

    def test_token_in_url_is_valid(self):
        url = build_widget_url("https://bot.example.com", "/widget/incident", "!r:x", "w1")
        token = url.split("token=")[-1]
        payload = verify_widget_token(token)
        assert payload["room_id"] == "!r:x"
