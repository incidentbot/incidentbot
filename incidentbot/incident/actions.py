import datetime

from incidentbot.configuration.settings import settings
from incidentbot.exceptions import IndexNotFoundError
from incidentbot.incident.core import format_channel_name
from incidentbot.incident.event import EventLogHandler
from incidentbot.scheduler.core import process as TaskScheduler
from incidentbot.logging import logger
from incidentbot.models.incident import IncidentDatabaseInterface
from incidentbot.models.slack import User
from incidentbot.slack.client import (
    get_digest_channel_id,
    get_formatted_channel_history,
    slack_web_client,
)
from incidentbot.slack.messages import (
    BlockBuilder,
    IncidentChannelDigestNotification,
    IncidentUpdate,
)
from incidentbot.util import gen
from slack_sdk.errors import SlackApiError

err_msg = ":robot_face::heart_on_fire: I've run into a problem processing commands for this incident: I cannot find it in the database. Let an administrator know about this error."

"""
Functions for handling inbound actions
"""


async def archive_incident_channel(
    channel_id: str,
):
    """
    Archives the channel passed in based on its channel_id

    Parameters:
        channel_id (str): Incident channel_id
    """

    incident = IncidentDatabaseInterface.get_one(channel_id=channel_id)

    if incident:
        try:
            logger.info(f"Archiving {incident.channel_name}.")
            result = slack_web_client.conversations_archive(
                channel=incident.channel_id
            )
            logger.debug(result)
        except SlackApiError as error:
            logger.error(f"Error archiving {incident.channel_name}: {error}")
        finally:
            # Write event log
            EventLogHandler.create(
                event="The incident channel was archived",
                incident_id=incident.id,
                incident_slug=incident.slug,
                source="system",
            )
    else:
        slack_web_client.chat_postMessage(
            channel=channel_id,
            text=err_msg,
        )


async def export_chat_logs(channel_id: str, user: str):
    """
    Fetches channel history, formats it, and returns it to the channel

    Parameters:
        channel_id (str): Incident channel_id
        user (str): The user who exported the logs
    """

    incident = IncidentDatabaseInterface.get_one(channel_id=channel_id)

    if incident:
        # Retrieve channel history and post as text attachment
        history = get_formatted_channel_history(
            channel_id=incident.channel_id,
            channel_name=incident.channel_name,
        )
        try:
            logger.info(f"Sending chat transcript to {incident.channel_name}.")
            result = slack_web_client.files_upload_v2(
                channel=incident.channel_id,
                content=history,
                filename=f"{incident.channel_name} Chat Transcript.txt",
                initial_comment="As requested, here is the chat transcript. Remember"
                + " - while this is useful, it will likely need cultivation before "
                + "being added to a postmortem.",
                title=f"{incident.channel_name} Chat Transcript",
            )
            logger.debug(f"\n{result}\n")
        except SlackApiError as error:
            logger.error(
                f"Error sending message and attachment to {incident.channel_name}: {error}"
            )
        finally:
            # Write event log
            EventLogHandler.create(
                event=f"Incident channel text log was exported by {user}",
                incident_id=incident.id,
                incident_slug=incident.slug,
                source="system",
            )
    else:
        slack_web_client.chat_postMessage(
            channel=channel_id,
            text=err_msg,
        )


