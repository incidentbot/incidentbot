import datetime
import json
import time

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
slack_web_client = WebClient(token=settings.SLACK_BOT_TOKEN)
slack_web_client_auth_test = slack_web_client.auth_test()

"""
Reusable variables
"""

all_workspace_groups = (
    slack_web_client.usergroups_list()
    if not settings.IS_TEST_ENVIRONMENT
    else []
)

bot_user_id = (
    slack_web_client_auth_test.get("user_id")
    if not settings.IS_TEST_ENVIRONMENT
    else "test"
)

bot_user_name = (
    slack_web_client_auth_test.get("user")
    if not settings.IS_TEST_ENVIRONMENT
    else "test"
)

slack_workspace_id = (
    slack_web_client_auth_test.get("url").replace("https://", "").split(".")[0]
    if not settings.IS_TEST_ENVIRONMENT
    else "test"
)

# Users to skip invites for
skip_invite_for_users = ["api", "web"]


"""
Conversations
"""


def get_channel_history(channel_id: str) -> str:
    """
    Return the history of a Slack channel as a json string object

    Parameters:
        channel_id (str): The ID of the Slack channel to retrieve history from
    """

    history_dict_list = []

    try:
        res = slack_web_client.conversations_history(
            channel=channel_id, limit=200
        )

        while res:
            history_dict_list += res.get("messages")

            if res.get("has_more"):
                res = slack_web_client.conversations_history(
                    channel=channel_id,
                    limit=200,
                    cursor=res.get("response_metadata").get("next_cursor"),
                )
            else:
                res = None
    except SlackApiError as error:
        if error.response.status_code == 429:
            delay = int(error.response.headers["Retry-After"])
            logger.warning(
                f"Rate limited by Slack API. Retrying in {delay} seconds..."
            )
            time.sleep(delay)
            res = slack_web_client.conversations_history(
                channel=channel_id, limit=200
            )

            while res:
                history_dict_list += res.get("messages")

                if res.get("has_more"):
                    res = slack_web_client.conversations_history(
                        channel=channel_id,
                        limit=200,
                        cursor=res.get("response_metadata").get("next_cursor"),
                    )
                else:
                    res = None
        else:
            raise error

    history_dict_reversed = []

    for item in reversed(history_dict_list):
        history_dict_reversed.append(item)

    return json.dumps(history_dict_reversed)


def get_channel_list() -> dict[str, str]:
    """
    Return a list of Slack channels
    """

    channels = []

    try:
        res = slack_web_client.conversations_list(
            exclude_archived=True,
            limit=1000,
        )

        while res:
            channels += res.get("channels")

            if res.get("response_metadata").get("next_cursor") != "":
                res = slack_web_client.conversations_list(
                    exclude_archived=True,
                    limit=1000,
                    cursor=res.get("response_metadata").get("next_cursor"),
                )
            else:
                res = None
    except SlackApiError as error:
        if error.response.status_code == 429:
            delay = int(error.response.headers["Retry-After"])
            logger.warning(
                f"Rate limited by Slack API. Retrying in {delay} seconds..."
            )
            time.sleep(delay)
            res = slack_web_client.conversations_list(
                exclude_archived=True,
                limit=1000,
            )

            while res:
                channels += res.get("channels")

                if res.get("response_metadata").get("next_cursor") != "":
                    res = slack_web_client.conversations_list(
                        exclude_archived=True,
                        limit=1000,
                        cursor=res.get("response_metadata").get("next_cursor"),
                    )
                else:
                    res = None
        else:
            raise error

    logger.info(f"Found {len(channels)} Slack channels")

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


def get_digest_channel_id() -> str:
    """
    Get channel id of the incidents digest channel to send updates to
    """

    channels = get_slack_channel_list_db()
    index = gen.find_index_in_list(channels, "name", settings.digest_channel)
    if index == -1:
        raise IndexNotFoundError(
            "Could not find index for digest channel in Slack conversations list"
        )
    return channels[index].get("id")


