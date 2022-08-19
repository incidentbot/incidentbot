import logging
import sqlalchemy

from bot.models.pg import Setting, Session
from typing import Dict

logger = logging.getLogger(__name__)


def read_single_setting_value(name: str) -> Dict:
    try:
        setting = Session.query(Setting).filter(Setting.name == name).one()
        return setting.value
    except sqlalchemy.exc.NoResultFound as error:
        logger.error(f"Setting lookup failed for {name}: {error}")
        Session.rollback()
        return {}
    except Exception as error:
        logger.error(f"Setting lookup failed for {name}: {error}")
        Session.rollback()
        return {}
    finally:
        Session.close()
        Session.remove()