async def join_incident_as_role(
    channel_id: str,
    role: str,
    user: User,
):
    """
    Parameters:
        channel_id (str): Incident channel_id
        role (str): The role being claimed
        user (incidentbot.models.slack.User): User object from the Slack response
    """

    incident = IncidentDatabaseInterface.get_one(channel_id=channel_id)

    # Verify the role is valid
    try:
        role_definition = settings.roles.get(role)
    except Exception:
        logger.error(f"role {role} isn't valid")
        return

    if incident:
        role_normalized = role.replace("_", " ").title()

        # Check whether or not the user has already claimed the role
        assigned = IncidentDatabaseInterface.check_role_assigned_to_user(
            incident=incident, role=role, user=user
        )
        if assigned:
            try:
                slack_web_client.chat_postEphemeral(
                    channel=channel_id,
                    user=user.id,
                    text=f"You have already joined this incident as *{role_normalized}*.",
                )

                return
            except SlackApiError as error:
                logger.error(
                    f"error sending message back to user via slash command invocation: {error}"
                )

        # Send update notification message to incident channel
        try:
            result = slack_web_client.chat_postMessage(
                **IncidentUpdate.role(
                    action="joined",
                    channel=incident.channel_id,
                    role=role_normalized,
                    user=user.id,
                ),
                text=f"<@{user}> has joined this incident as *{role_normalized}*.",
            )
            logger.debug(f"\n{result}\n")
        except SlackApiError as error:
            logger.error(
                f"Error sending role update to incident channel: {error}"
            )

        # Provide the user with information regarding the role
        try:
            slack_web_client.chat_postEphemeral(
                channel=channel_id,
                user=user.id,
                text="You have joined this incident as {}. {}".format(
                    role_normalized,
                    settings.roles.get(role).description,
                ),
            )
        except SlackApiError as error:
            logger.error(
                f"error sending message back to user via slash command invocation: {error}"
            )

        # Update topic if lead role
        if role_definition.is_lead:
            # Get current topic
            try:
                current_topic = [
                    item.strip()
                    for item in slack_web_client.conversations_info(
                        channel=incident.channel_id,
                    )
                    .get("channel")
                    .get("topic")
                    .get("value")
                    .split("|")
                ]
            except SlackApiError as error:
                logger.error(f"error getting channel info: {error}")

            # Update topic
            # Severity is always index 0
            # Status is always index 1
            try:
                slack_web_client.conversations_setTopic(
                    channel=incident.channel_id,
                    topic=f"{current_topic[0]} | {current_topic[1]} | {role_normalized}: <@{user.id}>",
                )
            except SlackApiError as error:
                logger.error(f"Error setting incident channel topic: {error}")

        # Create record
        IncidentDatabaseInterface.associate_role(
            incident=incident,
            is_lead=role_definition.is_lead,
            role=role,
            user=user,
        )

        # Write event log
        EventLogHandler.create(
            event=f"{user.name} joined the incident as {role_normalized}",
            incident_id=incident.id,
            incident_slug=incident.slug,
            source="system",
        )
    else:
        slack_web_client.chat_postMessage(
            channel=channel_id,
            text=err_msg,
        )


async def leave_incident_as_role(
    channel_id: str,
    role: str,
    user: User,
):
    """
    Parameters:
        channel_id (str): Incident channel_id
        role (str): The role being forfeited
        user (incidentbot.models.slack.User): User object from the Slack response
    """

    incident = IncidentDatabaseInterface.get_one(channel_id=channel_id)

    # Verify the role is valid
    try:
        role_definition = settings.roles.get(role)
    except Exception:
        logger.error(f"role {role} isn't valid")
        return

    if incident:
        role_normalized = role.replace("_", " ").title()

        # Check whether or not the user has claimed the role
        assigned = IncidentDatabaseInterface.check_role_assigned_to_user(
            incident=incident, role=role, user=user
        )
        if assigned:
            pass
        else:
            logger.error("user is not assigned that role")
            return

        # Send update notification message to incident channel
        try:
            result = slack_web_client.chat_postMessage(
                **IncidentUpdate.role(
                    action="left",
                    channel=incident.channel_id,
                    role=role_normalized,
                    user=user.id,
                ),
                text=f"<@{user}> is no longer *{role_normalized}* for this incident.",
            )
            logger.debug(f"\n{result}\n")
        except SlackApiError as error:
            logger.error(
                f"Error sending role update to incident channel: {error}"
            )

        # Notify the user
        try:
            slack_web_client.chat_postEphemeral(
                channel=channel_id,
                user=user.id,
                text="You are no longer {}.".format(
                    role_normalized,
                ),
            )
        except SlackApiError as error:
            logger.error(
                f"error sending message back to user via slash command invocation: {error}"
            )

        # Update topic if lead role
        if role_definition.is_lead:
            # Get current topic
            try:
                current_topic = [
                    item.strip()
                    for item in slack_web_client.conversations_info(
                        channel=incident.channel_id,
                    )
                    .get("channel")
                    .get("topic")
                    .get("value")
                    .split("|")
                ]
            except SlackApiError as error:
                logger.error(f"error getting channel info: {error}")

            # Update topic
            # Severity is always index 0
            # Status is always index 1
            try:
                slack_web_client.conversations_setTopic(
                    channel=incident.channel_id,
                    topic=f"{current_topic[0]} | {current_topic[1]}",
                )
            except SlackApiError as error:
                logger.error(f"Error setting incident channel topic: {error}")

        # Delete record
        IncidentDatabaseInterface.remove_role(
            incident=incident,
            role=role,
            user=user,
        )

        # Write event log
        EventLogHandler.create(
            event=f"{user.name} left the incident as {role_normalized}",
            incident_id=incident.id,
            incident_slug=incident.slug,
            source="system",
        )
    else:
        slack_web_client.chat_postMessage(
            channel=channel_id,
            text=err_msg,
        )


