import asyncio
import re
import requests
import slack_sdk

from incidentbot.configuration.settings import settings
from incidentbot.version import APP_VERSION
from incidentbot.incident.actions import (
    archive_incident_channel,
    export_chat_logs,
    join_incident_as_role,
    leave_incident_as_role,
    set_severity as set_incident_severity,
    set_status as set_incident_status,
    sync_postmortem,
)
from incidentbot.incident.event import EventLogHandler
from incidentbot.logging import logger
from incidentbot.models.database import ApplicationData, engine
from incidentbot.models.incident import IncidentDatabaseInterface
from incidentbot.models.slack import SlackBlockActionsResponse
from incidentbot.slack.client import (
    get_slack_user,
    slack_web_client,
)
from incidentbot.slack.messages import (
    BlockBuilder,
)
from incidentbot.slack.postmortem_sync_guard import (
    begin_postmortem_sync,
    end_postmortem_sync,
)
from incidentbot.util import gen
from slack_bolt import App
from slack_sdk.errors import SlackApiError
from sqlmodel import Session, select

## The xoxb oauth token for the bot is called here to provide bot privileges.
app = App(token=settings.SLACK_BOT_TOKEN)


@app.error
def custom_error_handler(error, body, logger):
    logger.exception("error", error=error)
    logger.debug("request body", body=body)


from . import command  # noqa: F401 E402
from . import modals  # noqa: F401 E402


@app.event("message")
def handle_message_events(body, logger):
    # This generates errors if absent. I don't know why.
    pass


"""
Handle Mentions
"""


@app.event("app_mention")
def handle_mention(body, say, logger):
    message = body.get("event").get("text").split(" ")
    _ = body["event"]["user"]
    logger.debug(body)

    if len(message) == 1:
        # This is just a user mention and the bot shouldn't really do anything.
        return

    match message[1]:
        case "help":
            say(f"Use my slash command! `{settings.root_slash_command}`")
        case "pager":
            if (
                settings.integrations
                and settings.integrations.pagerduty
                and settings.integrations.pagerduty.enabled
            ):
                from incidentbot.configuration.settings import (
                    pagerduty_logo_url,
                )
                from incidentbot.pagerduty.api import (
                    PagerDutyInterface,
                )

                pagerduty_interface = PagerDutyInterface()

                pd_oncall_data = pagerduty_interface.get_on_calls()
                if pd_oncall_data == {}:
                    say(
                        text="Hmm... I'm unable to get that information from PagerDuty - when I looked for schedules, I couldn't find any. Check my logs for additional information."
                    )
                else:
                    # Header
                    say(
                        blocks=[
                            {
                                "type": "header",
                                "text": {
                                    "type": "plain_text",
                                    "text": ":pager: Who is on call right now?",
                                },
                            },
                            {"type": "divider"},
                        ],
                        text="Oncall information was sent.",
                    )

                    # Iterate over schedules
                    if pd_oncall_data != {}:
                        # Get length of returned objects
                        # If returned objects is greater than 5, paginate over them 5 at a time and include 5 in each message
                        # Send a separate message for each grouping of 5 to avoid block limits from the Slack API
                        for page in gen.paginate_dictionary(
                            pd_oncall_data.items(),
                            settings.options.slack_items_pagination_per_page,
                        ):
                            base_block = []

                            for key, value in page:
                                options = []
                                for item in value:
                                    if item.get("slack_user_id") != []:
                                        user_mention = item.get(
                                            "slack_user_id"
                                        )[0]
                                    else:
                                        user_mention = item.get("user")
                                    options.append(
                                        {
                                            "text": {
                                                "type": "plain_text",
                                                "text": "{} {}".format(
                                                    item.get(
                                                        "escalation_level"
                                                    ),
                                                    item.get("user"),
                                                ),
                                            },
                                            "value": user_mention,
                                        },
                                    )
                                base_block.append(
                                    {
                                        "type": "section",
                                        "block_id": f"ping_oncall_{gen.random_string_generator()}",
                                        "text": {
                                            "type": "mrkdwn",
                                            "text": f"*{key}*",
                                        },
                                        "accessory": {
                                            "type": "overflow",
                                            "options": options,
                                            "action_id": "incident.add_on_call_to_channel",
                                        },
                                    }
                                )
                            say(
                                blocks=base_block,
                                text="Oncall information was sent.",
                            )
                    else:
                        say(
                            text="There are no results from PagerDuty to display."
                        )

                    # Footer
                    say(
                        blocks=[
                            {
                                "type": "context",
                                "elements": [
                                    {
                                        "type": "image",
                                        "image_url": pagerduty_logo_url,
                                        "alt_text": "pagerduty",
                                    },
                                    {
                                        "type": "mrkdwn",
                                        "text": f"This information is sourced from PagerDuty and is accurate as of {gen.fetch_timestamp()}.",
                                    },
                                ],
                            }
                        ],
                        text="Oncall information was sent.",
                    )
            else:
                say(
                    text=":no_entry: Sorry - no platforms have been added for handling paging yet. Ask the administrator about adding one."
                )
        case "ping":
            say(text="pong")
        case "version":
            say(text=f"I am currently running version: {APP_VERSION}")
        case _:
            resp = " ".join(message[1:])
            say(text=f"Sorry, I don't know the command `{resp}` yet.")


