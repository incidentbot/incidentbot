import asyncio
import config

from bot.api.routes.auth import api_key_required
from bot.api.schemas.incident import (
    incident_schema,
    incidents_schema,
)
from bot.audit import log
from bot.exc import ConfigurationError
from bot.incident import actions, incident
from bot.incident.action_parameters import ActionParametersWeb
from bot.models.incident import db_read_all_incidents, db_read_incident
from bot.models.pg import Incident, IncidentLogging, Session
from flask import Blueprint, jsonify, request, Response
from flask_jwt_extended import jwt_required
from logger import logger

incidentrt = Blueprint("incident", __name__)


@incidentrt.route("/incident", methods=["GET"])
@jwt_required()
def get_incidents():
    try:
        incidents = db_read_all_incidents(return_json=False)
        return jsonify({"data": incidents_schema.dump(incidents)}), 200
    except Exception as error:
        return (
            jsonify({"error": str(error)}),
            500,
            {"ContentType": "application/json"},
        )


@incidentrt.route("/incident/<incident_id>", methods=["GET"])
@jwt_required()
def get_one_incident(incident_id):
    try:
        incident = db_read_incident(incident_id=incident_id, return_json=True)
        return jsonify({"data": incident_schema.dump(incident)}), 200
    except Exception as error:
        return (
            jsonify({"error": str(error)}),
            500,
            {"ContentType": "application/json"},
        )


@incidentrt.route("/incident", methods=["POST"])
@jwt_required()
def post_incident():
    try:
        data = request.json
        description = data.get("description", "")
        severity = data.get("severity", None)
        is_security_incident = data.get("security", "false") in (
            "True",
            "true",
            True,
        )
        private_channel = data.get("private", "false") in (
            "True",
            "true",
            True,
        )
        # Create request parameters object
        try:
            request_parameters = incident.RequestParameters(
                channel="web",
                incident_description=description,
                user="api",
                severity=severity,
                created_from_web=True,
                is_security_incident=is_security_incident,
                private_channel=private_channel,
            )
        except ConfigurationError as error:
            logger.error(error)
            return (
                jsonify({"error": str(error)}),
                500,
                {"ContentType": "application/json"},
            )
        # Create an incident based on the message using the internal path
        try:
            resp = incident.create_incident(
                internal=False, request_parameters=request_parameters
            )
            return (
                jsonify({"success": True, "message": resp}),
                201,
                {"ContentType": "application/json"},
            )
        except Exception as error:
            logger.error(f"Error when trying to create an incident: {error}")
            return (
                jsonify({"error": str(error)}),
                500,
                {"ContentType": "application/json"},
            )
    except Exception as error:
        return (
            jsonify({"error": str(error)}),
            500,
            {"ContentType": "application/json"},
        )


@incidentrt.route("/incident/ext", methods=["POST"])
@api_key_required
def post_incident_ext():
    try:
        data = request.json
        description = data.get("description", "")
        severity = data.get("severity", None)
        is_security_incident = data.get("security", "false") in (
            "True",
            "true",
            True,
        )
        private_channel = data.get("private", "false") in (
            "True",
            "true",
            True,
        )
        # Create request parameters object
        try:
            request_parameters = incident.RequestParameters(
                channel="web",
                incident_description=description,
                user="api",
                severity=severity,
                created_from_web=True,
                is_security_incident=is_security_incident,
                private_channel=private_channel,
            )
        except ConfigurationError as error:
            logger.error(error)
            return (
                jsonify({"error": str(error)}),
                500,
                {"ContentType": "application/json"},
            )
        # Create an incident based on the message using the internal path
        try:
            resp = incident.create_incident(
                internal=False, request_parameters=request_parameters
            )
            return (
                jsonify({"success": True, "message": resp}),
                201,
                {"ContentType": "application/json"},
            )
        except Exception as error:
            logger.error(f"Error when trying to create an incident: {error}")
            return (
                jsonify({"error": str(error)}),
                500,
                {"ContentType": "application/json"},
            )
    except Exception as error:
        return (
            jsonify({"error": str(error)}),
            500,
            {"ContentType": "application/json"},
        )


