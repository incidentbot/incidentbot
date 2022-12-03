import config
import json
import logging

from datetime import datetime, timedelta, timezone
from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    get_current_user,
    get_jwt,
    get_jwt_identity,
    jwt_required,
    verify_jwt_in_request,
    JWTManager,
)
from bot.models.pg import OperationalData, Session
from bot.api.flask import app
from bot.models.pg import Session, TokenBlocklist, User
from bot.models.user import (
    db_user_adj_admin,
    db_user_create,
    db_user_delete,
    db_user_disable,
    db_user_enable,
    db_user_lookup,
    db_user_token_revoke,
)
from werkzeug.security import generate_password_hash, check_password_hash

user = Blueprint("user", __name__)

logger = logging.getLogger("auth-router")

# jwt

jwt = JWTManager(app)


@jwt.user_identity_loader
def user_identity_lookup(user):
    return user.id


@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    identity = jwt_data["sub"]
    return Session.query(User).filter_by(id=identity).one_or_none()


# Callback function to check if a JWT exists in the database blocklist
@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload: dict) -> bool:
    jti = jwt_payload["jti"]
    token = Session.query(TokenBlocklist.id).filter_by(jti=jti).scalar()
    return token is not None


@user.after_request
def refresh_expiring_jwts(response):
    try:
        exp_timestamp = get_jwt()["exp"]
        now = datetime.now(timezone.utc)
        target_timestamp = datetime.timestamp(now + timedelta(minutes=30))
        if target_timestamp > exp_timestamp:
            access_token = create_access_token(identity=get_jwt_identity())
            data = response.get_json()
            if type(data) is dict:
                data["access_token"] = access_token
                response.data = jsonify(data)
        return response
    except (RuntimeError, KeyError):
        # Case where there is not a valid JWT. Just return the original respone
        return response


"""
Routes
"""


@user.route("/user/validate", methods=["POST"])
def validate_token():
    try:
        verify_jwt_in_request(locations=["headers"])
        return (
            jsonify({"valid": True}),
            200,
            {"ContentType": "application/json"},
        )
    except Exception as error:
        return (
            jsonify({"valid": False}),
            401,
            {"ContentType": "application/json"},
        )


@user.route("/user/login", methods=["POST"])
def create_token():
    email = request.json.get("email", None)
    password = request.json.get("password", None)
    user = db_user_lookup(email=email)
    if not user:
        return (
            jsonify({"error": "User does not exist."}),
            401,
            {"ContentType": "application/json"},
        )
    if user and not check_password_hash(user.password, password):
        return (
            jsonify({"error": "Incorrect password."}),
            401,
            {"ContentType": "application/json"},
        )
    if user and user.is_disabled:
        return (
            jsonify({"error": "This account has been locked."}),
            401,
            {"ContentType": "application/json"},
        )
    access_token = create_access_token(identity=user)
    return (
        jsonify(
            {
                "success": True,
                "access_token": access_token,
                "user_data": json.dumps(
                    {
                        "name": user.name,
                        "email": user.email,
                        "role": user.role,
                        "is_admin": user.is_admin,
                    }
                ),
            }
        ),
        200,
        {"ContentType": "application/json"},
    )


@user.route("/user/logout", methods=["DELETE"])
@jwt_required(verify_type=False)
def logout():
    token = get_jwt()
    jti = token["jti"]
    ttype = token["type"]
    now = datetime.now(timezone.utc)
    db_user_token_revoke(
        jti=jti, ttype=ttype, user_id=get_current_user().id, created_at=now
    )
    return (
        jsonify({"success": True}),
        200,
        {"ContentType": "application/json"},
    )


@user.route("/user/list", methods=["GET"])
@jwt_required()
def return_user_list():
    users = db_user_lookup(all=True)
    user_details = []
    for u in users:
        user_details.append(
            {
                "id": u.id,
                "email": u.email,
                "name": u.name,
                "role": u.role,
                "is_admin": u.is_admin,
                "is_disabled": u.is_disabled,
            }
        )
    return (
        jsonify(user_details),
        200,
        {"ContentType": "application/json"},
    )


@user.route("/user/change/<user_id>", methods=["DELETE", "PATCH"])
@jwt_required()
def adjust_user(user_id):
    user = db_user_lookup(id=user_id)
    if request.method == "DELETE":
        success, error = db_user_delete(email=user.email)
        if success:
            return (
                jsonify({"success": True}),
                200,
                {"ContentType": "application/json"},
            )
        else:
            return (
                jsonify({"error": user}),
                500,
                {"ContentType": "application/json"},
            )
    elif request.method == "PATCH":
        data = request.json
        toggle = data["set_to"]
        if toggle == "enabled":
            success, error = db_user_enable(email=user.email)
            if success:
                return (
                    jsonify({"success": True}),
                    200,
                    {"ContentType": "application/json"},
                )
            else:
                return (
                    jsonify({"error": error}),
                    500,
                    {"ContentType": "application/json"},
                )
        elif toggle == "disabled":
            success, error = db_user_disable(email=user.email)
            if success:
                return (
                    jsonify({"success": True}),
                    200,
                    {"ContentType": "application/json"},
                )
            else:
                return (
                    jsonify({"error": error}),
                    500,
                    {"ContentType": "application/json"},
                )
        elif toggle == "add_admin" or toggle == "remove_admin":
            success, error = db_user_adj_admin(
                email=user.email,
                state=True if toggle == "add_admin" else False,
            )
            if success:
                return (
                    jsonify({"success": True}),
                    200,
                    {"ContentType": "application/json"},
                )
            else:
                return (
                    jsonify({"error": error}),
                    500,
                    {"ContentType": "application/json"},
                )


@user.route("/user/create", methods=["POST"])
@jwt_required()
def create_user():
    data = request.json
    success, error = db_user_create(
        email=data["email"],
        name=data["name"],
        password=generate_password_hash(data["password"], method="sha256"),
        role="user",
    )
    if success:
        return (
            jsonify({"success": True}),
            200,
            {"ContentType": "application/json"},
        )
    else:
        return (
            jsonify({"error": error}),
            500,
            {"ContentType": "application/json"},
        )


@user.route("/user/slack_users", methods=["GET"])
@jwt_required()
def get_slack_users():
    try:
        data = (
            Session.query(OperationalData)
            .filter(OperationalData.id == "slack_users")
            .one()
            .serialize()
        )
        return (
            jsonify({"data": data["json_data"]}),
            200,
            {"ContentType": "application/json"},
        )
    except Exception as error:
        return (
            jsonify({"error": str(error)}),
            500,
            {"ContentType": "application/json"},
        )


default_account_email = "admin@admin.com"
admin_user = db_user_lookup(email=default_account_email)
if not admin_user:
    success, error = db_user_create(
        email=default_account_email,
        password=generate_password_hash(
            config.default_admin_password, method="sha256"
        ),
        name="administrator",
        role="administrator",
        is_admin=True,
    )
    if success:
        logger.info(
            f"Default admin account {default_account_email} created with the value supplied"
        )
    else:
        logger.error(f"Error creating default admin account: {error}")
