import json
import logging
import psycopg2
import sqlalchemy

from bot.models.pg import Setting, Session
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

logger = logging.getLogger(__name__)

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
    if request.method == "GET":
        try:
            setting = Session.query(Setting).filter(Setting.name == name).one()
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
            logger.error(f"Setting lookup failed for {name}: {error}")
            Session.rollback()
            return (
                jsonify({"error": str(error)}),
                500,
                {"ContentType": "application/json"},
            )
        finally:
            Session.close()
            Session.remove()
