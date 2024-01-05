import asyncio
import config
import requests
import slack_sdk

from bot.exc import ConfigurationError
from bot.incident import actions as inc_actions, incident
from bot.incident.action_parameters import ActionParametersSlack
from bot.models.incident import db_read_recent_incidents
from bot.models.pager import read_pager_auto_page_targets
from bot.scheduler import scheduler
from bot.shared import tools
from bot.slack.client import (
    get_digest_channel_id,
    get_user_name,
    slack_web_client,
    slack_workspace_id,
)
from bot.slack.helpers import DigestMessageTracking
from bot.slack.incident_logging import write as write_content
from bot.slack.messages import (
    help_menu,
    incident_list_message,
    job_list_message,
)
from iblog import logger
from slack_bolt import App
from slack_sdk.errors import SlackApiError
from typing import Any, Dict


## The xoxb oauth token for the bot is called here to provide bot privileges.
app = App(token=config.slack_bot_token)
enabled_chatter_message = config.slack_chatter_message_enabled

@app.error
def custom_error_handler(error, body, logger):
    logger.exception(f"Error: {error}")
    logger.debug(f"Request body: {body}")


from . import modals

tracking = DigestMessageTracking()

"""
Handle Mentions
"""


@app.event("app_mention")
def handle_mention(body, say, logger):
    message = body.get("event").get("text").split(" ")
    user = body["event"]["user"]
    logger.debug(body)

    if len(message) == 1:
        # This is just a user mention and the bot shouldn't really do anything.
        return

    match message[1]:
        case "help":
            say(blocks=help_menu(), text="")
        case "diag":
            startup_message = config.startup_message(
                workspace=slack_workspace_id, wrap=True
            )
            say(channel=user, text=startup_message)
        case "lsoi":
            database_data = db_read_recent_incidents(
                limit=config.show_most_recent_incidents_app_home_limit
            )
            resp = incident_list_message(database_data, all=False)
            say(blocks=resp, text="")
        case "pager":
            if "pagerduty" in config.active.integrations:
                from bot.pagerduty import api as pd_api

                pd_oncall_data = pd_api.find_who_is_on_call()
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
                        ]
                    )

                    # Iterate over schedules
                    if pd_oncall_data is not {}:
                        # Get length of returned objects
                        # If returned objects is greater than 5, paginate over them 5 at a time and include 5 in each message
                        # Send a separate message for each grouping of 5 to avoid block limits from the Slack API
                        for page in tools.paginate_dictionary(
                            pd_oncall_data.items(),
                            config.slack_items_pagination_per_page,
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
                                        "block_id": "ping_oncall_{}".format(
                                            tools.random_string_generator()
                                        ),
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
                            say(blocks=base_block, text="")
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
                                        "image_url": pd_api.image_url,
                                        "alt_text": "pagerduty",
                                    },
                                    {
                                        "type": "mrkdwn",
                                        "text": f"This information is sourced from PagerDuty and is accurate as of {tools.fetch_timestamp()}.",
                                    },
                                ],
                            }
                        ]
                    )
            elif config.active.integrations.get(
                "atlassian"
            ) and config.active.integrations.get("atlassian").get("opsgenie"):
                from bot.opsgenie import api as og_api

                sess = og_api.OpsgenieAPI()
                og_oncall_data = sess.list_rotations()

                if og_oncall_data:
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
                        ]
                    )

                    base_block = []

                    # Iterate over schedules
                    for item in og_oncall_data:
                        options = []
                        for user in item.get("participants"):
                            options.append(
                                {
                                    "text": {
                                        "type": "plain_text",
                                        "text": user.get("username"),
                                    },
                                    "value": user.get("username"),
                                },
                            )
                        base_block.append(
                            {
                                "type": "section",
                                "block_id": "ping_oncall_{}".format(
                                    tools.random_string_generator()
                                ),
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"*{item.get('name')}*",
                                },
                                "accessory": {
                                    "type": "overflow",
                                    "options": options,
                                    "action_id": "incident.add_on_call_to_channel",
                                },
                            }
                        )
                    say(blocks=base_block, text="")
                else:
                    say(
                        text="No data regarding schedule rotations was returned from Opsgnie."
                    )

                # Footer
                say(
                    blocks=[
                        {
                            "type": "context",
                            "elements": [
                                {
                                    "type": "image",
                                    "image_url": og_api.image_url,
                                    "alt_text": "opsgenie",
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"This information is sourced from Opsgenie and is accurate as of {tools.fetch_timestamp()}.",
                                },
                            ],
                        }
                    ]
                )
            else:
                say(
                    text="No upstream platform configurations are present. I cannot provide information as a result."
                )
        case "scheduler":
            match message[2]:
                case "list":
                    jobs = scheduler.process.list_jobs()
                    resp = job_list_message(jobs)
                    say(blocks=resp, text="")
                case "delete":
                    if len(message) < 4:
                        say(text="Please provide the ID of a job to delete.")
                    else:
                        job_title = message[3]
                        delete_job = scheduler.process.delete_job(job_title)
                        if delete_job != None:
                            say(
                                f"Could not delete the job {job_title}: {delete_job}"
                            )
                        else:
                            say(f"Deleted job: *{job_title}*")
        case "ping":
            say(text="pong")
        case "version":
            say(text=f"I am currently running version: {config.__version__}")
        case default:
            resp = " ".join(message[1:])
            say(text=f"Sorry, I don't know the command *{resp}* yet.")


