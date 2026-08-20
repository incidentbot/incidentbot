import datetime
import json
import time

from functools import lru_cache
from incidentbot.configuration.settings import settings
from incidentbot.exceptions import IndexNotFoundError
from incidentbot.logging import logger
from incidentbot.models.database import engine, ApplicationData
from incidentbot.util import gen
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from sqlalchemy import update
from sqlmodel import Session, select

from typing import Any

# Initialize Slack clients
# Constructing the client makes no network call; everything derived from
# auth_test() is resolved lazily so importing this module is safe when
# settings.platform is not "slack" (or when no token is configured).
slack_web_client = WebClient(token=settings.SLACK_BOT_TOKEN)

"""
Reusable variables
"""


@lru_cache(maxsize=1)
def _auth_test() -> dict:
    if settings.IS_TEST_ENVIRONMENT:
        return {"user_id": "test", "user": "test", "url": "https://test.slack.com"}

    return slack_web_client.auth_test()


@lru_cache(maxsize=1)
def _workspace_groups() -> dict:
    if settings.IS_TEST_ENVIRONMENT:
        return {"usergroups": []}

    return slack_web_client.usergroups_list()


def _bot_user_id() -> str:
    return _auth_test().get("user_id")


def _bot_user_name() -> str:
    return _auth_test().get("user")


def _slack_workspace_id() -> str:
    return _auth_test().get("url").replace("https://", "").split(".")[0]


# ponytail: PEP 562 module __getattr__ keeps the old module-level names working
# for importers without doing the API calls at import time.
_LAZY_ATTRS = {
    "slack_web_client_auth_test": _auth_test,
    "all_workspace_groups": _workspace_groups,
    "bot_user_id": _bot_user_id,
    "bot_user_name": _bot_user_name,
    "slack_workspace_id": _slack_workspace_id,
}


def __getattr__(name: str):
    if name in _LAZY_ATTRS:
        return _LAZY_ATTRS[name]()

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

# Users to skip invites for
skip_invite_for_users = ["api", "web"]


def _slack_call_with_retry(fn, *args, **kwargs):
    """Execute a single Slack API call, retrying once on HTTP 429."""
    try:
        return fn(*args, **kwargs)
    except SlackApiError as error:
        if error.response.status_code == 429:
            delay = int(error.response.headers.get("Retry-After", 5))
            logger.warning("rate limited by slack api, retrying", delay_seconds=delay)
            time.sleep(delay)
            return fn(*args, **kwargs)
        raise


"""
Conversations
"""


def get_channel_history(channel_id: str) -> str:
    """
    Return the history of a Slack channel as a json string object

    Parameters:
        channel_id (str): The ID of the Slack channel to retrieve history from
    """

    history: list = []
    res = _slack_call_with_retry(
        slack_web_client.conversations_history, channel=channel_id, limit=200
    )
    while res:
        history += res.get("messages", [])
        if res.get("has_more"):
            res = _slack_call_with_retry(
                slack_web_client.conversations_history,
                channel=channel_id,
                limit=200,
                cursor=res.get("response_metadata", {}).get("next_cursor"),
            )
        else:
            res = None
    return json.dumps(list(reversed(history)))


def get_channel_list() -> dict[str, str]:
    """
    Return a list of Slack channels
    """

    channels = []
    res = _slack_call_with_retry(
        slack_web_client.conversations_list, exclude_archived=True, limit=1000
    )
    while res:
        channels += res.get("channels", [])
        next_cursor = res.get("response_metadata", {}).get("next_cursor", "")
        if next_cursor:
            res = _slack_call_with_retry(
                slack_web_client.conversations_list,
                exclude_archived=True,
                limit=1000,
                cursor=next_cursor,
            )
        else:
            res = None

    logger.info("found slack channels", count=len(channels))
    return channels


def get_channel_name(channel_id: str) -> str:
    """
    Get a Slack channel name by ID

    Parameters:
        channel_id (str): Channel ID
    """

    channels = get_slack_channel_list_db()
    index = gen.find_index_in_list(channels, "id", channel_id)
    if index == -1:
        raise IndexNotFoundError(
            "Could not find index for channel in Slack conversations list"
        )
    return channels[index].get("name")