def get_formatted_channel_history(channel_id: str, channel_name: str) -> str:
    """
    Return the history of a Slack channel as a formatted string

    Parameters:
        channel_id (str): The ID of the Slack channel to retrieve history from
        channel_name (str): The name of the Slack channel to retrieve history from
    """

    try:
        users = slack_web_client.users_list()["members"]
        replaced_messages_string = replace_user_ids(
            get_channel_history(channel_id), users
        )

        formatted_channel_history = str()
        formatted_channel_history += (
            f"Slack channel history for incident {channel_name}\n"
        )

        for message in replaced_messages_string:
            user = message["user"]
            text = message["text"]
            timestamp = datetime.datetime.fromtimestamp(
                int(message["ts"].split(".")[0])
            )
            prefix = f"* {timestamp}"
            if "has joined the channel" in text:
                formatted_channel_history += (
                    f"{prefix} {user} joined the channel\n"
                )
            elif "set the channel topic" in text:
                formatted_channel_history += f"{prefix} {user} {text}\n"
            elif "This content can't be displayed." in text:
                pass
            else:
                formatted_channel_history += f"{prefix} {user}: {text}\n"
    except SlackApiError as error:
        if error.response.status_code == 429:
            delay = int(error.response.headers["Retry-After"])
            logger.warning(
                f"Rate limited by Slack API. Retrying in {delay} seconds..."
            )
            time.sleep(delay)
            users = slack_web_client.users_list()["members"]
            replaced_messages_string = replace_user_ids(
                get_channel_history(channel_id), users
            )

            formatted_channel_history = str()
            formatted_channel_history += (
                f"Slack channel history for incident {channel_name}\n"
            )

            for message in replaced_messages_string:
                user = message["user"]
                text = message["text"]
                timestamp = datetime.datetime.fromtimestamp(
                    int(message["ts"].split(".")[0])
                )
                prefix = f"* {timestamp}"
                if "has joined the channel" in text:
                    formatted_channel_history += (
                        f"{prefix} {user} joined the channel\n"
                    )
                elif "set the channel topic" in text:
                    formatted_channel_history += f"{prefix} {user} {text}\n"
                elif "This content can't be displayed." in text:
                    pass
                else:
                    formatted_channel_history += f"{prefix} {user}: {text}\n"
        else:
            raise error

    return formatted_channel_history


def get_conversation_members(channel_id: str) -> list[str]:
    """
    Retrieves Slack users as members of a channel (conversation)

    Parameters:
        channel_id (str): Channel ID
    """

    members = []

    try:
        res = slack_web_client.conversations_members(
            channel=channel_id, limit=200
        )

        while res:
            members += res.get("members")

            if res.get("response_metadata").get("next_cursor") != "":
                res = slack_web_client.conversations_members(
                    channel=channel_id,
                    cursor=res.get("response_metadata").get("next_cursor"),
                    limit=200,
                )
            else:
                res = None
    except SlackApiError as error:
        if error.response.status_code == 429:
            delay = int(error.response.headers["Retry-After"])
            logger.warning(
                f"Rate limited by Slack API. Retrying in {delay} seconds..."
            )
            time.sleep(delay)
            res = slack_web_client.conversations_members(
                channel=channel_id, limit=200
            )

            while res:
                members += res.get("members")

                if res.get("response_metadata").get("next_cursor") != "":
                    res = slack_web_client.conversations_members(
                        channel=channel_id,
                        cursor=res.get("response_metadata").get("next_cursor"),
                        limit=200,
                    )
                else:
                    res = None
        else:
            raise error

    return members