async def set_description(channel_id: str, description: str, user: str = None):
    """
    Parameters:
        channel_id (str): Incident channel_id
        description (str): The description value
    """

    incident = IncidentDatabaseInterface.get_one(channel_id=channel_id)

    if incident:
        # Update digest message
        try:
            slack_web_client.chat_update(
                channel=get_digest_channel_id(),
                ts=incident.digest_message_ts,
                blocks=IncidentChannelDigestNotification.update(
                    channel_id=incident.channel_id,
                    has_private_channel=incident.has_private_channel,
                    incident_components=incident.components,
                    incident_description=description,
                    incident_impact=incident.impact,
                    incident_slug=incident.slug,
                    meeting_link=incident.meeting_link,
                    severity=incident.severity,
                    status=incident.status,
                ),
                text="Digest message has been updated.",
            )
        except SlackApiError as error:
            logger.error(
                f"Error during description update for incident channel {incident.channel_name}: {error}"
            )
            return

        # Update boilerplate message
        result = slack_web_client.conversations_history(
            channel=incident.channel_id,
            inclusive=True,
            oldest=incident.boilerplate_message_ts,
            limit=1,
        )
        blocks = result["messages"][0]["blocks"]
        description_block_index = gen.find_index_in_list(
            blocks, "block_id", "digest_channel_description"
        )
        if description_block_index == -1:
            raise IndexNotFoundError(
                "Could not find index for block_id severity"
            )

        blocks[description_block_index]["text"][
            "text"
        ] = f":mag_right: *Description:* {description}"

        slack_web_client.chat_update(
            channel=incident.channel_id,
            ts=incident.boilerplate_message_ts,
            blocks=blocks,
            text="This incident's description has been updated.",
        )

        # Notify channel
        notification_suffix = (
            f"{description} by {user}" if user else f"{description}"
        )
        slack_web_client.chat_postMessage(
            channel=channel_id,
            text=f"The description of this incident has been updated to {notification_suffix}.",
        )

        # If that all worked, change the channel name
        new_channel_name = format_channel_name(
            id=incident.id,
            description=description,
            use_date_prefix=settings.options.channel_name_use_date_prefix,
        )
        try:
            slack_web_client.conversations_rename(
                channel=channel_id, name=new_channel_name
            )
        except SlackApiError as error:
            logger.error(
                f"Error renaming channel for {incident.channel_name} (rename it manually): {error}"
            )

        # Update database record
        try:
            IncidentDatabaseInterface.update_col(
                channel_id=incident.channel_id,
                col_name="channel_name",
                value=new_channel_name,
            )
            IncidentDatabaseInterface.update_col(
                channel_id=incident.channel_id,
                col_name="description",
                value=description,
            )
        except Exception as error:
            logger.fatal(f"Error updating entry in database: {error}")

        # Write event log
        EventLogHandler.create(
            event=f"The incident description was updated to {notification_suffix}",
            incident_id=incident.id,
            incident_slug=incident.slug,
            source="system",
        )

        logger.info(
            f"Updated incident description for {incident.channel_name}."
        )
    else:
        slack_web_client.chat_postMessage(
            channel=channel_id,
            text=err_msg,
        )


