import logging

from bot.api.schemas.incident import (
    incident_schema,
    incidents_schema,
)
from bot.audit import log
from bot.incident import actions, incident
from bot.models.incident import db_read_all_incidents, db_read_incident
from bot.models.pg import Incident, IncidentLogging, Session
from flask import Blueprint, jsonify, request, Response
from flask_jwt_extended import jwt_required
from sqlalchemy import update

logger = logging.getLogger("incident-api-router")

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
        description = data["description"]
        user = data["user"]
        severity = data["severity"]
        is_security_incident = data["security"] in ("True", "true")
        request_parameters = {
            "channel": "web",
            "incident_description": description,
            "user": user,
            "severity": severity,
            "created_from_web": True,
            "is_security_incident": is_security_incident,
        }
        # Create an incident based on the message using the internal path
        try:
            incident.create_incident(
                internal=False, request_parameters=request_parameters
            )
            return (
                jsonify({"success": True}),
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


@incidentrt.route("/incident/<incident_id>/audit", methods=["GET", "DELETE"])
@jwt_required()
def get_incident_audit_log(incident_id):
    if request.method == "GET":
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
    elif request.method == "DELETE":
        request_data = request.json
        try:
            success, error = log.delete(
                incident_id=incident_id,
                log=request_data["log"],
                ts=request_data["ts"],
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
    "/incident/<incident_id>/pinned/<id>", methods=["GET", "DELETE"]
)
# ToDo
# It is an acceptable risk since this app should never be publicly exposed
# The API is currently only consumed by the app
# @jwt_required()
def get_delete_item_by_id(incident_id, id):
    try:
        img = Session.query(IncidentLogging).filter_by(id=id).first()
        if request.method == "GET":
            if not img:
                return (
                    jsonify({"error": "object not found"}),
                    500,
                    {"ContentType": "application/json"},
                )
            return Response(img.img, mimetype=img.mimetype), 200
        elif request.method == "DELETE":
            Session.delete(img)
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
        int_request_data = {
            "incident_id": incident_id,
            "channel_id": request_data["channel_id"],
            "role": request_data["role"],
            "bp_message_ts": request_data["bp_message_ts"],
            "user": request_data["user"],
        }
        actions.assign_role(web_data=int_request_data, request_origin="web")
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
    try:
        request_data = request.json
        field = request_data["field"]
        action = request_data["action"]
        value = request_data["value"]
        incident = (
            Session.query(Incident).filter_by(incident_id=incident_id).one()
        )
        if field == "tags":
            existing_tags = incident.tags
            if action == "update":
                if existing_tags == None:
                    existing_tags = [value]
                else:
                    existing_tags.append(value)
            elif action == "delete":
                existing_tags.remove(value)
            try:
                Session.execute(
                    update(Incident)
                    .where(Incident.incident_id == incident_id)
                    .values(tags=existing_tags)
                )
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
            return (
                jsonify(
                    {
                        "error": f"field {field} is not a valid option for incidents/PATCH"
                    }
                ),
                500,
                {"ContentType": "application/json"},
            )
    except Exception as error:
        return (
            jsonify({"error": str(error)}),
            500,
            {"ContentType": "application/json"},
        )
