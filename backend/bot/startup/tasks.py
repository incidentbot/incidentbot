import config
import json
import logging

from bot.models.pg import OperationalData, Session, Setting
from bot.scheduler.scheduler import update_slack_user_list
from bot.shared import tools
from sqlalchemy import exc, update

logger = logging.getLogger(__name__)


def startup_task_init():
    """
    When the app is started for the first time, run the following jobs automatically

    Run this on each start to synchronize other tasks
    """
    try:
        # init_job
        row = Session.query(Setting).filter(Setting.name == "init_job").one()
        ans = row.value["has_run"]
        has_run = bool(ans)
    except exc.NoResultFound:
        has_run = False
    finally:
        # pending_changes
        if not Session.query(Setting).filter(Setting.name == "application_state").all():
            pc = Setting(
                name="application_state",
                value={"pending_changes": False},
                deletable=False,
            )
            Session.add(pc)
            Session.commit()
        else:
            Session.execute(
                update(Setting)
                .where(Setting.name == "application_state")
                .values(value={"pending_changes": False})
            )
            Session.commit()

        # init_job
        if not has_run:
            # If the init job has already run, skip it
            logger.info("Running startup jobs for app init...")

            # Populate list of Slack users
            update_slack_user_list()

            # Optionally populate PagerDuty on-call data and sete auto-page option if integration is enabled
            if config.pagerduty_integration_enabled != "false":
                from bot.scheduler.scheduler import update_pagerduty_oc_data

                update_pagerduty_oc_data()

                try:
                    auto_page_teams = OperationalData(
                        id="auto_page_teams",
                        json_data={"teams": []},
                    )
                    Session.add(auto_page_teams)
                    Session.commit()
                except Exception as error:
                    logger.error(f"Error storing auto_page_teams: {error}")
                finally:
                    Session.close()
                    Session.remove()
            # Store default severity level definitions
            try:
                severity_levels = Setting(
                    name="severity_levels",
                    value=tools.read_json_from_file(
                        f"{config.templates_directory}severity_levels.json"
                    ),
                    description="Shortnames and description of severity levels available for incidents.",
                    deletable=False,
                )
                Session.add(severity_levels)
                Session.commit()
            except Exception as error:
                logger.error(f"Error storing severity_levels: {error}")
            finally:
                Session.close()
                Session.remove()

            # Store default role definitions
            try:
                role_definitions = Setting(
                    name="role_definitions",
                    value=tools.read_json_from_file(
                        f"{config.templates_directory}role_definitions.json"
                    ),
                    description="Names and description of incident participant roles.",
                    deletable=False,
                )
                Session.add(role_definitions)
                Session.commit()
            except Exception as error:
                logger.error(f"Error storing role_definitions: {error}")
            finally:
                Session.close()
                Session.remove()

            # Store default incident configuration parameters
            try:
                severity_levels = Setting(
                    name="incident_management_configuration",
                    value={
                        "incident_channel_topic": "This is the default incident channel topic. You can edit it in settings.",
                        "incident_guide_link": "https://changeme.com",
                        "incident_postmortems_link": "https://changeme.com",
                        "zoom_link": "https://zoom.us",
                    },
                    description="Various settings to control Incident Management functionality.",
                    deletable=False,
                )
                Session.add(severity_levels)
                Session.commit()
            except Exception as error:
                logger.error(f"Error storing severity_levels: {error}")
            finally:
                Session.close()
                Session.remove()

            # Update init_job has_run value
            try:
                row = Session.query(Setting).filter(Setting.name == "init_job").one()
                row.value = {"has_run": True}
                Session.commit()
            except exc.NoResultFound:
                update_setting = Setting(
                    name="init_job",
                    value={"has_run": True},
                    description="Set by the application after first startup. Changing to false will re-run startup tasks.",
                    deletable=False,
                )
                Session.add(update_setting)
                Session.commit()
            except Exception as error:
                logger.error(f"Error running init jobs: {error}")
            finally:
                Session.close()
                Session.remove()