"""
Incident Management Actions
"""


def parse_action(body) -> Dict[str, Any]:
    return ActionParametersSlack(
        payload={
            "actions": body["actions"],
            "channel": body["channel"],
            "message": body["message"],
            "state": body["state"],
            "user": body["user"],
        }
    )


@app.action("incident.export_chat_logs")
def handle_incident_export_chat_logs(ack, body):
    logger.debug(body)
    ack()
    asyncio.run(
        inc_actions.export_chat_logs(action_parameters=parse_action(body))
    )


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
    asyncio.run(
        inc_actions.archive_incident_channel(
            action_parameters=parse_action(body)
        )
    )


@app.action("incident.assign_role")
def handle_incident_assign_role(ack, body):
    logger.debug(body)
    ack()
    asyncio.run(inc_actions.assign_role(action_parameters=parse_action(body)))


@app.action("incident.claim_role")
def handle_incident_claim_role(ack, body):
    logger.debug(body)
    ack()
    asyncio.run(inc_actions.claim_role(action_parameters=parse_action(body)))


@app.action("incident.set_status")
def handle_incident_set_status(ack, body):
    logger.debug(body)
    ack()
    asyncio.run(inc_actions.set_status(action_parameters=parse_action(body)))


@app.action("incident.set_severity")
def handle_incident_set_severity(ack, body):
    logger.debug(body)
    ack()
    asyncio.run(inc_actions.set_severity(action_parameters=parse_action(body)))


"""
Reactions
"""