@incidentrt.route(
    "/incident/<incident_id>/audit",
    methods=["GET", "DELETE", "PATCH", "POST", "OPTIONS"],
)
@jwt_required()
def get_delete_post_incident_audit_log(incident_id):
    match request.method:
        case "GET":
            try:
                audit_logs = log.read(incident_id)
                return (
                    jsonify({"data": audit_logs}),
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
            request_data = request.json
            try:
                success, error = log.delete(
                    incident_id=incident_id,
                    id=request_data["id"],
                    log=request_data["log"],
                )
                if success:
                    return (
                        jsonify({"success": True}),
                        200,
                        {"ContentType": "application/json"},
                    )
                else:
                    return (
                        jsonify({"error": str(error)}),
                        500,
                        {"ContentType": "application/json"},
                    )
            except Exception as error:
                return (
                    jsonify({"error": str(error)}),
                    500,
                    {"ContentType": "application/json"},
                )
        case "POST":
            request_data = request.json
            try:
                audit_logs = log.write(
                    incident_id=incident_id,
                    event=request_data["event"],
                    ts=request_data["timestamp"],
                    user=request_data["user"],
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
        case "PATCH":
            request_data = request.json
            try:
                create, msg = log.edit(
                    incident_id=incident_id,
                    id=request_data["id"],
                    new_log=request_data["event"],
                )
                if not create:
                    return (
                        jsonify({"error": str(msg)}),
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


@incidentrt.route("/incident/<incident_id>/pinned", methods=["GET"])
@jwt_required()
def get_incident_pinned_items(incident_id):
    try:
        all_objs = (
            Session.query(IncidentLogging)
            .filter_by(incident_id=incident_id)
            .all()
        )
        items = [
            {
                "id": obj.id,
                "is_image": True if obj.img else False,
                "title": obj.title,
                "content": obj.content,
                "ts": obj.ts,
                "user": obj.user,
            }
            for obj in all_objs
        ]
        return jsonify({"data": items}), 200
    except Exception as error:
        return (
            jsonify({"error": str(error)}),
            500,
            {"ContentType": "application/json"},
        )


@incidentrt.route(
    "/incident/<incident_id>/pinned/<id>", methods=["GET", "PATCH", "DELETE"]
)
@jwt_required()
def get_patch_delete_item_by_id(incident_id, id):
    try:
        obj = (
            Session.query(IncidentLogging)
            .filter_by(incident_id=incident_id, id=id)
            .first()
        )
        match request.method:
            case "GET":
                if not obj:
                    return (
                        jsonify({"error": "object not found"}),
                        500,
                        {"ContentType": "application/json"},
                    )
                return (
                    Response(
                        obj.img,
                        mimetype=obj.mimetype,
                    ),
                    200,
                )
            case "DELETE":
                Session.delete(obj)
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


@incidentrt.route("/incident/<incident_id>/role", methods=["POST"])
@jwt_required()
def post_set_incident_role(incident_id):
    try:
        request_data = request.json
        inc_request_data = ActionParametersWeb(
            incident_id=incident_id,
            channel_id=request_data["channel_id"],
            role=request_data["role"],
            bp_message_ts=request_data["bp_message_ts"],
            user=request_data["user"],
        )
        asyncio.run(
            actions.assign_role(
                web_data=inc_request_data, request_origin="web"
            )
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


@incidentrt.route("/incident/<incident_id>", methods=["PATCH"])
@jwt_required()
def patch_update_incident(incident_id):
    request_data = request.json
    field = request_data["field"]
    action = request_data["action"]
    value = request_data["value"]
    incident = Session.query(Incident).filter_by(incident_id=incident_id).one()
    match field:
        case "tags":
            match action:
                case "update":
                    if incident.tags is None:
                        try:
                            incident.tags = []
                            incident.tags.append(value)
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
                    else:
                        try:
                            incident.tags.append(value)
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
                case "delete":
                    try:
                        incident.tags.remove(value)
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
        case _:
            return (
                jsonify(
                    {
                        "error": f"field {field} is not a valid option for incidents/PATCH"
                    }
                ),
                500,
                {"ContentType": "application/json"},
            )


@incidentrt.route("/incident/config/<parameter>", methods=["GET"])
@jwt_required()
def get_incident_config(parameter):
    try:
        match parameter:
            case "roles":
                resp = [key for key, _ in config.active.roles.items()]
            case "severities":
                resp = [key for key, _ in config.active.severities.items()]
            case "statuses":
                resp = config.active.statuses
        return (
            jsonify({"data": resp}),
            200,
            {"ContentType": "application/json"},
        )
    except Exception as error:
        logger.error(f"Error returning incident configuration: {error}")
        return (
            jsonify({"error": str(error)}),
            500,
            {"ContentType": "application/json"},
        )
