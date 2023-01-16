import config
import json
import logging

from bot.models.pg import Incident, OperationalData, Session
from bot.shared import tools
from bot.slack.client import slack_workspace_id
from collections import defaultdict
from pdpyras import APISession, PDClientError
from sqlalchemy import update
from typing import Dict

logger = logging.getLogger(__name__)

session = APISession(
    config.pagerduty_api_token, default_from=config.pagerduty_api_username
)

"""
PagerDuty
"""


def find_escalation_policy_id(ep_name: str) -> str:
    """
    Get the ID of an escalation policy
    """
    eps = session.iter_all("escalation_policies")
    # .find wasn't working for this, no idea why.
    for ep in eps:
        if ep["name"] == ep_name:
            return ep["id"]


def find_service_for_escalation_policy(ep_name: str) -> str:
    """
    Determine which service is associated with an escalation policy
    """
    eps = session.iter_all("escalation_policies")
    # .find wasn't working for this, no idea why.
    for ep in eps:
        if ep["name"] == ep_name:
            return ep["services"][0]["id"]


def find_who_is_on_call(short: bool = False) -> Dict:
    """
    Given a PagerDuty instance, loop through oncall schedules and return info
    on each one identifying who to contact when run

    This is stored in the database and will only refresh when this function is
    called to avoid API abuse
    """
    on_call = defaultdict(list)
    auto_mapping = {}
    try:
        slack_users_from_dict = (
            Session.query(OperationalData)
            .filter(OperationalData.id == "slack_users")
            .one()
            .serialize()
        )
    except Exception as error:
        logger.error(f"Error retrieving list of Slack users from db: {error}")
    finally:
        Session.close()
        Session.remove()
    slack_users = {
        user["real_name"]: user["id"]
        for user in slack_users_from_dict
        if user.__contains__("real_name")
    }
    for oc in session.iter_all("oncalls"):
        if oc["start"] != None and oc["end"] != None:
            on_call[oc["escalation_policy"]["summary"]].append(
                {
                    "escalation_level": oc["escalation_level"],
                    "escalation_policy": oc["escalation_policy"]["summary"],
                    "escalation_policy_id": oc["escalation_policy"]["id"],
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
            auto_mapping[oc["schedule"]["summary"]] = oc["escalation_policy"][
                "summary"
            ]
    # Sort values by name, sort dict by escalation_level
    result = {}
    if short:
        return auto_mapping
    for i, j in sorted(dict(on_call).items()):
        result[i] = sorted(j, key=lambda d: d["escalation_level"])
    return result


def page(
    ep_name: str,
    priority: str,
    channel_name: str,
    channel_id: str,
    paging_user: str,
):
    """
    Page via an escalation policy when triggered from Slack.
    """
    service_id = find_service_for_escalation_policy(ep_name=ep_name)
    ep_id = find_escalation_policy_id(ep_name=ep_name)
    pd_inc = {
        "incident": {
            "type": "incident",
            "title": f"Slack incident {channel_name} has been started and a page has been issued for assistance.",
            "service": {"id": service_id, "type": "service_reference"},
            "urgency": priority,
            "incident_key": channel_name,
            "body": {
                "type": "incident_body",
                "details": "An incident has been declared in Slack and this team has been paged as a result. "
                + f"You were paged by {paging_user}. Link: https://{slack_workspace_id}.slack.com/archives/{channel_id}",
            },
            "escalation_policy": {
                "id": ep_id,
                "type": "escalation_policy_reference",
            },
        }
    }
    try:
        response = session.post("/incidents", json=pd_inc)
        logger.info(response)
        if not response.ok:
            logger.error(
                "Error creating PagerDuty incident: {}".format(response.json())
            )
    except PDClientError as error:
        logger.error(f"Error creating PagerDuty incident: {error}")
    # Update incident record with PagerDuty incident info
    try:
        created_incident = json.loads(response.text)["incident"]
        incident = (
            Session.query(Incident).filter_by(incident_id=channel_name).one()
        )
        existing_incidents = incident.pagerduty_incidents
        if existing_incidents is None:
            existing_incidents = [created_incident["id"]]
        else:
            existing_incidents.append(created_incident["id"])
            Session.execute(
                update(Incident)
                .where(Incident.incident_id == channel_name)
                .values(pagerduty_incidents=existing_incidents)
            )
            Session.commit()
    except Exception as error:
        logger.error(f"Error updating incident: {error}")
    finally:
        Session.close()
        Session.remove()


def resolve(pd_incident_id: str):
    pd_inc_patch = {
        "incident": {
            "type": "incident",
            "status": "resolved",
            "resolution": "This incident has been resolved via the incident management process.",
        }
    }
    try:
        response = session.put(
            f"/incidents/{pd_incident_id}", json=pd_inc_patch
        )
        logger.info(response)
        if not response.ok:
            logger.error(
                "Error patching PagerDuty incident: {}".format(response.json())
            )
        else:
            logger.info(
                f"Successfully resolved PagerDuty incident {pd_incident_id}"
            )
    except PDClientError as error:
        logger.error(f"Error patching PagerDuty incident: {error}")


def store_on_call_data():
    """
    Parses information from PagerDuty regarding on-call information and stores it
    in the database

    This stores both a comprehensive list of schedule information and a mapping made
    available to the auto page functions
    """
    # Store all data
    try:
        record_name = "pagerduty_oc_data"
        # Create the row if it doesn't exist
        if not Session.query(OperationalData).filter_by(id=record_name).all():
            try:
                row = OperationalData(id=record_name)
                Session.add(row)
                Session.commit()
            except Exception as error:
                logger.error(
                    f"Opdata row create failed for {record_name}: {error}"
                )
        Session.execute(
            update(OperationalData)
            .where(OperationalData.id == record_name)
            .values(
                json_data=find_who_is_on_call(short=False),
                updated_at=tools.fetch_timestamp(),
            )
        )
        Session.commit()
    except Exception as error:
        logger.error(f"Opdata row edit failed for {record_name}: {error}")
        Session.rollback()
    finally:
        Session.close()

    # Store all data
    try:
        record_name = "pagerduty_auto_mapping"
        # Create the row if it doesn't exist
        if not Session.query(OperationalData).filter_by(id=record_name).all():
            try:
                row = OperationalData(id=record_name)
                Session.add(row)
                Session.commit()
            except Exception as error:
                logger.error(
                    f"Opdata row create failed for {record_name}: {error}"
                )
        Session.execute(
            update(OperationalData)
            .where(OperationalData.id == record_name)
            .values(
                json_data=find_who_is_on_call(short=True),
                updated_at=tools.fetch_timestamp(),
            )
        )
        Session.commit()
    except Exception as error:
        logger.error(f"Opdata row edit failed for {record_name}: {error}")
        Session.rollback()
    finally:
        Session.close()