"""
Incident Management Actions
"""


@app.action("incident.add_on_call_to_channel")
def handle_incident_add_on_call(ack, body, say):
    logger.debug(body)
    ack()
    user = body["user"]["id"]

    say(
        channel=user,
        text="Hi! If you want to page someone, use my shortcut 'Incident Bot Pager' instead!",
    )


@app.action("incident.archive_incident_channel")
def handle_incident_archive_incident_channel(ack, body):
    logger.debug(body)
    ack()
    parsed_body = SlackBlockActionsResponse(**body)

    asyncio.run(archive_incident_channel(channel_id=parsed_body.channel.id))


@app.action("incident.clicked_meeting_link")
def handle_static_action(ack, body, logger):  # noqa: F811
    logger.debug(body)
    ack()


if settings.links:
    for link in settings.links:

        @app.action(
            f"incident.clicked_link_{link.title.lower().replace(' ', '_')}"
        )
        def handle_static_action(ack, body, logger):
            logger.debug(body)
            ack()


@app.action("incident.declare_incident_modal.set_additional_comms_channel")
def handle_static_action(ack, body, logger):  # noqa: F811
    ack()
    logger.info(body)


@app.action("incident.declare_incident_modal.set_private")
def handle_static_action(ack, body, logger):  # noqa: F811
    logger.debug(body)
    ack()


@app.action("incident.declare_incident_modal.set_security_type")
def handle_static_action(ack, body, logger):  # noqa: F811
    logger.debug(body)
    ack()

    try:
        slack_web_client.views_update(
            # Pass the view_id
            view_id=body["view"]["id"],
            # String that represents view state to protect against race conditions
            hash=body["view"]["hash"],
            # View payload with updated blocks
            view={
                "type": "modal",
                "callback_id": "declare_incident_modal",
                "title": {
                    "type": "plain_text",
                    "text": "Start a new incident",
                },
                "submit": {"type": "plain_text", "text": "Start"},
                "blocks": BlockBuilder.declare_incident_modal(
                    security_selected=body.get("actions")[0]
                    .get("selected_option")
                    .get("value")
                    in ["true"],
                ),
            },
        )
    except slack_sdk.errors.SlackApiError as error:
        logger.exception("error deleting message", error=error)


@app.action("incident.declare_incident_modal.set_severity")
def handle_static_action(ack, body, logger):  # noqa: F811
    logger.debug(body)
    ack()


@app.action("incident.export_chat_logs")
def handle_incident_export_chat_logs(ack, body):
    logger.debug(body)
    ack()
    parsed_body = SlackBlockActionsResponse(**body)

    asyncio.run(
        export_chat_logs(
            channel_id=parsed_body.channel.id, user=parsed_body.user.name
        )
    )


