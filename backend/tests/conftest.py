import pytest

from bot.models.pg import Base


@pytest.fixture(scope="function")
def sqlalchemy_declarative_base():
    return Base


@pytest.fixture(scope="function")
def sqlalchemy_mock_config():
    return [
        (
            "auditlog",
            [
                {
                    "incident_id": "inc-mock-test",
                    "data": [
                        {
                            "log": "Incident created.",
                            "user": "Scott",
                            "content": "",
                            "ts": "2022-12-09T16:54:50 UTC",
                        }
                    ],
                }
            ],
        ),
        (
            "application_settings",
            [
                {
                    "name": "mock",
                    "value": {"foo": "bar"},
                    "description": "mock",
                    "deletable": True,
                }
            ],
        ),
        (
            "incident_logging",
            [
                {
                    "id": 1,
                    "incident_id": "inc-mock-test",
                    "title": "mock",
                    "content": "some messaged that was pinned",
                    "img": b"",
                    "ts": "time",
                    "user": "mock_user",
                },
                {
                    "id": 2,
                    "incident_id": "inc-mock-test",
                    "title": "mock",
                    "content": "some messaged that was pinned",
                    "img": b"something",
                    "ts": "time",
                    "user": "mock_user",
                },
            ],
        ),
    ]
