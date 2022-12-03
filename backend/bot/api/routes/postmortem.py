import logging
import psycopg2
import sqlalchemy

from bot.models.pg import PostmortemSettings, Session
from flasgger import swag_from
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from http import HTTPStatus

logger = logging.getLogger(__name__)

postmortem = Blueprint("postmortem", __name__)


@postmortem.route(
    "/postmortem/setting/<name>", methods=["GET", "POST", "PATCH", "DELETE"]
)
@jwt_required()
@swag_from(
    {
        "responses": {
            HTTPStatus.OK.value: {
                "description": "Welcome to the Flask Starter Kit",
                "schema": "{}",
            }
        }
    }
)
def handle_postmortem(name):
    if request.method == "GET":
        try:
            postmortem = (
                Session.query(PostmortemSettings)
                .filter(PostmortemSettings.id == name)
                .one()
            )
            return (
                jsonify({"data": postmortem.data}),
                200,
                {"ContentType": "application/json"},
            )
        except sqlalchemy.exc.NoResultFound as error:
            Session.rollback()
            return (
                jsonify({"error": "postmortem setting not found"}),
                500,
                {"ContentType": "application/json"},
            )
        except Exception as error:
            logger.error(
                f"postmortem setting lookup failed for {name}: {error}"
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
    elif request.method == "POST":
        value = request.json["value"]
        try:
            postmortem = PostmortemSettings(
                id=name,
                data=value,
            )
            Session.add(postmortem)
            Session.commit()
            return (
                jsonify({"success": "stored"}),
                200,
                {"ContentType": "application/json"},
            )
        except sqlalchemy.exc.IntegrityError:
            Session.rollback()
            return (
                jsonify(
                    {
                        "error": "postmortem setting already exists, use PATCH to update it"
                    }
                ),
                500,
                {"ContentType": "application/json"},
            )
        except psycopg2.errors.UniqueViolation:
            Session.rollback()
            return (
                jsonify(
                    {
                        "error": "postmortem setting already exists, use PATCH to update it"
                    }
                ),
                500,
                {"ContentType": "application/json"},
            )
        except Exception as error:
            logger.error(f"postmortem create failed for {name}: {error}")
            Session.rollback()
            return (
                jsonify({"error": str(error)}),
                500,
                {"ContentType": "application/json"},
            )
        finally:
            Session.close()
            Session.remove()
    elif request.method == "PATCH":
        value = request.json["value"]
        try:
            postmortem = (
                Session.query(PostmortemSettings)
                .filter(PostmortemSettings.id == name)
                .one()
            )
            postmortem.data = value
            Session.commit()
            # try:
            #     success, error = update_template(new_body=value)
            #     if not success:
            #         return (
            #             jsonify({"error": str(error)}),
            #             500,
            #             {"ContentType": "application/json"},
            #         )
            # except Exception as error:
            #     logger.info(f"Error updating template: {error}")
            #     return (
            #         jsonify({"error": str(error)}),
            #         500,
            #         {"ContentType": "application/json"},
            #     )
            # return (
            #     jsonify({"success": "updated"}),
            #     200,
            #     {"ContentType": "application/json"},
            # )
        except Exception as error:
            logger.error(
                f"postmortem setting update failed for {name}: {error}"
            )
            return (
                jsonify({"error": str(error)}),
                500,
                {"ContentType": "application/json"},
            )
        finally:
            Session.close()
            Session.remove()
    elif request.method == "DELETE":
        try:
            postmortem = (
                Session.query(PostmortemSettings)
                .filter(PostmortemSettings.id == name)
                .one()
            )
            Session.delete(postmortem)
            Session.commit()
            return (
                jsonify({"success": "deleted"}),
                200,
                {"ContentType": "application/json"},
            )
        except Exception as error:
            logger.error(
                f"postmortem setting update failed for {name}: {error}"
            )
            return (
                jsonify({"error": str(error)}),
                500,
                {"ContentType": "application/json"},
            )
        finally:
            Session.close()
            Session.remove()