for role in [key for key, _ in settings.roles.items()]:

    @app.action(f"incident.join_this_incident_{role}")
    def handle_join_this_incident(ack, body, logger):
        ack()
        logger.info(body)

        parsed_body = SlackBlockActionsResponse(**body)

        asyncio.run(
            join_incident_as_role(
                channel_id=parsed_body.channel.id,
                role=parsed_body.actions[0]
                .get("value")
                .replace("join_this_incident_", ""),
                user=parsed_body.user,
            )
        )


@app.action("incident.get_help_for_this_incident")
def handle_static_action(ack, body, logger):  # noqa: F811
    ack()
    logger.info(body)

    parsed_body = SlackBlockActionsResponse(**body)

    channel_id = parsed_body.channel.id

    try:
        slack_web_client.chat_postMessage(
            channel=channel_id,
            text=f"To interact with an incident, use `{settings.root_slash_command} this`",
            blocks=BlockBuilder.help_message(),
        )
    except SlackApiError as error:
        logger.exception("error sending help message", error=error)


@app.action(re.compile(r"^reminder\.snooze\."))
def handle_reminder_snooze(ack, body, logger):
    ack()
    logger.debug(body)

    try:
        action_id = body["actions"][0]["action_id"]
        # format: reminder.snooze.{reminder_id}.{minutes}
        # maxsplit=3 keeps reminder_id intact even if it contains dots (defensive)
        _, _, reminder_id, minutes_str = action_id.split(".", maxsplit=3)
        minutes = int(minutes_str)
    except (KeyError, ValueError):
        logger.warning("malformed reminder snooze action_id", action_id=body.get("actions", [{}])[0].get("action_id"))
        return

    channel_id = body["channel"]["id"]
    ts = body["message"]["ts"]

    from incidentbot.incident.reminders import handle_snooze
    handle_snooze(channel_id=channel_id, reminder_id=reminder_id, minutes=minutes, ts=ts)


@app.action(re.compile(r"^reminder\.dismiss\."))
def handle_reminder_dismiss(ack, body, logger):
    ack()
    logger.debug(body)

    try:
        action_id = body["actions"][0]["action_id"]
        # format: reminder.dismiss.{reminder_id}
        _, _, reminder_id = action_id.split(".", maxsplit=2)
    except (KeyError, ValueError):
        logger.warning("malformed reminder dismiss action_id", action_id=body.get("actions", [{}])[0].get("action_id"))
        return

    channel_id = body["channel"]["id"]
    ts = body["message"]["ts"]

    from incidentbot.incident.reminders import handle_dismiss
    handle_dismiss(channel_id=channel_id, reminder_id=reminder_id, ts=ts)


@app.action("incident.leave_this_incident")
def handle_static_action(ack, body, logger):  # noqa: F811
    logger.debug(body)
    ack()

    parsed_body = SlackBlockActionsResponse(**body)
    incident = IncidentDatabaseInterface.get_one(
        channel_name=parsed_body.channel.name
    )
    has_role = IncidentDatabaseInterface.check_role_assigned_to_user(
        incident=incident,
        role=parsed_body.actions[0]
        .get("value")
        .replace("leave_this_incident_as_", ""),
        user=parsed_body.user,
    )

    if has_role:
        asyncio.run(
            leave_incident_as_role(
                channel_id=parsed_body.channel.id,
                role=parsed_body.actions[0]
                .get("value")
                .replace("leave_this_incident_as_", ""),
                user=parsed_body.user,
            )
        )


