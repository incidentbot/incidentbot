import config
import json

from bot.models.pg import Incident, OperationalData, Session
from bot.utils import utils
from bot.slack.client import slack_workspace_id
from logger import logger
from pdpyras import APISession, PDClientError
from sqlalchemy import update
from typing import Dict, List

image_url = "https://i.imgur.com/IVvdFCV.png"


class PagerDutyInterface:
    def __init__(self, escalation_policy: str = None):
        self.escalation_policy = escalation_policy

    @classmethod
    def session(self) -> APISession:
        return APISession(
            config.pagerduty_api_token,
            default_from=config.pagerduty_api_username,
        )

    @property
    def escalation_policy_id(self) -> str:
        """
        Get the ID of an escalation policy
        """

        escalation_policies = self.session().iter_all("escalation_policies")
        for policy in escalation_policies:
            if policy.get("name") == self.escalation_policy:
                return policy.get("id")

    @property
    def service_for_escalation_policy(self) -> str:
        """
        Determine which service is associated with an escalation policy
        """

        escalation_policies = self.session().iter_all("escalation_policies")
        for policy in escalation_policies:
            if policy.get("name") == self.escalation_policy:
                return policy.get("services")[0].get("id")

    @classmethod
    def get_on_calls(self, short: bool = False) -> Dict:
        """
        Given a PagerDuty instance, loop through oncall schedules and return info
        on each one identifying who to contact when run

        This is stored in the database and will only refresh when this function is
        called to avoid API abuse
        """

        on_call = {}
        auto_mapping = {}

        try:
            slack_users_from_dict = (
                Session.query(OperationalData)
                .filter(OperationalData.id == "slack_users")
                .one()
                .serialize()
            )
        except Exception as error:
            logger.error(
                f"Error retrieving list of Slack users from db: {error}"
            )
        finally:
            Session.close()
            Session.remove()

        slack_users = {
            user.get("real_name"): user.get("id")
            for user in slack_users_from_dict
            if user.__contains__("real_name")
        }

        oncalls = self.session().iter_all("oncalls")

        if oncalls is None:
            logger.warn("PagerDuty schedule information returned as empty")

            return {}
        else:
            for item in oncalls:
                on_call[item.get("escalation_policy").get("summary")] = sorted(
                    [
                        {
                            "escalation_level": item.get("escalation_level"),
                            "escalation_policy": item.get(
                                "escalation_policy"
                            ).get("summary"),
                            "escalation_policy_id": item.get(
                                "escalation_policy"
                            ).get("id"),
                            "user": item.get("user").get("summary"),
                            "start": item.get("start"),
                            "end": item.get("end"),
                            "slack_user_id": [
                                val
                                for key, val in slack_users.items()
                                if item.get("user").get("summary") in key
                            ],
                        }
                        for item in self.session().iter_all("oncalls")
                        if item.get("start") != None
                        and item.get("end") != None
                    ],
                    key=lambda x: x.get("escalation_level"),
                )

                auto_mapping[item.get("escalation_policy").get("summary")] = (
                    item.get("escalation_policy").get("summary")
                )

        logger.info(f"PagerDuty returned {len(on_call)} schedules")

        if short:
            return auto_mapping
        else:
            return on_call

    def page(
        self,
        priority: str,
        channel_name: str,
        channel_id: str,
        paging_user: str,
    ):
        """
        Page via an escalation policy when triggered from Slack.
        """

        if self.escalation_policy_id is not None:
            pagerduty_incident_data = {
                "incident": {
                    "type": "incident",
                    "title": f"Slack incident {channel_name} has been started and a page has been issued for assistance.",
                    "service": {
                        "id": self.service_for_escalation_policy,
                        "type": "service_reference",
                    },
                    "urgency": priority,
                    "incident_key": channel_name,
                    "body": {
                        "type": "incident_body",
                        "details": "An incident has been declared in Slack and this team has been paged as a result. "
                        + f"You were paged by {paging_user}. Link: https://{slack_workspace_id}.slack.com/archives/{channel_id}",
                    },
                    "escalation_policy": {
                        "id": self.escalation_policy_id,
                        "type": "escalation_policy_reference",
                    },
                }
            }
            try:
                response = self.session().post(
                    "/incidents", json=pagerduty_incident_data
                )

                if not response.ok:
                    raise Exception(
                        "Error creating PagerDuty incident: {}".format(
                            response.json()
                        )
                    )

                try:
                    created_incident = json.loads(response.text)["incident"]
                    incident = (
                        Session.query(Incident)
                        .filter_by(incident_id=channel_name)
                        .one()
                    )

                    existing_incidents = incident.pagerduty_incidents

                    if existing_incidents is None:
                        existing_incidents = [created_incident.get("id")]
                    else:
                        existing_incidents.append(created_incident.get("id"))

                    Session.execute(
                        update(Incident)
                        .where(Incident.incident_id == channel_name)
                        .values(pagerduty_incidents=existing_incidents)
                    )
                    Session.commit()
                except Exception as error:
                    logger.error(
                        f"Error updating incident with PagerDuty incident data: {error}"
                    )
                finally:
                    Session.close()
                    Session.remove()
            except PDClientError as error:
                logger.error(f"Error creating PagerDuty incident: {error}")
        else:
            logger.error(
                f"Error during PagerDuty incident creation - could not find escalation policy id for policy {self.escalation_policy}"
            )

    def resolve(self, pagerduty_incident_id: str):
        """Resolve a PagerDuty incident"""

        pd_inc_patch = {
            "incident": {
                "type": "incident",
                "status": "resolved",
                "resolution": "This incident has been resolved via the incident management process.",
            }
        }
        try:
            response = self.session().put(
                f"/incidents/{pagerduty_incident_id}", json=pd_inc_patch
            )

            if not response.ok:
                logger.error(
                    "Error patching PagerDuty incident: {}".format(
                        response.json()
                    )
                )
            else:
                logger.info(
                    f"Successfully resolved PagerDuty incident {pagerduty_incident_id}"
                )
        except PDClientError as error:
            logger.error(f"Error patching PagerDuty incident: {error}")

    @classmethod
    def store_on_call_data(self):
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
            if (
                not Session.query(OperationalData)
                .filter_by(id=record_name)
                .all()
            ):
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
                    json_data=self.get_on_calls(),
                    updated_at=utils.fetch_timestamp(),
                )
            )
            Session.commit()
        except Exception as error:
            logger.error(f"Opdata row edit failed for {record_name}: {error}")
            Session.rollback()
        finally:
            Session.close()

        # Store auto map data
        try:
            record_name = "pagerduty_auto_mapping"
            # Create the row if it doesn't exist
            if (
                not Session.query(OperationalData)
                .filter_by(id=record_name)
                .all()
            ):
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
                    json_data=self.get_on_calls(short=True),
                    updated_at=utils.fetch_timestamp(),
                )
            )
            Session.commit()
        except Exception as error:
            logger.error(f"Opdata row edit failed for {record_name}: {error}")
            Session.rollback()
        finally:
            Session.close()

    @classmethod
    def test(self) -> List[Dict]:
        try:
            return [sch for sch in self.session().iter_all("oncalls")]
        except Exception as error:
            logger.error(f"Error during validation of PagerDuty auth: {error}")
