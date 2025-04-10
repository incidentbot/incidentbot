import datetime
import json
import random
import string

from typing import Any, List

random_suffix = "".join(
    random.choices(string.ascii_lowercase + string.digits, k=6)
)
timestamp_fmt = "%Y-%m-%dT%H:%M:%S %Z"
timestamp_fmt_short = "%d/%m/%Y %H:%M:%S"


def is_json(val: string) -> bool:
    try:
        json.loads(val)
    except ValueError:
        return False
    return True


def fetch_timestamp(short: bool = False):
    if short:
        return (
            datetime.datetime.now().astimezone().strftime(timestamp_fmt_short)
        )
    return datetime.datetime.now().astimezone().strftime(timestamp_fmt)


def find_index_in_list(lst: List, key: Any, value: Any):
    """Takes a list of dictionaries and returns
    the index value if key matches.
    """
    for i, dic in enumerate(lst):
        if dic[key] == value:
            return i
    return -1
