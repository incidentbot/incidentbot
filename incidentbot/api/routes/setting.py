from fastapi import APIRouter, Depends, HTTPException, status
from incidentbot.api.deps import get_current_active_superuser, SessionDep
from incidentbot.models.database import ApplicationData
from incidentbot.slack.client import slack_workspace_id
from sqlalchemy.exc import NoResultFound
from sqlmodel import select

router = APIRouter()


@router.get(
    "/setting",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=status.HTTP_200_OK,
)
def get_settings(session: SessionDep) -> list[ApplicationData]:
    try:

        settings = session.exec(select(ApplicationData)).all()

        return settings
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.get(
    "/setting/{setting_name}",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=status.HTTP_200_OK,
)
def get_setting(session: SessionDep, setting_name: str) -> ApplicationData:
    match setting_name:
        case "slack_users":
            data = session.exec(
                select(ApplicationData).filter(
                    ApplicationData.name == "slack_users"
                )
            ).first()

            return ApplicationData(name="slack_users", value=data.json_data)
        case "slack_workspace_id":
            return ApplicationData(
                name="slack_workspace_id", value=[slack_workspace_id]
            )
        case _:
            try:
                setting = session.exec(
                    select(ApplicationData.name == setting_name)
                ).first()

                return setting
            except NoResultFound:
                raise HTTPException(
                    status_code=404, detail="setting not found"
                )
            except Exception as error:
                raise HTTPException(status_code=500, detail=str(error))
