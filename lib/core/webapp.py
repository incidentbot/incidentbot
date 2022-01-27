import flask_login
import logging

from __main__ import app, config, task_scheduler
from ..core import action_parameters as ap, incident_management as incmgmt
from ..db import db
from ..incident import routes as inc
from ..shared import tools
from ..slack import slack_tools
from flask import abort, flash, redirect, render_template, request, url_for
from urllib.parse import urlparse, urljoin
from werkzeug.security import generate_password_hash, check_password_hash

logger = logging.getLogger(__name__)

"""
Flask LoginManager
"""

# Set secret key in Flask app since this is required
app.secret_key = bytes(config.flask_app_secret_key, "UTF-8")

# Initialize LoginManager to handle webapp logins
login_manager = flask_login.LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.session_protection = "strong"

# LoginManager Objects
def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


class User(flask_login.UserMixin):
    pass


@login_manager.user_loader
def user_loader(user_id):
    return db.db_user_lookup(id=int(user_id))


def create_default_admin_account():
    try:
        user = db.db_user_lookup(email="admin@admin.com")
        if not (user):
            logger.info("Creating default user...")
            db.db_user_create(
                email="admin@admin.com",
                name="admin",
                password=generate_password_hash("admin", method="sha256"),
                role="Admin",
                is_admin=True,
            )
        elif user:
            if user.is_disabled:
                pass
            else:
                logger.info("Default user already exists.")
    except Exception as error:
        logger.error(f"Error looking up default user: {error}")


"""
Web application routes
"""
signups_enabled = False

# Pass vars to all rendered templates. Signups disabled by default, set to True to change.
# botname here is what is rendered on pages where the bot name is referenced.
@app.context_processor
def inject_vars():
    return dict(
        user=flask_login.current_user,
        signups_enabled=signups_enabled,
        botname="Incident Bot",
    )


@app.route("/admin")
@flask_login.login_required
def index():
    return render_template("/webapp/index.html", config=config)


@app.route("/admin/login", methods=["GET"])
def login():
    # Grab next param and verify server is the same
    next = request.args.get("next")
    if not is_safe_url(next):
        return abort(400)
    return render_template("/webapp/login.html")


@app.route("/admin/login", methods=["POST"])
def login_post():
    # login code goes here
    email = request.form.get("email")
    password = request.form.get("password")
    remember = True if request.form.get("remember") else False

    user = db.db_user_lookup(email=email)

    # check if the user actually exists
    # take the user-supplied password, hash it, and compare it to the hashed password in the database
    if not user or not check_password_hash(user.password, password) or user.is_disabled:
        flash("Please check your login details and try again.")
        return redirect(
            url_for("profile")
        )  # if the user doesn't exist or password is wrong, reload the page

    # if the above check passes, then we know the user has the right credentials
    flask_login.login_user(user, remember=remember)
    return redirect(url_for("index"))


@app.route("/admin/logout")
@flask_login.login_required
def logout():
    flask_login.logout_user()
    return redirect(url_for("login"))


@app.route("/admin/profile")
@flask_login.login_required
def profile():
    return render_template("/webapp/profile.html")


@app.route("/admin/signup")
def signup():
    if signups_enabled:
        return render_template("/webapp/signup.html")
    else:
        return abort(404)


@app.route("/admin/signup", methods=["POST"])
def signup_post():
    email = request.form.get("email")
    name = request.form.get("name")
    password = request.form.get("password")
    role = request.form.get("role")
    user = db.db_user_lookup(email=email)
    if (
        user
    ):  # if a user is found, we want to redirect back to signup page so user can try again
        flash("Email address already exists")
        return redirect(url_for("signup"))
    # create a new user with the form data. Hash the password so the plaintext version isn't saved.
    db.db_user_create(
        email=email,
        name=name,
        password=generate_password_hash(password, method="sha256"),
        role=role,
    )
    flash("Account created. You may now login.")
    return redirect(url_for("login"))


@app.route("/admin/incidents", methods=["GET"])
@flask_login.login_required
def incidents():
    incidents = db.db_read_all_incidents()
    return render_template(
        "/webapp/incidents.html",
        incidents=incidents,
        statuses=config.statuses,
        severities=config.severities,
        slack_workspace_id=config.slack_workspace_id,
        statuspage_url=config.statuspage_url,
    )


@app.route("/admin/tasks", methods=["GET"])
@flask_login.login_required
def tasks():
    tasks = task_scheduler.list_jobs()
    return render_template(
        "/webapp/tasks.html",
        tasks=tasks,
        slack_workspace_id=config.slack_workspace_id,
    )


@app.route("/admin/on_call", methods=["GET"])
@flask_login.login_required
def on_call():
    return render_template("/webapp/on_call.html")


@app.route("/admin/adminpanel", methods=["GET"])
@flask_login.login_required
def adminpanel():
    return render_template(
        "/webapp/adminpanel.html",
        users=db.db_user_lookup(all=True),
    )