@app.event("reaction_added")
def reaction_added(event, say):
    emoji = event["reaction"]
    channel_id = event["item"]["channel"]
    ts = event["item"]["ts"]
    # Automatically create incident based on reaction with specific emoji
    if emoji == config.active.options.get("create_from_reaction").get(
        "reacji"
    ) and config.active.options.get("create_from_reaction").get("enabled"):
        # Retrieve the content of the message that was reacted to
        try:
            result = slack_web_client.conversations_history(
                channel=channel_id, inclusive=True, oldest=ts, limit=1
            )
            message = result["messages"][0]
            message_reacted_to_content = message["text"]
        except Exception as error:
            logger.error(f"Error when trying to retrieve a message: {error}")
        # Create request parameters object
        try:
            request_parameters = incident.RequestParameters(
                channel=channel_id,
                incident_description=f"auto-{tools.random_suffix}",
                user="internal_auto_create",
                severity="sev4",
                message_reacted_to_content=message_reacted_to_content,
                original_message_timestamp=ts,
                is_security_incident=False,
                private_channel=False,
            )
        except ConfigurationError as error:
            logger.error(error)
        # Create an incident based on the message using the internal path
        try:
            incident.create_incident(
                internal=True, request_parameters=request_parameters
            )
        except Exception as error:
            logger.error(f"Error when trying to create an incident: {error}")
    # Pinned content for incidents
    if emoji == "pushpin":
        channel_info = slack_web_client.conversations_info(channel=channel_id)

        prefix = config.default_incident_channel_name_prefix
        if config.active.options.get("channel_naming"):
            if config.active.options.get("channel_naming").get(
                "channel_name_prefix"
            ):
                prefix = config.active.options.get("channel_naming").get(
                    "channel_name_prefix"
                )

        if f"{prefix}-" in channel_info["channel"]["name"]:
            # Retrieve the content of the message that was reacted to
            try:
                result = slack_web_client.conversations_history(
                    channel=channel_id, inclusive=True, oldest=ts, limit=1
                )
                message = result["messages"][0]
                if "files" in message:
                    for file in message["files"]:
                        if "image" in file["mimetype"]:
                            if not file["public_url_shared"]:
                                # Make the attachment public temporarily
                                try:
                                    slack_web_client.files_sharedPublicURL(
                                        file=file["id"],
                                        token=config.slack_user_token,
                                    )
                                except SlackApiError as error:
                                    logger.error(
                                        f"Error preparing pinned file for copy: {error}"
                                    )
                            # Copy the attachment into the database
                            pub_secret = file["permalink_public"].split("-")[3]
                            res = requests.get(
                                file["url_private"],
                                headers={
                                    "Authorization": f"Bearer {config.slack_bot_token}"
                                },
                                params={"pub_secret": pub_secret},
                            )
                            write_content(
                                incident_id=channel_info["channel"]["name"],
                                title=file["name"],
                                img=res.content,
                                mimetype=file["mimetype"],
                                ts=tools.fetch_timestamp(short=True),
                                user=get_user_name(user_id=message["user"]),
                            )
                            # Revoke public access
                            try:
                                slack_web_client.files_revokePublicURL(
                                    file=file["id"],
                                    token=config.slack_user_token,
                                )
                            except SlackApiError as error:
                                logger.error(
                                    f"Error preparing pinned file for copy: {error}"
                                )
                        else:
                            say(
                                channel=channel_id,
                                text=f":wave: Hey there! It looks like that's not an image. I can currently only attach images.",
                            )
                else:
                    write_content(
                        incident_id=channel_info["channel"]["name"],
                        content=message["text"],
                        ts=tools.fetch_timestamp(short=True),
                        user=get_user_name(user_id=message["user"]),
                    )
            except Exception as error:
                logger.error(
                    f"Error when trying to retrieve a message: {error}"
                )
            finally:
                try:
                    slack_web_client.reactions_add(
                        channel=channel_id,
                        name="white_check_mark",
                        timestamp=ts,
                    )
                except Exception as error:
                    if "already_reacted" in str(error):
                        reason = (
                            "It looks like I've already pinned that content."
                        )
                    else:
                        reason = f"Something went wrong: {error}"
                    say(
                        channel=channel_id,
                        text=f":wave: Hey there! I was unable to pin that message. {reason}",
                    )


"""
Helper Functions
"""


