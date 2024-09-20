import sqlalchemy

from incidentbot.logging import logger
from incidentbot.models.database import engine, Setting
from sqlmodel import Session, select
from typing import Dict


def read_single_setting_value(name: str) -> Dict:
    with Session(engine) as session:
        try:
            setting = session.exec(
                select(Setting).filter(Setting.name == name)
            ).first()

            return setting.value
        except sqlalchemy.exc.NoResultFound as error:
            logger.error(f"Setting lookup failed for {name}: {error}")
            return {}
        except Exception as error:
            logger.error(f"Setting lookup failed for {name}: {error}")
            return {}