@app.route("/admin/backend/create_user", methods=["POST"])
@flask_login.login_required
def admin_new_user_post():
    if flask_login.current_user.is_admin == True:
        email = request.form.get("email")
        name = request.form.get("name")
        password = request.form.get("password")
        role = request.form.get("role")
        is_admin = request.form.get("is_admin")
        user = db.db_user_lookup(email=email)
        if (
            user
        ):  # if a user is found, we want to redirect back to signup page so user can try again
            flash(f"User {email} already exists.")
            return redirect(url_for("adminpanel"))
        # create a new user with the form data. Hash the password so the plaintext version isn't saved.
        db.db_user_create(
            email=email,
            name=name,
            password=generate_password_hash(password, method="sha256"),
            role=role,
            is_admin=bool(is_admin == "on"),
        )
        flash(f"User {email} was created.")
        return redirect(url_for("adminpanel"))
    return abort(401)


@app.route("/admin/backend/delete_user", methods=["POST"])
@flask_login.login_required
def delete_user_post():
    if flask_login.current_user.is_admin == True:
        email = request.form.get("user_email")
        try:
            user = db.db_user_lookup(email=email)
        except Exception as error:
            logger.error(f"Error looking up user for deletion: {error}")
            flash(f"Error: {error}")
        if not (user):  # if a user is not found, we say so
            flash(f"User {email} doesn't exist.")
            return redirect(url_for("adminpanel"))
        try:
            db.db_user_delete(
                email=email,
            )
            flash(f"User {email} was deleted.")
        except Exception as error:
            logger.error(f"Error deleting user {user}: {error}")
            flash(f"Error: {error}")
        return redirect(url_for("adminpanel"))
    return abort(401)


@app.route("/admin/backend/disable_user", methods=["POST"])
@flask_login.login_required
def disable_user_post():
    if flask_login.current_user.is_admin == True:
        email = request.form.get("user_email")
        try:
            user = db.db_user_lookup(email=email)
        except Exception as error:
            logger.error(f"Error looking up user for disable: {error}")
            flash(f"Error: {error}")
        if not (user):  # if a user is not found, we say so
            flash(f"User {email} doesn't exist.")
            return redirect(url_for("adminpanel"))
        # create a new user with the form data. Hash the password so the plaintext version isn't saved.
        try:
            db.db_user_disable(
                email=email,
            )
            flash(f"User {email} was disabled.")
        except Exception as error:
            logger.error(f"Error disabling user {user}: {error}")
            flash(f"Error: {error}")
        return redirect(url_for("adminpanel"))
    return abort(401)


@app.route("/admin/backend/enable_user", methods=["POST"])
@flask_login.login_required
def enable_user_post():
    if flask_login.current_user.is_admin == True:
        email = request.form.get("user_email")
        try:
            user = db.db_user_lookup(email=email)
        except Exception as error:
            logger.error(f"Error looking up user for enable: {error}")
            flash(f"Error: {error}")
        if not (user):  # if a user is not found, we say so
            flash(f"User {email} doesn't exist.")
            return redirect(url_for("adminpanel"))
        try:
            db.db_user_enable(
                email=email,
            )
            flash(f"User {email} was enabled.")
        except Exception as error:
            logger.error(f"Error enabling user {user}: {error}")
            flash(f"Error: {error}")
        return redirect(url_for("adminpanel"))
    return abort(401)


@app.route("/admin/backend/incidents/create_incident", methods=["POST"])
@flask_login.login_required
def create_incident_post():
    description = request.form.get("description")
    request_parameters = {
        "channel": "create",
        "channel_description": description,
        "descriptor": description,
        "user": "internal_auto_create",
        "token": slack_tools.verification_token,
        "created_from_web": True,
    }
    # Create an incident based on the message using the internal path
    try:
        inc.create_incident(internal=False, request_parameters=request_parameters)
        flash(f"Incidented created.")
        return redirect(url_for("incidents"))
    except Exception as error:
        logger.error(f"Error when trying to create an incident: {error}")
        flash(f"Error when trying to create an incident: {error}")
    return redirect(url_for("incidents"))


@app.route("/admin/backend/incidents/update_status", methods=["POST"])
@flask_login.login_required
def set_status_post():
    params = {
        "action_id": "incident.set_incident_status",
        "channel_id": request.form.get("channel_id"),
        "channel_name": request.form.get("channel_name"),
        "timestamp": request.form.get("ts"),
        "user": "webapp",
        "action_value": request.form.get("set_status"),
    }
    incmgmt.set_incident_status(override_dict=params)
    return redirect(url_for("incidents"))


@app.route("/admin/backend/incidents/update_severity", methods=["POST"])
@flask_login.login_required
def set_severity_post():
    params = {
        "action_id": "incident.set_incident_status",
        "channel_id": request.form.get("channel_id"),
        "channel_name": request.form.get("channel_name"),
        "timestamp": request.form.get("ts"),
        "user": "webapp",
        "action_value": request.form.get("set_severity"),
    }
    incmgmt.set_severity(override_dict=params)
    return redirect(url_for("incidents"))