@app.event("message")
def handle_message_events(body, logger):
    logger.debug(body)
    """
    Handle monitoring digest channel
    """
    if (
        # The presence of subtype indicates events like message updates, etc.
        # We don't want to act on these.
        body["event"]["channel"] == get_digest_channel_id()
        and not "subtype" in body["event"].keys()
        and enabled_chatter_message == "true"
    ):
        tracking.incr()
        if tracking.calls > 3:
            try:
                result = slack_web_client.chat_postMessage(
                    channel=body["event"]["channel"],
                    blocks=[
                        {
                            "block_id": "chatter_help_message",
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": ":wave: Hey there! I've noticed there's some conversation happening in this channel and that there are no active incidents. "
                                + "You can always start an incident and use it to investigate. In fact, all incidents start off as investigations! "
                                + "You can always mark things as resolved if there are no actual issues.",
                            },
                        },
                        {"type": "divider"},
                        {
                            "type": "actions",
                            "block_id": "chat_help_message_buttons",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {
                                        "type": "plain_text",
                                        "text": "Start New Incident",
                                        "emoji": True,
                                    },
                                    "value": "show_incident_modal",
                                    "action_id": "open_incident_modal",
                                    "style": "danger",
                                },
                                {
                                    "type": "button",
                                    "text": {
                                        "type": "plain_text",
                                        "text": "Dismiss",
                                        "emoji": True,
                                    },
                                    "value": "placeholder",
                                    "action_id": "dismiss_message",
                                },
                            ],
                        },
                    ],
                )
                tracking.reset()
                tracking.set_message_ts(message_ts=result["message"]["ts"])
                # Retrieve the sent message
                sent_message = slack_web_client.conversations_history(
                    channel=body["event"]["channel"],
                    inclusive=True,
                    oldest=result["message"]["ts"],
                    limit=1,
                )
                # Update the sent message with its own timestamp
                existing_blocks = sent_message["messages"][0]["blocks"]
                existing_blocks[2]["elements"][1]["value"] = result["message"][
                    "ts"
                ]
                try:
                    slack_web_client.chat_update(
                        channel=body["event"]["channel"],
                        ts=result["message"]["ts"],
                        blocks=existing_blocks,
                        text="",
                    )
                except slack_sdk.errors.SlackApiError as error:
                    logger.error(f"Error updating message: {error}")
            except slack_sdk.errors.SlackApiError as error:
                logger.error(
                    f"Error sending help message to incident channel during increased chatter: {error}"
                )


"""
Statuspage
"""


@app.action("statuspage.components_select")
def handle_static_action(ack, body):
    logger.debug(body)
    ack()


@app.action("statuspage.components_status_select")
def handle_static_action(ack, body, logger):
    logger.debug(body)
    ack()


@app.action("statuspage.impact_select")
def handle_static_action(ack, body):
    logger.debug(body)
    ack()


@app.action("statuspage.open_statuspage")
def handle_static_action(ack, body):
    logger.debug(body)
    ack()


@app.action("statuspage.update_status")
def handle_static_action(ack, body):
    logger.debug(body)
    ack()


@app.action("statuspage.view_incident")
def handle_static_action(ack, body):
    logger.debug(body)
    ack()


"""
Jira
"""


@app.action("jira.description_input")
def handle_static_action(ack, body, logger):
    logger.debug(body)
    ack()


@app.action("jira.priority_select")
def handle_static_action(ack, body):
    logger.debug(body)
    ack()


@app.action("jira.summary_input")
def handle_static_action(ack, body):
    logger.debug(body)
    ack()


@app.action("jira.type_select")
def handle_static_action(ack, body):
    logger.debug(body)
    ack()


@app.action("jira.view_issue")
def handle_static_action(ack, body):
    logger.debug(body)
    ack()