@app.action("incident.list_incidents")
def handle_static_action(ack, body, logger):  # noqa: F811
    logger.debug(body)
    ack()

    parsed_body = SlackBlockActionsResponse(**body)

    database_data = IncidentDatabaseInterface.list_recent(
        limit=settings.options.show_most_recent_incidents_app_home_limit
    )
    open_incidents = BlockBuilder.incident_list(
        incidents=database_data, exclude_timestamp=True
    )

    try:
        slack_web_client.chat_postEphemeral(
            channel=parsed_body.channel.id,
            user=parsed_body.user.id,
            text="incident list",
            blocks=open_incidents,
        )
    except SlackApiError as error:
        logger.exception("error sending message via slash command", error=error)


@app.action("incident.set_severity")
def handle_incident_set_severity(ack, body):
    logger.debug(body)
    ack()
    parsed_body = SlackBlockActionsResponse(**body)

    asyncio.run(
        set_incident_severity(
            channel_id=parsed_body.channel.id,
            severity=parsed_body.actions[0]
            .get("selected_option")
            .get("value"),
            ts=parsed_body.message.ts,
        )
    )


@app.action("incident.set_status")
def handle_incident_set_status(ack, body):
    logger.debug(body)
    ack()
    parsed_body = SlackBlockActionsResponse(**body)

    asyncio.run(
        set_incident_status(
            channel_id=parsed_body.channel.id,
            selected_user=parsed_body.user,
            status=parsed_body.actions[0].get("selected_option").get("value"),
            ts=parsed_body.message.ts,
        )
    )


@app.action("incident.update_modal.select_incident")
def handle_static_action(ack, body, logger):  # noqa: F811
    logger.debug(body)
    ack()


"""
Other
"""


@app.action("view_upstream_incident")
def handle_static_action(ack, body, logger):  # noqa: F811
    ack()
    logger.info(body)


"""
Reactions
"""


@app.event("reaction_added")
def reaction_added(event, say):
    reacji = event.get("reaction")
    channel_id = event.get("item").get("channel")
    message_timestamp = event.get("item").get("ts")

    incident = IncidentDatabaseInterface.get_one(channel_id=channel_id)

    # Pinned content for incidents
    if reacji == settings.pin_content_reacji:
        channel_info = slack_web_client.conversations_info(channel=channel_id)

        prefix = settings.options.channel_name_prefix

        if f"{prefix}-" in channel_info["channel"]["name"]:
            # Retrieve the content of the message that was reacted to
            try:
                result = slack_web_client.conversations_history(
                    channel=channel_id,
                    inclusive=True,
                    oldest=message_timestamp,
                    limit=1,
                )
                message = result["messages"][0]

                if "files" in message:
                    if settings.enable_pinned_images:
                        for file in message["files"]:
                            if "image" in file["mimetype"]:
                                if not file["public_url_shared"]:
                                    # Make the attachment public temporarily
                                    try:
                                        slack_web_client.files_sharedPublicURL(
                                            file=file["id"],
                                            token=settings.SLACK_USER_TOKEN,
                                        )
                                    except SlackApiError as error:
                                        logger.exception(
                                            "error preparing pinned file for copy", error=error
                                        )

                                # Copy the attachment into the database
                                pub_secret = file["permalink_public"].split(
                                    "-"
                                )[3]

                                response = requests.get(
                                    file["url_private"],
                                    headers={
                                        "Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}"
                                    },
                                    params={"pub_secret": pub_secret},
                                )

                                # Revoke public access
                                try:
                                    slack_web_client.files_revokePublicURL(
                                        file=file["id"],
                                        token=settings.SLACK_USER_TOKEN,
                                    )
                                except SlackApiError as error:
                                    logger.exception(
                                        "error revoking public url for pinned file", error=error
                                    )

                                try:
                                    result = EventLogHandler.create(
                                        image=response.content,
                                        incident_id=incident.id,
                                        incident_slug=incident.slug,
                                        message_ts=message["ts"],
                                        mimetype=file["mimetype"],
                                        title=file["name"],
                                        source="pin",
                                        user=get_slack_user(
                                            message.get("user")
                                        ).get("real_name", "NotAvailable"),
                                    )

                                    slack_web_client.reactions_add(
                                        channel=channel_id,
                                        name="white_check_mark",
                                        timestamp=message_timestamp,
                                    )
                                except Exception as error:
                                    if "already_reacted" in str(error):
                                        reason = "It looks like I've already pinned that content."
                                    else:
                                        reason = (
                                            f"Something went wrong: {error}"
                                        )
                                    say(
                                        channel=channel_id,
                                        text=f":wave: I was unable to pin that message. {reason}",
                                    )
                            else:
                                say(
                                    channel=channel_id,
                                    text=":wave: It looks like that's not an image. I can currently only attach images.",
                                )
                    else:
                        say(
                            channel=channel_id,
                            text=":wave: Attaching images is currently disabled.",
                        )
                else:
                    try:
                        # Parse elements in message text

                        result = EventLogHandler.create(
                            event=parse_pinned_message_content(
                                message["text"]
                            ),
                            incident_id=incident.id,
                            incident_slug=incident.slug,
                            message_ts=message["ts"],
                            source="pin",
                            user=get_slack_user(message.get("user")).get(
                                "real_name", "NotAvailable"
                            ),
                        )

                        slack_web_client.reactions_add(
                            channel=channel_id,
                            name="white_check_mark",
                            timestamp=message_timestamp,
                        )
                    except Exception as error:
                        if "already_reacted" in str(error):
                            reason = "It looks like I've already pinned that content."
                        else:
                            reason = f"Something went wrong: {error}"

                        say(
                            channel=channel_id,
                            text=f":wave: I was unable to pin that message. {reason}",
                        )
            except Exception as error:
                logger.exception(
                    "error when trying to retrieve a message", error=error
                )


