import config
import ipaddress
import itertools
import logging
import random
import string

from datetime import datetime
from pytz import timezone
from typing import Any, List

logger = logging.getLogger("shared")

random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
timestamp_fmt = "%Y-%m-%dT%H:%M:%S %Z"
timestamp_fmt_short = "%d/%m/%Y %H:%M:%S %Z"

application_timezone = config.active.options.get("timezone")


def fetch_timestamp(short: bool = False):
    """Return a localized, formatted timestamp using datetime.now()"""
    now = datetime.now()
    localized = timezone(application_timezone).localize(now)
    if short:
        return localized.strftime(timestamp_fmt_short)
    return localized.strftime(timestamp_fmt)


def fetch_timestamp_from_time_obj(t: datetime):
    """Return a localized, formatted timestamp using datetime.datetime class"""
    return timezone(application_timezone).localize(t).strftime(timestamp_fmt)


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
