import importlib
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


def load_module(
    module_path: str,
    *,
    options: SimpleNamespace | None = None,
    statuses: dict | None = None,
    icons: dict | None = None,
    integrations: object | None = None,
    links: list | None = None,
):
    """
    Import a module with external runtime dependencies mocked.
    """

    mock_client = MagicMock()
    mock_client.auth_test.return_value = {
        "ok": True,
        "url": "https://testworkspace.slack.com",
        "team": "test team",
        "user": "test user",
        "team_id": "test team id",
        "user_id": "test user id",
    }

    mock_options = options or SimpleNamespace(
        timezone="UTC",
        channel_name_prefix="incident",
        channel_name_date_format="YYYY-MM-DD",
        channel_name_use_date_prefix=False,
        meeting_link=None,
    )

    default_statuses = statuses or {
        "investigating": SimpleNamespace(final=False, initial=True),
        "resolved": SimpleNamespace(final=True, initial=False),
    }
    default_icons = icons or {"slack": {"postmortem": ":book:"}}

    with (
        patch("slack_sdk.WebClient", return_value=mock_client),
        patch("incidentbot.configuration.settings.settings") as mock_settings,
        patch("sqlmodel.create_engine"),
        patch("apscheduler.schedulers.background.BackgroundScheduler"),
    ):
        mock_settings.IS_TEST_ENVIRONMENT = True
        mock_settings.SLACK_BOT_TOKEN = "test-token"
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.LOG_TYPE = None
        mock_settings.DATABASE_URI = "sqlite:///:memory:"
        mock_settings.options = mock_options
        mock_settings.statuses = default_statuses
        mock_settings.icons = default_icons
        mock_settings.integrations = integrations
        mock_settings.links = links
        mock_settings.platform = "slack"
        mock_settings.digest_channel = "incidents"
        mock_settings.root_slash_command = "/incidentbot"
        mock_settings.pin_content_reacji = "pushpin"
        mock_settings.enable_pinned_images = True

        import sys as _sys
        # Snapshot sys.modules before importing so we can undo side-effects.
        _before = set(_sys.modules.keys())
        _original = _sys.modules.pop(module_path, None)
        module = importlib.import_module(module_path)
        result = importlib.reload(module)
        _after = set(_sys.modules.keys())

    # Remove every module that was pulled in during this load so that other
    # test files get clean, uncontaminated copies on their own imports.
    import sys as _sys
    for _key in _after - _before:
        _sys.modules.pop(_key, None)
    # If the target module was already imported before this load, put the
    # original back so string-based patch() targets in other test files keep
    # resolving to the module object they imported from.
    if _original is not None:
        _sys.modules[module_path] = _original
    return result