def parse_pinned_message_content(message: str) -> str:
    """
    Replace components in pinned message

    Args:
        message (str): The message content to parse
    """

    channel_pattern = r"<#([A-Z0-9]+)\|?.*?>"
    url_patterns = [
        r"<(https?://[^|]+)\|([^>]+)>",
        r"<(https?://[^|]+)>",
    ]
    username_pattern = r"<@([A-Z0-9]+)>"

    if re.search(channel_pattern, message):
        with Session(engine) as session:
            match = re.search(channel_pattern, message)
            channel_list = session.exec(
                select(ApplicationData).filter(
                    ApplicationData.name == "slack_channels"
                )
            ).one()
            matched_channels = [
                channel
                for channel in channel_list.json_data
                if channel.get("id") == match.group(1)
            ]
            if matched_channels:
                matched_channel = matched_channels[0]
                message = message.replace(
                    match.group(0),
                    f"#{matched_channel.get("name")}",
                )
            else:
                # Keep original format if channel not found
                pass

    for pattern in url_patterns:
        if re.search(pattern, message):
            with Session(engine) as session:
                match = re.search(pattern, message)
                message = message.replace(
                    match.group(0),
                    match.group(1),
                )

    if re.search(username_pattern, message):
        with Session(engine) as session:
            match = re.search(username_pattern, message)
            user_list = session.exec(
                select(ApplicationData).filter(
                    ApplicationData.name == "slack_users"
                )
            ).one()
            matched_users = [
                user
                for user in user_list.json_data
                if user.get("id") == match.group(1)
            ]
            if matched_users:
                matched_user = matched_users[0]
                message = message.replace(
                    match.group(0),
                    f"@{matched_user.get("real_name")}",
                )
            else:
                # Keep original format if user not found
                pass

    return message


"""
Jira
"""


@app.action("jira.description_input")
def handle_static_action(ack, body, logger):  # noqa: F811
    logger.debug(body)
    ack()


@app.action("jira.priority_select")
def handle_static_action(ack, body):  # noqa: F811
    logger.debug(body)
    ack()


@app.action("jira.summary_input")
def handle_static_action(ack, body):  # noqa: F811
    logger.debug(body)
    ack()


@app.action("jira.type_select")
def handle_static_action(ack, body):  # noqa: F811
    logger.debug(body)
    ack()


