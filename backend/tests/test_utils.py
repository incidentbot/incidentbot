import datetime

from bot.utils import utils


class TestUtils:
    def test_fetch_timestamp(self):
        ny_ts = utils.fetch_timestamp(tz="America/New_York")
        ch_ts = utils.fetch_timestamp(tz="Europe/Copenhagen")
        utc_ts = utils.fetch_timestamp(tz="UTC")

        parsed_ny = datetime.datetime.strptime(ny_ts, utils.timestamp_fmt)
        parsed_ch = datetime.datetime.strptime(ch_ts, utils.timestamp_fmt)
        parsed_utc = datetime.datetime.strptime(utc_ts, utils.timestamp_fmt)

        assert (
            parsed_ny.hour != parsed_utc.hour
        ), "Fetched timestamps should be timezone aware"

        assert (
            parsed_ch.hour != parsed_utc.hour
        ), "Fetched timestamps should be timezone aware"

        assert parsed_ny.astimezone()

    def test_fetch_timestamp_short(self):
        ts = utils.fetch_timestamp(short=True, tz="UTC")

        assert datetime.datetime.strptime(
            ts, utils.timestamp_fmt_short
        ), "Shortened timestamp format should parse properly"

    def test_fetch_timestamp_from_time_obj(self):
        now = datetime.datetime.now(datetime.UTC)
        now_as_ny = utils.fetch_timestamp_from_time_obj(
            now, tz="America/New_York"
        )
        now_as_ny_datetime = datetime.datetime.strptime(
            now_as_ny, utils.timestamp_fmt
        )

        assert (
            now_as_ny_datetime.hour != now.hour
        ), "Fetched timestamps from datetime objects should be timezone aware"

    def test_find_index_in_list(self):
        index = utils.find_index_in_list(
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

    def test_validate_ip_address(self):
        is_ip = utils.validate_ip_address("127.0.0.1")

        assert (
            is_ip
        ), "validate_ip_address should return True for valid ip addresses"

        is_ip = utils.validate_ip_address("300.0.0.2")

        assert (
            not is_ip
        ), "validate_ip_address should return False for invalid ip addresses"

    def test_validate_ip_in_subnet(self):
        is_in_subnet = utils.validate_ip_in_subnet(
            "192.168.10.30", "192.168.10.0/24"
        )
        assert (
            is_in_subnet
        ), "validate_ip_in_subnet should return True if an IP address is valid within a subnet"
