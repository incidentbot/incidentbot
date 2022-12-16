import config

from bot.scheduler import scheduler
from bot.slack.client import store_slack_user_list
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

job = Blueprint("job", __name__)

undeletable_jobs = ["update_pagerduty_oc_data", "update_slack_user_list"]


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
    if request.method == "POST":
        try:
            if job_id == "update_pagerduty_oc_data":
                if config.pagerduty_integration_enabled in (
                    "True",
                    "true",
                    True,
                ):
                    from bot.pagerduty.api import store_on_call_data

                    try:
                        store_on_call_data()
                    except Exception as error:
                        return (
                            jsonify({"error": str(error)}),
                            500,
                            {"ContentType": "application/json"},
                        )
                else:
                    return (
                        jsonify(
                            {"error": "pagerduty integration is not enabled"}
                        ),
                        500,
                        {"ContentType": "application/json"},
                    )
            elif job_id == "update_slack_user_list":
                try:
                    store_slack_user_list()
                except Exception as error:
                    return (
                        jsonify({"error": str(error)}),
                        500,
                        {"ContentType": "application/json"},
                    )
            else:
                return (
                    jsonify({"error": f"{job_id} is not a valid option"}),
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
    elif request.method == "DELETE":
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