async def set_severity(channel_id: str, severity: str, user: User | str):
    """
    Parameters:
        channel_id (str): Incident channel_id
        severity (str): The severity value
        user (incidentbot.models.slack.User | str): User object from the Slack response, or api
    """

    incident = IncidentDatabaseInterface.get_one(channel_id=channel_id)

    if incident:
        if user != "api":
            # Check to see if the severity is already set to that value
            if incident.severity == severity:
                try:
                    slack_web_client.chat_postEphemeral(
                        channel=channel_id,
                        user=user.id,
                        text=f"The severity for this incident is already {severity.upper()}.",
                    )

                    return
                except SlackApiError as error:
                    logger.error(
                        f"error sending message back to user via slash command invocation: {error}"
                    )

        # Update gitlab ticket severity
        if (
            settings.integrations
            and settings.integrations.gitlab
            and settings.integrations.gitlab.enabled
            and settings.integrations.gitlab.severity_mapping
        ):
            from incidentbot.gitlab.api import GitLabApi

            gitlab = GitLabApi()
            gitlab.update_issue_severity(
                incident_name=incident.channel_name, incident_severity=severity
            )
            logger.info(
                f"Updated GitLab issue severity for {incident.channel_name} to {severity}"
            )

        # Update digest message
        try:
            slack_web_client.chat_update(
                channel=get_digest_channel_id(),
                ts=incident.digest_message_ts,
                blocks=IncidentChannelDigestNotification.update(
                    channel_id=incident.channel_id,
                    has_private_channel=incident.has_private_channel,
                    incident_components=incident.components,
                    incident_description=incident.description,
                    incident_impact=incident.impact,
                    incident_slug=incident.slug,
                    meeting_link=incident.meeting_link,
                    severity=severity,
                    status=incident.status,
                ),
                text="Digest message has been updated.",
            )
        except SlackApiError as error:
            logger.error(
                f"Error sending severity update to incident channel {incident.channel_name}: {error}"
            )

        # Channel notification
        try:
            result = slack_web_client.chat_postMessage(
                **IncidentUpdate.severity(
                    channel=incident.channel_id, severity=severity
                ),
                text=f"The incident severity has been changed to {severity}.",
            )
            logger.debug(f"\n{result}\n")
        except SlackApiError as error:
            logger.error(
                f"Error sending severity update to incident channel {incident.channel_name}: {error}"
            )

        # Get current topic
        try:
            current_topic = [
                item.strip()
                for item in slack_web_client.conversations_info(
                    channel=incident.channel_id,
                )
                .get("channel")
                .get("topic")
                .get("value")
                .split("|")
            ]
        except SlackApiError as error:
            logger.error(f"error getting channel info: {error}")

        # Update topic
        # Severity is always index 0
        # Status is always index 1
        # If commander is assigned, it's always index 2
        new_topic = f"Severity: {severity.upper()} | {current_topic[1]}"
        if len(current_topic) == 3:
            new_topic += f" | {current_topic[2]}"

        try:
            slack_web_client.conversations_setTopic(
                channel=incident.channel_id,
                topic=new_topic,
            )
        except SlackApiError as error:
            logger.error(f"Error setting incident channel topic: {error}")

        # Log
        logger.info(
            f"Updated incident severity for {incident.channel_name} to {severity}"
        )

        # Update incident record with new severity
        try:
            IncidentDatabaseInterface.update_col(
                channel_id=incident.channel_id,
                col_name="severity",
                value=severity,
            )
        except Exception as error:
            logger.fatal(f"Error updating entry in database: {error}")

        # Write event log
        EventLogHandler.create(
            event=f"The incident severity was changed to {severity.upper()}",
            incident_id=incident.id,
            incident_slug=incident.slug,
            source="system",
        )
    else:
        slack_web_client.chat_postMessage(
            channel=channel_id,
            text=err_msg,
        )


