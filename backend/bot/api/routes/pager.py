import config

from bot.models.pg import OperationalData, Session
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

pager = Blueprint("pager", __name__)


@pager.route("/pager", methods=["GET"])
@jwt_required()
def get_pager():
    if config.active.integrations.get(
        "atlassian"
    ) and config.active.integrations.get("atlassian").get("opsgenie"):
        try:
            data = (
                Session.query(OperationalData)
                .filter(OperationalData.id == "opsgenie_oc_data")
                .one()
                .serialize()
            )
            return (
                jsonify(
                    {
                        "platform": "opsgenie",
                        "data": data["json_data"],
                        "ts": data["updated_at"],
                    }
                ),
                200,
                {"ContentType": "application/json"},
            )
        except Exception as error:
            return (
                jsonify({"error": str(error)}),
                500,
                {"ContentType": "application/json"},
            )
        finally:
            Session.close()
            Session.remove()
    elif "pagerduty" in config.active.integrations:
        try:
            data = (
                Session.query(OperationalData)
                .filter(OperationalData.id == "pagerduty_oc_data")
                .one()
                .serialize()
            )
            return (
                jsonify(
                    {
                        "platform": "pagerduty",
                        "data": data["json_data"],
                        "ts": data["updated_at"],
                    }
                ),
                200,
                {"ContentType": "application/json"},
            )
        except Exception as error:
            return (
                jsonify({"error": str(error)}),
                500,
                {"ContentType": "application/json"},
            )
        finally:
            Session.close()
            Session.remove()

    return (
        jsonify({"data": "feature_not_enabled"}),
        200,
        {"ContentType": "application/json"},
    )


@pager.route("/pager/auto_map", methods=["GET"])
@jwt_required()
def get_pager_automapping():
    if "pagerduty" in config.active.integrations:
        try:
            data = (
                Session.query(OperationalData)
                .filter(OperationalData.id == "pagerduty_auto_mapping")
                .one()
                .serialize()
            )
            return (
                jsonify({"data": data["json_data"], "ts": data["updated_at"]}),
                200,
                {"ContentType": "application/json"},
            )
        except Exception as error:
            return (
                jsonify({"error": str(error)}),
                500,
                {"ContentType": "application/json"},
            )
        finally:
            Session.close()
            Session.remove()

    return (
        jsonify({"data": "feature_not_enabled"}),
        200,
        {"ContentType": "application/json"},
    )


@pager.route("/pager/auto_map/store", methods=["GET", "PATCH"])
@jwt_required()
def get_patch_pager_automapping():
    if "pagerduty" in config.active.integrations:
        match request.method:
            case "GET":
                try:
                    data = (
                        Session.query(OperationalData)
                        .filter(OperationalData.id == "auto_page_teams")
                        .one()
                        .serialize()
                    )
                    return (
                        jsonify(
                            {
                                "data": data["json_data"],
                                "ts": data["updated_at"],
                            }
                        ),
                        200,
                        {"ContentType": "application/json"},
                    )
                except Exception as error:
                    return (
                        jsonify({"error": str(error)}),
                        500,
                        {"ContentType": "application/json"},
                    )
                finally:
                    Session.close()
                    Session.remove()
            case "PATCH":
                v = request.json["value"]
                try:
                    data = (
                        Session.query(OperationalData)
                        .filter(OperationalData.id == "auto_page_teams")
                        .one()
                    )
                    data.json_data = {"teams": v}
                    Session.commit()
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
                finally:
                    Session.close()
                    Session.remove()

    return (
        jsonify({"data": "feature_not_enabled"}),
        200,
        {"ContentType": "application/json"},
    )