def get_message_content(conversation_id: str, ts: str):
    """
    Given a Slack conversation and a message timestamp,
    return information about a message.

    Parameters:
        conversation_id (str): Channel ID
        ts (str): Timestamp field
    """

    try:
        result = slack_web_client.conversations_history(
            channel=conversation_id, inclusive=True, oldest=ts, limit=1
        )
    except SlackApiError as error:
        if error.response.status_code == 429:
            delay = int(error.response.headers["Retry-After"])
            logger.warning(
                f"Rate limited by Slack API. Retrying in {delay} seconds..."
            )
            time.sleep(delay)
            result = slack_web_client.conversations_history(
                channel=conversation_id, inclusive=True, oldest=ts, limit=1
            )
        else:
            raise error

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
        logger.error(
            f"Error retrieving list of Slack channels from db: {error}"
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
        try:
            slack_web_client.conversations_invite(
                channel=channel_id,
                users=user,
            )
        except SlackApiError as error:
            if error.response.status_code == 429:
                delay = int(error.response.headers["Retry-After"])
                logger.warning(
                    f"Rate limited by Slack API. Retrying in {delay} seconds..."
                )
                time.sleep(delay)
                slack_web_client.conversations_invite(
                    channel=channel_id,
                    users=user,
                )
            else:
                raise error


def store_slack_channel_list_db():
    """
    Retrieves information about Slack channels for a workspace and stores
    it in the database
    """

    logger.info("[running task update_slack_channel_list]")

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
                    logger.error(
                        f"ApplicationData row create failed for {record_name}: {error}"
                    )

            session.exec(
                update(ApplicationData)
                .where(ApplicationData.name == record_name)
                .values(
                    json_data=get_channel_list(),
                )
            )
            session.commit()
            logger.info("Stored current Slack channels in database...")
    except Exception as error:
        logger.error(
            f"ApplicationData row edit failed for {record_name}: {error}"
        )


"""
Users
"""


def check_bot_user_in_digest_channel():
    """
    Adds bot user to digest channel if not already present
    """

    digest_channel_id = get_digest_channel_id()

    try:
        if (
            bot_user_id
            not in slack_web_client.conversations_members(
                channel=digest_channel_id
            )["members"]
        ):
            slack_web_client.conversations_join(channel=digest_channel_id)
            logger.info(
                f"Added bot user to digest channel #{get_channel_name(channel_id=digest_channel_id)}"
            )
    except SlackApiError as error:
        if error.response.status_code == 429:
            delay = int(error.response.headers["Retry-After"])
            logger.warning(
                f"Rate limited by Slack API. Retrying in {delay} seconds..."
            )
            time.sleep(delay)

            if (
                bot_user_id
                not in slack_web_client.conversations_members(
                    channel=digest_channel_id
                )["members"]
            ):
                slack_web_client.conversations_join(channel=digest_channel_id)
                logger.info(
                    f"Added bot user to digest channel #{get_channel_name(channel_id=digest_channel_id)}"
                )
        else:
            raise error
    else:
        logger.info(
            f"Bot user is already present in digest channel #{get_channel_name(channel_id=digest_channel_id)}"
        )


def check_user_in_group(user_id: str, group_name: str) -> bool:
    """
    Provided a user ID and a group name, return a bool indicating
    whether or not the user is in the group

    Parameters:
        user_id (str): User ID
        group_name (str): Name of the group
    """

    all_groups = all_workspace_groups.get("usergroups")

    try:
        target_group = [g for g in all_groups if g["handle"] == group_name]

        if len(target_group) == 0:
            logger.error(f"Couldn't find group {group_name}")
            return False

        target_group_members = slack_web_client.usergroups_users_list(
            usergroup=target_group[0].get("id"),
        ).get("users")
    except SlackApiError as error:
        if error.response.status_code == 429:
            delay = int(error.response.headers["Retry-After"])
            logger.warning(
                f"Rate limited by Slack API. Retrying in {delay} seconds..."
            )
            time.sleep(delay)
            target_group = [g for g in all_groups if g["handle"] == group_name]

            if len(target_group) == 0:
                logger.error(f"Couldn't find group {group_name}")
                return False

            target_group_members = slack_web_client.usergroups_users_list(
                usergroup=target_group[0].get("id"),
            ).get("users")
        else:
            raise error

    if user_id in target_group_members:
        return True

    return False


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

    users = []

    try:
        res = slack_web_client.users_list()

        while res:
            users += res.get("members")

            if res.get("response_metadata").get("next_cursor") != "":
                res = slack_web_client.users_list(
                    cursor=res.get("response_metadata").get("next_cursor")
                )
            else:
                res = None
    except SlackApiError as error:
        if error.response.status_code == 429:
            delay = int(error.response.headers["Retry-After"])
            logger.warning(
                f"Rate limited by Slack API. Retrying in {delay} seconds..."
            )
            time.sleep(delay)
            res = slack_web_client.users_list()

            while res:
                users += res.get("members")

                if res.get("response_metadata").get("next_cursor") != "":
                    res = slack_web_client.users_list(
                        cursor=res.get("response_metadata").get("next_cursor")
                    )
                else:
                    res = None
        else:
            raise error

    users_array = [
        {
            "name": user["name"],
            "real_name": user["profile"]["real_name"],
            "email": user["profile"].get("email"),
            "id": user["id"],
        }
        for user in users
    ]

    jdata = sorted(users_array, key=lambda d: d["name"])

    logger.info(f"Found {len(users_array)} Slack users")

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

    logger.info("[running task update_slack_user_list]")

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
            logger.info("Stored current Slack users in database...")
    except Exception as error:
        logger.error(
            f"ApplicationData row create failed for slack_users: {error}"
        )
