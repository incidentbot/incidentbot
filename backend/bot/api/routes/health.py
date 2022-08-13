from flask import Blueprint, jsonify

health_check = Blueprint("health_check", __name__)


@health_check.route("/health", methods=["GET"])
def get_health():
    return (
        jsonify({"healthy": True}),
        200,
        {"ContentType": "application/json"},
    )
