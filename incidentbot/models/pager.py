import sqlalchemy

from incidentbot.logging import logger
from incidentbot.models.database import engine, ApplicationData
from pydantic import BaseModel
from sqlmodel import Session, select


class PagerAutoMappingRequest(BaseModel):
    value: str


def read_pager_auto_page_targets():
    name = "auto_page_teams"

    try:
        with Session(engine) as session:
            res = session.exec(
                select(ApplicationData).filter(ApplicationData.name == name)
            ).first()

            targets = res.json_data["teams"]
            mappings = (
                session.exec(
                    select(ApplicationData).filter(
                        ApplicationData.name == "pagerduty_auto_mapping"
                    )
                )
                .one()
                .json_data
            )

            return [{t: mappings[t]} for t in targets]
    except sqlalchemy.exc.NoResultFound as error:
        logger.error(f"Setting lookup failed for {name}: {error}")
    except Exception as error:
        logger.error(f"Setting lookup failed for {name}: {error}")
