import datetime

from incidentbot.util import gen


class TestUtils:
    def test_fetch_timestamp(self):
        ny_ts = gen.fetch_timestamp(tz="America/New_York")
        ch_ts = gen.fetch_timestamp(tz="Europe/Copenhagen")
        utc_ts = gen.fetch_timestamp(tz="UTC")

        parsed_ny = datetime.datetime.strptime(ny_ts, gen.timestamp_fmt)
        parsed_ch = datetime.datetime.strptime(ch_ts, gen.timestamp_fmt)
        parsed_utc = datetime.datetime.strptime(utc_ts, gen.timestamp_fmt)

        assert (
            parsed_ny.hour != parsed_utc.hour
        ), "Fetched timestamps should be timezone aware"

        assert (
            parsed_ch.hour != parsed_utc.hour
        ), "Fetched timestamps should be timezone aware"

        assert parsed_ny.astimezone()

    def test_find_index_in_list(self):
        index = gen.find_index_in_list(
            [
                {
                    "token": "verification-token",
                    "team_id": "T111",
                    "enterprise_id": "E111",
                    "api_app_id": "A111",
                    "event": {
                        "type": "message",
                        "subtype": "bot_message",
                        "text": "TEST 1",
                        "ts": "1610262363.001600",
                        "username": "classic-bot",
                        "bot_id": "B888",
                        "channel": "C111",
                        "event_ts": "1610262363.001600",
                        "channel_type": "channel",
                    },
                    "type": "event_callback",
                    "event_id": "Ev111",
                    "event_time": 1610262363,
                    "authorizations": [
                        {
                            "enterprise_id": "E111",
                            "team_id": "T111",
                            "user_id": "UB222",
                            "is_bot": True,
                            "is_enterprise_install": False,
                        }
                    ],
                    "is_ext_shared_channel": False,
                    "event_context": "1-message-T111-C111",
                },
                {
                    "token": "verification-token",
                    "team_id": "T111",
                    "enterprise_id": "E111",
                    "api_app_id": "A111",
                    "event": {
                        "type": "message",
                        "subtype": "bot_message",
                        "text": "TEST 2",
                        "ts": "1610262363.001600",
                        "username": "classic-bot",
                        "bot_id": "B888",
                        "channel": "C111",
                        "event_ts": "1610262363.001600",
                        "channel_type": "channel",
                    },
                    "type": "event_callback",
                    "event_id": "Ev222",
                    "event_time": 1610262363,
                    "authorizations": [
                        {
                            "enterprise_id": "E111",
                            "team_id": "T111",
                            "user_id": "UB222",
                            "is_bot": True,
                            "is_enterprise_install": False,
                        }
                    ],
                    "is_ext_shared_channel": False,
                    "event_context": "1-message-T111-C111",
                },
            ],
            "event_id",
            "Ev222",
        )

        assert index == 1, "find_index_in_list should return the correct index"
