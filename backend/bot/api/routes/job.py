import config

from bot.scheduler import scheduler
from bot.slack.client import (
    store_slack_channel_list_db,
    store_slack_user_list_db,
)
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

job = Blueprint("job", __name__)

undeletable_jobs = [
    "scrape_for_aging_incidents",
    "update_opsgenie_oc_data",
    "update_pagerduty_oc_data",
    "update_slack_channel_list",
    "update_slack_user_list",
]


@job.route("/job", methods=["GET"])
@jwt_required()
def get_jobs():
    try:
        jobs = scheduler.process.list_jobs()
        job_details = []
        for j in jobs:
            job_details.append(
                {
                    "id": j.id,
                    "name": j.name,
                    "function": j.func_ref,
                    "trigger": str(j.trigger),
                    "next_run": str(j.next_run_time),
                }
            )
        return (
            jsonify(job_details),
            200,
            {"ContentType": "application/json"},
        )
    except Exception as error:
        return (
            jsonify({"error": str(error)}),
            500,
            {"ContentType": "application/json"},
        )


@job.route("/job/run/<job_id>", methods=["POST", "DELETE"])
@jwt_required()
def post_delete_run_job(job_id):
    match request.method:
        case "POST":
            try:
                match job_id:
                    case "scrape_for_aging_incidents":
                        try:
                            scheduler.scrape_for_aging_incidents()
                        except Exception as error:
                            return (
                                jsonify({"error": str(error)}),
                                500,
                                {"ContentType": "application/json"},
                            )
                    case "update_opsgenie_oc_data":
                        if config.active.integrations.get(
                            "atlassian"
                        ) and config.active.integrations.get("atlassian").get(
                            "opsgenie"
                        ):
                            from bot.opsgenie.api import OpsgenieAPI

                            try:
                                api = OpsgenieAPI()
                                api.store_on_call_data()
                            except Exception as error:
                                return (
                                    jsonify({"error": str(error)}),
                                    500,
                                    {"ContentType": "application/json"},
                                )
                        else:
                            return (
                                jsonify(
                                    {
                                        "error": "opsgenie integration is not enabled"
                                    }
                                ),
                                500,
                                {"ContentType": "application/json"},
                            )
                    case "update_pagerduty_oc_data":
                        if "pagerduty" in config.active.integrations:
                            from bot.pagerduty.api import PagerDutyInterface

                            pagerduty_interface = PagerDutyInterface()

                            try:
                                pagerduty_interface.store_on_call_data()
                            except Exception as error:
                                return (
                                    jsonify({"error": str(error)}),
                                    500,
                                    {"ContentType": "application/json"},
                                )
                        else:
                            return (
                                jsonify(
                                    {
                                        "error": "pagerduty integration is not enabled"
                                    }
                                ),
                                500,
                                {"ContentType": "application/json"},
                            )
                    case "update_slack_channel_list":
                        try:
                            store_slack_channel_list_db()
                        except Exception as error:
                            return (
                                jsonify({"error": str(error)}),
                                500,
                                {"ContentType": "application/json"},
                            )
                    case "update_slack_user_list":
                        try:
                            store_slack_user_list_db()
                        except Exception as error:
                            return (
                                jsonify({"error": str(error)}),
                                500,
                                {"ContentType": "application/json"},
                            )
                    case _:
                        return (
                            jsonify(
                                {"error": f"{job_id} is not a valid option"}
                            ),
                            500,
                            {"ContentType": "application/json"},
                        )
                return (
                    jsonify({"success": True}),
                    200,
                    {"ContentType": "application/json"},
                )
            except Exception as error:
                return (
                    jsonify({"error": str(error)}),
                    500,
                    {"ContentType": "application/json"},
                )
        case "DELETE":
            if job_id not in undeletable_jobs:
                try:
                    delete_job = scheduler.process.delete_job(job_id)
                    if delete_job != None:
                        return (
                            jsonify({"error": str(delete_job)}),
                            500,
                            {"ContentType": "application/json"},
                        )
                    else:
                        return (
                            jsonify({"success": True}),
                            200,
                            {"ContentType": "application/json"},
                        )
                except Exception as error:
                    return (
                        jsonify({"error": str(error)}),
                        500,
                        {"ContentType": "application/json"},
                    )
            else:
                return (
                    jsonify({"error": f"{job_id} cannot be deleted"}),
                    500,
                    {"ContentType": "application/json"},
                )
