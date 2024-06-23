import secrets
import sqlalchemy

from bot.models.pg import PrivateSetting, Session
from bot.utils import utils
from flask import abort, Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from functools import wraps
from logger import logger

auth = Blueprint("auth", __name__)


class ApiKey:
    @staticmethod
    def generate() -> str:
        return secrets.token_urlsafe(20)


def api_key_required(func):
    """Decorator to verify a valid API key is provided on a route"""

    @wraps(func)
    def decorated_function(*args, **kwargs):
        # Determine whether or not there's an active API key
        try:
            active_api_key = (
                Session.query(PrivateSetting)
                .filter(PrivateSetting.name == "active_api_key")
                .one()
                .value
            )
        except sqlalchemy.exc.NoResultFound:
            return (
                jsonify({"error": "There are no active API keys."}),
                401,
                {"ContentType": "application/json"},
            )
        # Determine if there are any allowed host entries
        try:
            api_allowed_hosts = (
                Session.query(PrivateSetting)
                .filter(PrivateSetting.name == "api_allowed_hosts")
                .one()
                .value
            )
        except sqlalchemy.exc.NoResultFound:
            api_allowed_hosts = []
        # Process API request
        if (
            request.headers.get("Authorization")
            and request.headers.get("Authorization")
            == f"Bearer {active_api_key}"
        ):
            if len(api_allowed_hosts) > 0:
                for host in api_allowed_hosts:
                    if utils.validate_ip_in_subnet(
                        request.access_route[-1], host
                    ):
                        return func(*args, **kwargs)
                else:
                    return (
                        jsonify({"error": "Host not allowed."}),
                        401,
                        {"ContentType": "application/json"},
                    )
            else:
                return func(*args, **kwargs)
        else:
            abort(401)

    return decorated_function


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
            submission = request.json.get("host", None)
            if utils.validate_ip_address(submission):
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
            else:
                return (
                    jsonify({"error": "not a valid ip address"}),
                    500,
                    {"ContentType": "application/json"},
                )
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