@app.action("jira.view_issue")
def handle_static_action(ack, body):  # noqa: F811
    logger.debug(body)
    ack()


"""
Gitlab
"""


@app.action("gitlab.description_input")
def handle_static_action(ack, body, logger):  # noqa: F811
    logger.debug(body)
    ack()


@app.action("gitlab.priority_select")
def handle_static_action(ack, body):  # noqa: F811
    logger.debug(body)
    ack()


@app.action("gitlab.summary_input")
def handle_static_action(ack, body):  # noqa: F811
    logger.debug(body)
    ack()


@app.action("gitlab.type_select")
def handle_static_action(ack, body):  # noqa: F811
    logger.debug(body)
    ack()


@app.action("gitlab.view_issue")
def handle_static_action(ack, body):  # noqa: F811
    logger.debug(body)
    ack()


"""
Statuspage
"""


@app.action("statuspage.components_select")
def handle_static_action(ack, body):  # noqa: F811
    logger.debug(body)
    ack()


@app.action("statuspage.components_status_select")
def handle_static_action(ack, body, logger):  # noqa: F811
    logger.debug(body)
    ack()


@app.action("statuspage.impact_select")
def handle_static_action(ack, body):  # noqa: F811
    logger.debug(body)
    ack()


@app.action("phare.impact_select")
def handle_static_action(ack, body):  # noqa: F811
    logger.debug(body)
    ack()


@app.action("phare.monitors_select")
def handle_static_action(ack, body):  # noqa: F811
    logger.debug(body)
    ack()


@app.action("phare.open")
def handle_static_action(ack, body):  # noqa: F811
    logger.debug(body)
    ack()


@app.action("phare.update_status")
def handle_static_action(ack, body):  # noqa: F811
    logger.debug(body)
    ack()


@app.action("phare.view_incident")
def handle_static_action(ack, body):  # noqa: F811
    logger.debug(body)
    ack()


@app.action("statuspage.open")
def handle_static_action(ack, body):  # noqa: F811
    logger.debug(body)
    ack()


@app.action("statuspage.update_status")
def handle_static_action(ack, body):  # noqa: F811
    logger.debug(body)
    ack()


@app.action("statuspage.view_incident")
def handle_static_action(ack, body):  # noqa: F811
    logger.debug(body)
    ack()


"""
Request handling
"""


@app.action("dismiss_message")
def handle_dismiss_message(ack, body):
    logger.debug(body)
    try:
        ack()
        slack_web_client.chat_delete(
            channel=body["channel"]["id"], ts=body["actions"][0]["value"]
        )
    except slack_sdk.errors.SlackApiError as error:
        logger.exception("error deleting message", error=error)


@app.action("view_postmortem")
def handle_static_action(ack, body, logger):  # noqa: F811
    logger.debug(body)
    ack()


@app.action("incident.join_meeting")
def handle_static_action(ack, body, logger):  # noqa: F811
    logger.debug(body)
    ack()


@app.action("incident.sync_postmortem")
def handle_sync_postmortem(ack, body):
    ack()
    parsed_body = SlackBlockActionsResponse(**body)
    channel_id = parsed_body.channel.id
    user_id = parsed_body.user.id

    if not begin_postmortem_sync(channel_id):
        slack_web_client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text="Pinned-content sync is already in progress for this incident.",
        )
        return

    slack_web_client.chat_postEphemeral(
        channel=channel_id,
        user=user_id,
        text="Pinned-content sync has started. This can take a minute.",
    )

    try:
        asyncio.run(sync_postmortem(channel_id=channel_id))
    finally:
        end_postmortem_sync(channel_id)


@app.action("incident.sync_postmortem.disabled")
def handle_sync_postmortem_disabled(ack, body):
    ack()
    parsed_body = SlackBlockActionsResponse(**body)
    slack_web_client.chat_postEphemeral(
        channel=parsed_body.channel.id,
        user=parsed_body.user.id,
        text="Pinned-content sync is not available for this incident.",
    )