@lru_cache(maxsize=1)
def _get_slack_channel_list_cached(bucket: int):
    # bucket changes every TTL seconds -> cache invalidates automatically
    return get_slack_channel_list_db()


def get_digest_channel_id() -> str:
    """
    Resolve the channel ID for the digest channel configured in settings.digest_channel
    """

    value = settings.digest_channel
    if not value:
        raise ValueError("settings.digest_channel is empty")

    channels = _get_slack_channel_list_cached(int(time.time() // 300))

    # ID first
    for ch in channels:
        if ch.get("id") == value:
            return ch["id"]

    # name (case-insensitive)
    v = value.lower()
    for ch in channels:
        if (name := ch.get("name")) and name.lower() == v:
            return ch["id"]

    raise IndexNotFoundError(
        f"Could not resolve digest channel '{value}' from Slack conversations list"
    )


def get_formatted_channel_history(channel_id: str, channel_name: str) -> str:
    """
    Return the history of a Slack channel as a formatted string

    Parameters:
        channel_id (str): The ID of the Slack channel to retrieve history from
        channel_name (str): The name of the Slack channel to retrieve history from
    """

    users = _slack_call_with_retry(slack_web_client.users_list)["members"]
    replaced_messages_string = replace_user_ids(get_channel_history(channel_id), users)

    formatted_channel_history = f"Slack channel history for incident {channel_name}\n"
    for message in replaced_messages_string:
        user = message["user"]
        text = message["text"]
        timestamp = datetime.datetime.fromtimestamp(int(message["ts"].split(".")[0]))
        prefix = f"* {timestamp}"
        if "has joined the channel" in text:
            formatted_channel_history += f"{prefix} {user} joined the channel\n"
        elif "set the channel topic" in text:
            formatted_channel_history += f"{prefix} {user} {text}\n"
        elif "This content can't be displayed." in text:
            pass
        else:
            formatted_channel_history += f"{prefix} {user}: {text}\n"

    return formatted_channel_history


def get_conversation_members(channel_id: str) -> list[str]:
    """
    Retrieves Slack users as members of a channel (conversation)

    Parameters:
        channel_id (str): Channel ID
    """

    members = []
    res = _slack_call_with_retry(
        slack_web_client.conversations_members, channel=channel_id, limit=200
    )
    while res:
        members += res.get("members", [])
        next_cursor = res.get("response_metadata", {}).get("next_cursor", "")
        if next_cursor:
            res = _slack_call_with_retry(
                slack_web_client.conversations_members,
                channel=channel_id,
                cursor=next_cursor,
                limit=200,
            )
        else:
            res = None
    return members


def get_message_content(conversation_id: str, ts: str):
    """
    Given a Slack conversation and a message timestamp,
    return information about a message.

    Parameters:
        conversation_id (str): Channel ID
        ts (str): Timestamp field
    """

    result = _slack_call_with_retry(
        slack_web_client.conversations_history,
        channel=conversation_id,
        inclusive=True,
        oldest=ts,
        limit=1,
    )
    return result["messages"][0]


def get_slack_channel_list_db() -> list[dict]:
    """
    Get Slack channel list from database
    """

    try:
        with Session(engine) as session:
            record = session.exec(
                select(ApplicationData).filter(
                    ApplicationData.name == "slack_channels"
                )
            ).first()

            return record.json_data
    except Exception as error:
        logger.exception(
            "error retrieving list of slack channels from db", error=error
        )


def invite_user_to_channel(channel_id: str, user: str):
    """
    Invites a user to a Slack channel, checks if they're in it first

    Parameters:
        channel_id (str): Channel ID
        user (str): User ID
    """

    if (
        user not in get_conversation_members(channel_id)
        and user not in skip_invite_for_users
    ):
        _slack_call_with_retry(
            slack_web_client.conversations_invite, channel=channel_id, users=user
        )


def store_slack_channel_list_db():
    """
    Retrieves information about Slack channels for a workspace and stores
    it in the database
    """

    logger.info("running task update_slack_channel_list")

    try:
        with Session(engine) as session:
            record_name = "slack_channels"

            # Create the row if it doesn't exist
            if not session.exec(
                select(ApplicationData).filter(
                    ApplicationData.name == record_name
                )
            ).all():
                try:
                    row = ApplicationData(name=record_name)
                    session.add(row)
                    session.commit()
                except Exception as error:
                    logger.exception(
                        "applicationdata row create failed", record_name=record_name, error=error
                    )

            session.exec(
                update(ApplicationData)
                .where(ApplicationData.name == record_name)
                .values(
                    json_data=get_channel_list(),
                )
            )
            session.commit()
            logger.info("stored current slack channels in database")
    except Exception as error:
        logger.exception(
            "applicationdata row edit failed", record_name=record_name, error=error
        )


"""
Users
"""


def check_bot_user_in_digest_channel():
    """
    Adds bot user to digest channel if not already present
    """

    digest_channel_id = get_digest_channel_id()
    members = _slack_call_with_retry(
        slack_web_client.conversations_members, channel=digest_channel_id
    )["members"]
    channel_name = get_channel_name(channel_id=digest_channel_id)

    if _bot_user_id() not in members:
        slack_web_client.conversations_join(channel=digest_channel_id)
        logger.info("added bot user to digest channel", channel=channel_name)
    else:
        logger.info("bot user is already present in digest channel", channel=channel_name)


def check_user_in_group(user_id: str, group_name: str) -> bool:
    """
    Provided a user ID and a group name, return a bool indicating
    whether or not the user is in the group

    Parameters:
        user_id (str): User ID
        group_name (str): Name of the group
    """

    all_groups = _workspace_groups().get("usergroups", [])
    target_group = [g for g in all_groups if g["handle"] == group_name]

    if not target_group:
        logger.error("group not found", group=group_name)
        return False

    target_group_members = _slack_call_with_retry(
        slack_web_client.usergroups_users_list,
        usergroup=target_group[0].get("id"),
    ).get("users", [])

    return user_id in target_group_members


def get_slack_user(user_id: str) -> dict | None:
    """
    Get a single user object by id

    This is done against the local database so it won't work unless the job to store
    slack user data has been run

    Parameters:
        user_id (str): User ID
    """

    with Session(engine) as session:
        ulist = session.exec(
            select(ApplicationData).filter(
                ApplicationData.name == "slack_users"
            )
        ).first()

    for obj in ulist.json_data:
        if user_id in obj.values():
            return obj

    return None


def get_slack_users() -> list[dict[str, Any]]:
    """
    Retrieves Slack users from a workspace using pagination
    """

    users: list = []
    res = _slack_call_with_retry(slack_web_client.users_list)
    while res:
        users += res.get("members") or []
        next_cursor = res.get("response_metadata", {}).get("next_cursor")
        if next_cursor:
            res = _slack_call_with_retry(slack_web_client.users_list, cursor=next_cursor)
        else:
            res = None

    users_array = [
        {
            "name": user["name"],
            "real_name": user["profile"].get("real_name", ""),
            "email": user["profile"].get("email"),
            "id": user["id"],
        }
        for user in users
    ]

    jdata = sorted(users_array, key=lambda d: d["name"])

    logger.info("found slack users", count=len(users_array))

    return jdata


def replace_user_ids(json_string: str, user_list: dict[str, str]) -> str:
    """
    Replace a user's ID with their name and return a json string object

    Parameters:
        json_string (str): String to replace ID
        user_list (dict[str, str]): User list for reference
    """

    for user in user_list:
        real_name = user["profile"]["real_name"]
        user_id = user["id"]
        json_string = json_string.replace(user_id, real_name)

    return json.loads(json_string)


def store_slack_user_list_db():
    """
    Retrieves list of users from Slack organization and stores them using a clean format
    to be retrieved locally to avoid querying the Slack API every time this data
    is desired
    """

    logger.info("running task update_slack_user_list")

    try:
        with Session(engine) as session:
            # Delete if exists
            if session.exec(
                select(ApplicationData).filter(
                    ApplicationData.name == "slack_users"
                )
            ).first():
                existing = session.exec(
                    select(ApplicationData).filter(
                        ApplicationData.name == "slack_users"
                    )
                ).first()
                session.delete(existing)
                session.commit()

            # Store
            row = ApplicationData(
                name="slack_users",
                json_data=get_slack_users(),
            )

            session.add(row)
            session.commit()
            logger.info("stored current slack users in database")
    except Exception as error:
        logger.exception(
            "applicationdata row create failed", record_name="slack_users", error=error
        )
