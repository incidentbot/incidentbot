import logging
import sqlalchemy

from bot.models.pg import OperationalData, Session

logger = logging.getLogger(__name__)


def read_pager_auto_page_targets():
    name = "auto_page_teams"
    try:
        res = (
            Session.query(OperationalData)
            .filter(OperationalData.id == name)
            .one()
        )
        targets = res.json_data["teams"]
        mappings = (
            Session.query(OperationalData)
            .filter(OperationalData.id == "pagerduty_auto_mapping")
            .one()
            .json_data
        )
        return [{t: mappings[t]} for t in targets]
    except sqlalchemy.exc.NoResultFound as error:
        logger.error(f"Setting lookup failed for {name}: {error}")
        Session.rollback()
    except Exception as error:
        logger.error(f"Setting lookup failed for {name}: {error}")
        Session.rollback()
    finally:
        Session.close()
        Session.remove()
