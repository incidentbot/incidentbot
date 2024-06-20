import sqlalchemy

from bot.models.pg import Setting, Session
from bot.slack.client import slack_workspace_id
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from logger import logger

setting = Blueprint("setting", __name__)


@setting.route("/setting", methods=["GET"])
@jwt_required()
def handle_settings():
    try:
        settings = [
            s.serialize()
            for s in Session.query(Setting).order_by(Setting.name.asc())
        ]
        return (
            jsonify({"data": settings}),
            200,
            {"ContentType": "application/json"},
        )
    except Exception as error:
        Session.rollback()
        return (
            jsonify({"error": str(error)}),
            500,
            {"ContentType": "application/json"},
        )
    finally:
        Session.close()
        Session.remove()


@setting.route("/setting/<name>", methods=["GET"])
@jwt_required()
def handle_setting(name):
    match request.method:
        case "GET":
            match name:
                case "slack_workspace_id":
                    return (
                        jsonify({"data": slack_workspace_id}),
                        200,
                        {"ContentType": "application/json"},
                    )
                case _:
                    try:
                        setting = (
                            Session.query(Setting)
                            .filter(Setting.name == name)
                            .one()
                        )
                        return (
                            jsonify({"data": setting.value}),
                            200,
                            {"ContentType": "application/json"},
                        )
                    except sqlalchemy.exc.NoResultFound as error:
                        Session.rollback()
                        return (
                            jsonify({"error": "Setting not found"}),
                            500,
                            {"ContentType": "application/json"},
                        )
                    except Exception as error:
                        logger.error(
                            f"Setting lookup failed for {name}: {error}"
                        )
                        Session.rollback()
                        return (
                            jsonify({"error": str(error)}),
                            500,
                            {"ContentType": "application/json"},
                        )
                    finally:
                        Session.close()
                        Session.remove()
