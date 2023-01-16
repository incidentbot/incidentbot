import config
import ipaddress
import json
import logging
import random
import string

from datetime import datetime
from pytz import timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

random_suffix = "".join(
    random.choices(string.ascii_lowercase + string.digits, k=6)
)
timestamp_fmt = "%Y-%m-%dT%H:%M:%S %Z"
timestamp_fmt_short = "%d/%m/%Y %H:%M:%S %Z"

application_timezone = config.active.options.get("timezone")


class dotdict(Dict):
    """dot.notation access to dictionary attributes"""

    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def fetch_timestamp(short: bool = False):
    """
    Return a localized, formatted timestamp using datetime.now()
    """
    now = datetime.now()
    localized = timezone(application_timezone).localize(now)
    if short:
        return localized.strftime(timestamp_fmt_short)
    return localized.strftime(timestamp_fmt)


def fetch_timestamp_from_time_obj(t: datetime):
    """
    Return a localized, formatted timestamp using datetime.datetime class
    """
    return timezone(application_timezone).localize(t).strftime(timestamp_fmt)


def find_index_in_list(lst: List, key: Any, value: Any):
    """Takes a list of dictionaries and returns
    the index value if key matches.
    """
    for i, dic in enumerate(lst):
        if dic[key] == value:
            return i
    return -1


def validate_ip_address(address):
    try:
        ipaddress.ip_network(address)
        return True
    except ValueError as error:
        logger.error(error)
        return False
