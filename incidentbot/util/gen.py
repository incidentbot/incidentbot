import itertools
import random
import string

from datetime import datetime
from incidentbot.configuration.settings import settings
from typing import Any
from zoneinfo import ZoneInfo

timestamp_fmt = "%Y-%m-%dT%H:%M:%S"


def fetch_timestamp(
    epoch: bool | None = False,
    tz: str | None = None,
):
    """
    Return a localized, formatted timestamp using datetime.now()
    """

    now = datetime.now(ZoneInfo(tz or settings.options.timezone))

    if epoch:
        return now.timestamp()

    return now.strftime(timestamp_fmt)


def find_index_in_list(lst: list, key: Any, value: Any):
    """
    Takes a list of dictionaries and returns the index value if key matches.
    """

    for i, dic in enumerate(lst):
        if dic[key] == value:
            return i

    return -1


def paginate_dictionary(d, per_page):
    """
    Takes a dictionary and returns per_page items at a time
    """

    iterable = iter(d)
    while True:
        p = tuple(itertools.islice(iterable, per_page))
        if not p:
            break

        yield p


def random_string_generator() -> str:
    """
    Return a random string containing upcase characters and digits
    """

    return "".join(
        random.choices(
            string.ascii_uppercase + string.digits,
            k=8,
        )
    )
