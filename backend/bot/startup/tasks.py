import config
import logging

from bot.models.pg import OperationalData, Session, Setting
from bot.scheduler.scheduler import update_slack_user_list
from sqlalchemy import exc, update

logger = logging.getLogger("startup.tasks")


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
        if (
            not Session.query(Setting)
            .filter(Setting.name == "application_state")
            .all()
        ):
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
            if "pagerduty" in config.active.integrations:
                from bot.scheduler.scheduler import update_pagerduty_oc_data

                update_pagerduty_oc_data()

                try:
                    if (
                        not Session.query(OperationalData)
                        .filter(OperationalData.id == "auto_page_teams")
                        .all()
                    ):
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

            # Update init_job has_run value
            try:
                row = (
                    Session.query(Setting)
                    .filter(Setting.name == "init_job")
                    .one()
                )
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