"""
Logs for request handling various other requests
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
        logger.error(f"Error deleting message: {error}")


@app.action("incident.incident_postmortem_link")
def handle_static_action(ack, body, logger):
    logger.debug(body)
    ack()


@app.action("incident.click_conference_bridge_link")
def handle_static_action(ack, body, logger):
    logger.debug(body)
    ack()


@app.action("incident.incident_guide_link")
def handle_static_action(ack, body, logger):
    logger.debug(body)
    ack()


@app.action("incident.join_incident_channel")
def handle_static_action(ack, body, logger):
    logger.debug(body)
    ack()


@app.action("external.reload")
def handle_static_action(ack, body, logger):
    logger.debug(body)
    ack()


@app.action("external.view_status_page")
def handle_static_action(ack, body, logger):
    logger.debug(body)
    ack()


@app.action("incident_update_modal_select_incident")
def handle_static_action(ack, body, logger):
    logger.debug(body)
    ack()


@app.action("open_rca")
def handle_static_action(ack, body, logger):
    logger.debug(body)
    ack()


@app.action("open_incident_modal_set_severity")
def handle_static_action(ack, body, logger):
    logger.debug(body)
    ack()


@app.action("open_incident_modal_set_security_type")
def handle_static_action(ack, body, logger):
    logger.debug(body)
    ack()

    if body.get("actions")[0].get("selected_option").get("value") in (
        "True",
        "true",
        True,
    ):
        try:
            placeholder_severity = [
                sev for sev, _ in config.active.severities.items()
            ][-1]

            base_blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "This will start a new incident channel and you will "
                        + "be invited to it. From there, please use our incident "
                        + "management process to run the incident or coordinate "
                        + "with others to do so.",
                    },
                },
                {
                    "type": "section",
                    "block_id": "is_security_incident",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Is this a security incident?*",
                    },
                    "accessory": {
                        "action_id": "open_incident_modal_set_security_type",
                        "type": "static_select",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Yes",
                        },
                        "initial_option": {
                            "text": {
                                "type": "plain_text",
                                "text": "Yes",
                            },
                            "value": "true",
                        },
                        "options": [
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "Yes",
                                },
                                "value": "true",
                            },
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "No",
                                },
                                "value": "false",
                            },
                        ],
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": ":lock: *Security incident channels will be created as private channels.*",
                    },
                },
                {
                    "type": "input",
                    "block_id": "open_incident_modal_desc",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "open_incident_modal_set_description",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "A brief description of the problem.",
                        },
                    },
                    "label": {"type": "plain_text", "text": "Description"},
                },
                {
                    "block_id": "severity",
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "*Severity*"},
                    "accessory": {
                        "type": "static_select",
                        "action_id": "open_incident_modal_set_severity",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Select a severity...",
                            "emoji": True,
                        },
                        "initial_option": {
                            "text": {
                                "type": "plain_text",
                                "text": placeholder_severity.upper(),
                            },
                            "value": placeholder_severity,
                        },
                        "options": [
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": sev.upper(),
                                    "emoji": True,
                                },
                                "value": sev,
                            }
                            for sev, _ in config.active.severities.items()
                        ],
                    },
                },
            ]

            """
            If there are teams that will be auto paged, mention that
            """
            if "pagerduty" in config.active.integrations:
                auto_page_targets = read_pager_auto_page_targets()
                if len(auto_page_targets) != 0:
                    base_blocks.extend(
                        [
                            {"type": "divider"},
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": ":point_right: *The following teams will "
                                    + "be automatically paged when this incident is created:*",
                                },
                            },
                        ]
                    )
                    for i in auto_page_targets:
                        for k, v in i.items():
                            base_blocks.extend(
                                [
                                    {
                                        "type": "section",
                                        "text": {
                                            "type": "mrkdwn",
                                            "text": f"_{k}_",
                                        },
                                    },
                                ]
                            )

            slack_web_client.views_update(
                # Pass the view_id
                view_id=body["view"]["id"],
                # String that represents view state to protect against race conditions
                hash=body["view"]["hash"],
                # View payload with updated blocks
                view={
                    "type": "modal",
                    "callback_id": "open_incident_modal",
                    "title": {
                        "type": "plain_text",
                        "text": "Start a new incident",
                    },
                    "submit": {"type": "plain_text", "text": "Start"},
                    "blocks": base_blocks,
                },
            )
        except slack_sdk.errors.SlackApiError as error:
            logger.error(f"Error deleting message: {error}")


@app.action("open_incident_modal_set_private")
def handle_static_action(ack, body, logger):
    logger.debug(body)
    ack()


@app.action("view_statuspage_incident")
def handle_static_action(ack, body, logger):
    logger.debug(body)
    ack()
