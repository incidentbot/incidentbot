import config
import ipaddress
import itertools
import random
import string

from datetime import datetime
from logger import logger
from typing import Any, List
from zoneinfo import ZoneInfo

random_suffix = "".join(
    random.choices(string.ascii_lowercase + string.digits, k=6)
)
configured_timezone = config.active.options.get("timezone")
timestamp_fmt = "%Y-%m-%dT%H:%M:%S"
timestamp_fmt_short = "%d/%m/%Y %H:%M:%S"


def fetch_timestamp(short: bool = False, tz: str | None = None):
    """Return a localized, formatted timestamp using datetime.now()"""
    now = datetime.now(ZoneInfo(tz or configured_timezone))

    if short:
        return now.strftime(timestamp_fmt_short)

    return now.strftime(timestamp_fmt)


def fetch_timestamp_from_time_obj(t: datetime, tz: str | None = None):
    """Return a localized, formatted timestamp using datetime.datetime class"""

    return t.astimezone(ZoneInfo(tz or configured_timezone)).strftime(
        timestamp_fmt
    )


def find_index_in_list(lst: List, key: Any, value: Any):
    """Takes a list of dictionaries and returns
    the index value if key matches.
    """

    for i, dic in enumerate(lst):
        if dic[key] == value:
            return i

    return -1


def paginate_dictionary(d, per_page):
    """Takes a dictionary and returns per_page items at a time"""

    iterable = iter(d)
    while True:
        p = tuple(itertools.islice(iterable, per_page))
        if not p:
            break

        yield p


def random_string_generator() -> str:
    """Return a random string containing upcase characters and digits"""

    return "".join(
        random.choices(
            string.ascii_uppercase + string.digits,
            k=8,
        )
    )


def validate_date_format_string(fmt: str) -> bool:
    try:
        placeholder_date = datetime.strftime(datetime.now(), fmt)
        datetime.strptime(placeholder_date, fmt)

        return True
    except Exception:
        return False


def validate_ip_address(address: str) -> bool:
    """Validate that a provided string is an IP address"""

    try:
        ipaddress.ip_network(address)

        return True
    except ValueError as error:
        logger.error(error)
        return False


def validate_ip_in_subnet(address: str, subnet: str) -> bool:
    """Return whether or not an IP address is within a subnet"""

    return ipaddress.ip_address(address) in ipaddress.ip_network(subnet)