async def set_status(
    channel_id: str,
    status: str,
    user: User | str,
):
    """
    Parameters:
        channel_id (str): Incident channel_id
        status (str): The status value
        user (incidentbot.models.slack.User | str): User object from the Slack response, or api
    """

    incident = IncidentDatabaseInterface.get_one(channel_id=channel_id)

    if incident:
        if user != "api":
            # Check to see if the status is already set to that value
            if incident.status == status:
                try:
                    slack_web_client.chat_postEphemeral(
                        channel=channel_id,
                        user=user.id,
                        text=f"The status for this incident is already {status.title()}.",
                    )

                    return
                except SlackApiError as error:
                    logger.error(
                        f"error sending message back to user via slash command invocation: {error}"
                    )

        postmortem_link = None

        if (
            status
            == [
                status
                for status, config in settings.statuses.items()
                if config.final
            ][0]
        ):
            # First, make sure a postmortem doesn't already exist
            if not IncidentDatabaseInterface.get_postmortem(
                parent=incident.id,
            ):
                # Generate postmortem template and create postmortem if enabled
                # Get normalized description as postmortem title
                if (
                    settings.integrations
                    and settings.integrations.atlassian
                    and settings.integrations.atlassian.confluence
                    and settings.integrations.atlassian.confluence.enabled
                    and settings.integrations.atlassian.confluence.auto_create_postmortem
                ):
                    from incidentbot.confluence.postmortem import (
                        IncidentPostmortem,
                    )

                    postmortem = IncidentPostmortem(
                        incident=incident,
                        participants=IncidentDatabaseInterface.list_participants(
                            incident=incident
                        ),
                        timeline=EventLogHandler.read(incident_id=incident.id),
                        title=f"{datetime.datetime.today().strftime('%Y-%m-%d')} - {incident.slug.upper()} - {incident.description}",
                    )
                    postmortem_link = postmortem.create()

                    if postmortem_link:
                        # Create record
                        IncidentDatabaseInterface.add_postmortem(
                            parent=incident.id, url=postmortem_link
                        )

                        # Write event log
                        EventLogHandler.create(
                            event="Postmortem generated",
                            incident_id=incident.id,
                            incident_slug=incident.slug,
                            source="system",
                        )

                        postmortem_boilerplate_message_blocks = [
                            {
                                "type": "header",
                                "text": {
                                    "type": "plain_text",
                                    "text": "{} Incident Postmortem".format(
                                        settings.icons.get(
                                            settings.platform
                                        ).get("postmortem"),
                                    ),
                                },
                            },
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "A starter postmortem has been composed based on "
                                    + "data gathered during this incident.",
                                },
                            },
                            {
                                "block_id": "buttons",
                                "type": "actions",
                                "elements": [
                                    {
                                        "type": "button",
                                        "text": {
                                            "type": "plain_text",
                                            "text": "View Postmortem",
                                        },
                                        "style": "primary",
                                        "url": postmortem_link,
                                        "action_id": "view_postmortem",
                                    },
                                ],
                            },
                        ]

                        # Send postmortem message to incident channel
                        try:
                            result = slack_web_client.chat_postMessage(
                                channel=incident.channel_id,
                                blocks=postmortem_boilerplate_message_blocks,
                                text=postmortem_link,
                            )
                            slack_web_client.pins_add(
                                channel=incident.channel_id,
                                timestamp=result.get("ts"),
                            )
                        except SlackApiError as error:
                            logger.error(
                                f"Error sending postmortem update to incident channel: {error}"
                            )

                # Generate Gitlab postmortem if enabled
                # Get normalized description as postmortem title
                if (
                    settings.integrations
                    and settings.integrations.gitlab
                    and settings.integrations.gitlab.enabled
                    and settings.integrations.gitlab.auto_create_postmortem
                ):
                    from incidentbot.gitlab.postmortem import (
                        IncidentPostmortem,
                    )

                    postmortem = IncidentPostmortem(
                        incident=incident,
                        participants=IncidentDatabaseInterface.list_participants(
                            incident=incident
                        ),
                        timeline=EventLogHandler.read(incident_id=incident.id),
                        title=f"{datetime.datetime.today().strftime('%Y-%m-%d')} - {incident.slug.upper()} - {incident.description}",
                    )
                    postmortem_link = postmortem.create()

                    if postmortem_link:
                        # Create record
                        IncidentDatabaseInterface.add_postmortem(
                            parent=incident.id, url=postmortem_link
                        )

                        # Write event log
                        EventLogHandler.create(
                            event="Postmortem generated",
                            incident_id=incident.id,
                            incident_slug=incident.slug,
                            source="system",
                        )

                        postmortem_boilerplate_message_blocks = [
                            {
                                "type": "header",
                                "text": {
                                    "type": "plain_text",
                                    "text": "{} Incident Postmortem".format(
                                        settings.icons.get(
                                            settings.platform
                                        ).get("postmortem"),
                                    ),
                                },
                            },
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "A starter postmortem has been composed based on "
                                    + "data gathered during this incident.",
                                },
                            },
                            {
                                "block_id": "buttons",
                                "type": "actions",
                                "elements": [
                                    {
                                        "type": "button",
                                        "text": {
                                            "type": "plain_text",
                                            "text": "View Postmortem",
                                        },
                                        "style": "primary",
                                        "url": postmortem_link,
                                        "action_id": "view_postmortem",
                                    },
                                ],
                            },
                        ]

                        # Send postmortem message to incident channel
                        try:
                            result = slack_web_client.chat_postMessage(
                                channel=incident.channel_id,
                                blocks=postmortem_boilerplate_message_blocks,
                                text=postmortem_link,
                            )
                            slack_web_client.pins_add(
                                channel=incident.channel_id,
                                timestamp=result.get("ts"),
                            )
                        except SlackApiError as error:
                            logger.error(
                                f"Error sending postmortem update to incident channel: {error}"
                            )

            # If PagerDuty incident(s) exist, attempt to resolve them
            if (
                settings.integrations
                and settings.integrations.pagerduty
                and settings.integrations.pagerduty.enabled
            ):
                from incidentbot.pagerduty.api import PagerDutyInterface

                pagerduty_interface = PagerDutyInterface()

                if IncidentDatabaseInterface.list_pagerduty_incident_records(
                    id=incident.id
                ):
                    for (
                        inc
                    ) in IncidentDatabaseInterface.list_pagerduty_incident_records(
                        id=incident.id
                    ):
                        try:
                            pagerduty_interface.resolve(inc.url.split("/")[-1])
                        except Exception as error:
                            logger.error(
                                f"Error resolving PagerDuty incident {inc.url}: {error}"
                            )

        # Update digest message
        try:
            slack_web_client.chat_update(
                channel=get_digest_channel_id(),
                ts=incident.digest_message_ts,
                blocks=IncidentChannelDigestNotification.update(
                    channel_id=incident.channel_id,
                    has_private_channel=incident.has_private_channel,
                    incident_components=incident.components,
                    incident_description=incident.description,
                    incident_impact=incident.impact,
                    incident_slug=incident.slug,
                    meeting_link=incident.meeting_link,
                    severity=incident.severity,
                    status=status,
                    postmortem_link=postmortem_link,
                ),
                text="The digest message has been updated.",
            )
        except SlackApiError as error:
            logger.error(
                f"Error sending status update to incident channel {incident.channel_name}: {error}"
            )

        # Get current topic
        try:
            current_topic = [
                item.strip()
                for item in slack_web_client.conversations_info(
                    channel=incident.channel_id,
                )
                .get("channel")
                .get("topic")
                .get("value")
                .split("|")
            ]
        except SlackApiError as error:
            logger.error(f"error getting channel info: {error}")

        # Update topic
        # Severity is always index 0
        # Status is always index 1
        # If commander is assigned, it's always index 2
        new_topic = f"{current_topic[0]} | Status: {status.title()}"
        if len(current_topic) == 3:
            new_topic += f" | {current_topic[2]}"

        try:
            slack_web_client.conversations_setTopic(
                channel=incident.channel_id,
                topic=new_topic,
            )
        except SlackApiError as error:
            logger.error(f"Error setting incident channel topic: {error}")

        # Log
        logger.info(
            f"Updated incident status for {incident.channel_name} to {status}"
        )

        # Channel notification
        try:
            result = slack_web_client.chat_postMessage(
                **IncidentUpdate.status(
                    channel=incident.channel_id, status=status
                ),
                text=f"The incident status has been changed to {status}.",
            )
            logger.debug(f"\n{result}\n")
        except SlackApiError as error:
            logger.error(
                f"Error sending status update to incident channel {incident.channel_name}: {error}"
            )

        # Update jira ticket status last
        if (
            settings.integrations
            and settings.integrations.atlassian
            and settings.integrations.atlassian.jira
            and settings.integrations.atlassian.jira.enabled
            and settings.integrations.atlassian.jira.status_mapping
        ):
            from incidentbot.jira.api import JiraApi

            jira = JiraApi()
            jira.update_issue_status(
                incident_name=incident.channel_name,
                incident_status=status,
            )

        # Update gitlab ticket status
        if (
            settings.integrations
            and settings.integrations.gitlab
            and settings.integrations.gitlab.enabled
            and settings.integrations.gitlab.status_mapping
        ):
            from incidentbot.gitlab.api import GitLabApi

            gitlab = GitLabApi()
            gitlab.update_issue_status(
                incident_name=incident.channel_name, incident_status=status
            )
            logger.info(
                f"Updated GitLab issue status for {incident.channel_name} to {status}"
            )

        # Update incident record with new status
        try:
            IncidentDatabaseInterface.update_col(
                channel_id=incident.channel_id,
                col_name="status",
                value=status,
            )
        except Exception as error:
            logger.fatal(f"Error updating entry in database: {error}")

        # Write event log
        EventLogHandler.create(
            event=f"The incident status was changed to {status}",
            incident_id=incident.id,
            incident_slug=incident.slug,
            source="system",
        )

        if (
            status
            == [
                status
                for status, config in settings.statuses.items()
                if config.final
            ][0]
        ):
            # Remove comms reminder job if it exists
            try:
                job = TaskScheduler.get_job(
                    job_id=f"{incident.slug}_comms_reminder"
                )
                if job:
                    TaskScheduler.delete_job(job_to_delete=job.id)
            except Exception as error:
                logger.error(
                    f"error removing job {incident.slug}_comms_reminder: {error}"
                )

            # Remove role watcher job if it exists
            try:
                job = TaskScheduler.get_job(
                    job_id=f"{incident.slug}_role_watcher"
                )
                if job:
                    TaskScheduler.delete_job(job_to_delete=job.id)
            except Exception as error:
                logger.error(
                    f"error removing job {incident.slug}_role_watcher: {error}"
                )

            # Resolution message
            try:
                result = slack_web_client.chat_postMessage(
                    **BlockBuilder.resolution_message(
                        channel=incident.channel_id
                    ),
                    text="The incident has been resolved.",
                )
                logger.debug(f"\n{result}\n")
            except SlackApiError as error:
                logger.error(
                    f"Error sending resolution update to incident channel {incident.channel_name}: {error}"
                )
    else:
        slack_web_client.chat_postMessage(
            channel=channel_id,
            text=err_msg,
        )
