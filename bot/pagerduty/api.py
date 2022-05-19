import config
import logging

from bot.slack.client import slack_web_client
from collections import defaultdict
from pdpyras import APISession
from typing import Dict, List

logger = logging.getLogger(__name__)

session = APISession(
    config.pagerduty_api_token, default_from=config.pagerduty_api_username
)

"""
PagerDuty
"""


def find_who_is_on_call() -> List:
    """
    Given a PagerDuty instance, loop through oncall schedules and return info
    on each one identifying who to contact when run
    """
    on_call = defaultdict(list)
    slack_users = {
        user["real_name"]: user["id"]
        for user in slack_web_client.users_list()["members"]
        if user.__contains__("real_name")
    }
    for oc in session.iter_all("oncalls"):
        if oc["start"] != None and oc["end"] != None:
            on_call[oc["escalation_policy"]["summary"]].append(
                {
                    "escalation_level": oc["escalation_level"],
                    "escalation_policy": oc["escalation_policy"]["summary"],
                    "schedule_summary": oc["schedule"]["summary"],
                    "user": oc["user"]["summary"],
                    "start": oc["start"],
                    "end": oc["end"],
                    "slack_user_id": [
                        val
                        for key, val in slack_users.items()
                        if oc["user"]["summary"] in key
                    ],
                }
            )
    # Sort values by escalation_level
    result = {}
    for i, j in dict(on_call).items():
        result[i] = sorted(j, key=lambda d: d["escalation_level"])
    return result
