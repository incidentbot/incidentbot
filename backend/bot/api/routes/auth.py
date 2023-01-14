import logging
import secrets
import sqlalchemy

from bot.models.pg import PrivateSetting, Session
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

logger = logging.getLogger(__name__)

auth = Blueprint("auth", __name__)


class ApiKey:
    @staticmethod
    def generate() -> str:
        return secrets.token_urlsafe(20)


@auth.route("/auth/api_key", methods=["GET", "POST", "DELETE"])
@jwt_required()
def handle_api_key():
    match request.method:
        case "GET":
            try:
                setting = (
                    Session.query(PrivateSetting)
                    .filter(PrivateSetting.name == "active_api_key")
                    .one()
                )
                return (
                    jsonify({"data": setting.value}),  ######
                    200,
                    {"ContentType": "application/json"},
                )
            except sqlalchemy.exc.NoResultFound as error:
                Session.rollback()
                return (
                    jsonify({"data": None}),
                    200,
                    {"ContentType": "application/json"},
                )
            except Exception as error:
                logger.error(
                    f"Setting lookup failed for active API key: {error}"
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
        case "POST":
            try:
                if (
                    Session.query(PrivateSetting)
                    .filter_by(name="active_api_key")
                    .one_or_none()
                    is not None
                ):
                    Session.execute(
                        sqlalchemy.update(PrivateSetting)
                        .where(PrivateSetting.name == "active_api_key")
                        .values(value=ApiKey.generate())
                    )
                    Session.commit()
                    return (
                        jsonify({"success": True}),
                        200,
                        {"ContentType": "application/json"},
                    )
                else:
                    setting = PrivateSetting(
                        name="active_api_key",
                        value=ApiKey.generate(),
                        description="Current Active API Key",
                        deletable=True,
                    )
                    Session.add(setting)
                    Session.commit()
                    return (
                        jsonify({"success": True}),
                        200,
                        {"ContentType": "application/json"},
                    )
            except Exception as error:
                logger.error(f"Error looking up API key: {error}")
                Session.rollback()
                return (
                    jsonify({"error": str(error)}),
                    500,
                    {"ContentType": "application/json"},
                )
            finally:
                Session.close()
                Session.remove()
        case "DELETE":
            try:
                Session.query(PrivateSetting).filter(
                    PrivateSetting.name == "active_api_key"
                ).delete()
                Session.commit()
                return (
                    jsonify({"success": True}),
                    200,
                    {"ContentType": "application/json"},
                )
            except Exception as error:
                logger.error(f"Delete failed for API key: {error}")
                Session.rollback()
                return (
                    jsonify({"error": str(error)}),
                    500,
                    {"ContentType": "application/json"},
                )
            finally:
                Session.close()
                Session.remove()


@auth.route("/auth/api_allowed_hosts", methods=["GET", "POST", "DELETE"])
@jwt_required()
def handle_api_allowed_hosts():
    match request.method:
        case "GET":
            try:
                setting = (
                    Session.query(PrivateSetting)
                    .filter(PrivateSetting.name == "api_allowed_hosts")
                    .one()
                )
                return (
                    jsonify({"data": setting.value}),  ######
                    200,
                    {"ContentType": "application/json"},
                )
            except sqlalchemy.exc.NoResultFound as error:
                Session.rollback()
                return (
                    jsonify({"data": []}),
                    200,
                    {"ContentType": "application/json"},
                )
            except Exception as error:
                logger.error(
                    f"Setting lookup failed for allowed API hosts: {error}"
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
        case "POST":
            try:
                setting = (
                    Session.query(PrivateSetting)
                    .filter(PrivateSetting.name == "api_allowed_hosts")
                    .one()
                )
                existing = setting.value
                existing.append(request.json.get("host", None))
                Session.execute(
                    sqlalchemy.update(PrivateSetting)
                    .where(PrivateSetting.name == "api_allowed_hosts")
                    .values(value=existing)
                )
                Session.commit()
                return (
                    jsonify({"success": True}),
                    200,
                    {"ContentType": "application/json"},
                )
            except sqlalchemy.exc.NoResultFound as error:
                try:
                    setting = PrivateSetting(
                        name="api_allowed_hosts",
                        value=[request.json.get("host", None)],
                        description="Allowed API hosts",
                        deletable=True,
                    )
                    Session.add(setting)
                    Session.commit()
                    return (
                        jsonify({"success": True}),
                        200,
                        {"ContentType": "application/json"},
                    )
                except Exception as error:
                    logger.error(
                        f"Setting lookup failed for allowed API hosts: {error}"
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
        case "DELETE":
            try:
                setting = (
                    Session.query(PrivateSetting)
                    .filter(PrivateSetting.name == "api_allowed_hosts")
                    .one()
                )
                existing = setting.value
                existing.remove(request.json.get("host", None))
                Session.execute(
                    sqlalchemy.update(PrivateSetting)
                    .where(PrivateSetting.name == "api_allowed_hosts")
                    .values(value=existing)
                )
                Session.commit()
                return (
                    jsonify({"success": True}),
                    200,
                    {"ContentType": "application/json"},
                )
            except Exception as error:
                logger.error(f"Delete failed for allowed API hosts: {error}")
                Session.rollback()
                return (
                    jsonify({"error": str(error)}),
                    500,
                    {"ContentType": "application/json"},
                )
            finally:
                Session.close()
                Session.remove()
