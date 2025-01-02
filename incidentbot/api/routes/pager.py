from fastapi import APIRouter, Depends, HTTPException, status
from incidentbot.api.deps import get_current_active_superuser, SessionDep
from incidentbot.configuration.settings import settings
from incidentbot.models.database import ApplicationData
from incidentbot.models.pager import PagerAutoMappingRequest
from incidentbot.models.response import (
    PagerDataResponse,
    SuccessResponse,
)
from sqlmodel import select

router = APIRouter()


@router.get(
    "/pager",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=status.HTTP_200_OK,
)
def get_pager(session: SessionDep) -> PagerDataResponse | SuccessResponse:
    if (
        settings.integrations
        and settings.integrations.atlassian
        and settings.integrations.atlassian.opsgenie
        and settings.integrations.atlassian.opsgenie.enabled
    ):
        try:

            data = (
                session.exec(select(ApplicationData))
                .filter(ApplicationData.name == "opsgenie_oc_data")
                .first()
            )

            return PagerDataResponse(
                platform="opsgenie",
                data=data.json_data,
                ts=data.updated_at,
            )
        except Exception as error:
            raise HTTPException(status_code=500, detail=str(error))
    elif (
        settings.integrations
        and settings.integrations.pagerduty
        and settings.integrations.pagerduty.enabled
    ):
        try:

            data = (
                session.exec(select(ApplicationData))
                .filter(ApplicationData.name == "pagerduty_oc_data")
                .first()
            )

            return PagerDataResponse(
                platform="pagerduty",
                data=data.json_data,
                ts=data.updated_at,
            )
        except Exception as error:
            raise HTTPException(status_code=500, detail=str(error))

    return SuccessResponse(result="success", message="feature_not_enabled")


@router.get(
    "/pager/auto_map",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=status.HTTP_200_OK,
)
def get_pager_automapping(session: SessionDep) -> dict | SuccessResponse:
    if (
        settings.integrations
        and settings.integrations.pagerduty
        and settings.integrations.pagerduty.enabled
    ):
        try:

            data = session.exec(
                select(ApplicationData)
                .filter(ApplicationData.name == "pagerduty_auto_mapping")
                .one()
            )

            return {"data": data.json_data, "ts": data.updated_at}
        except Exception as error:
            raise HTTPException(status_code=500, detail=str(error))

    return SuccessResponse(result="success", message="feature_not_enabled")


@router.get(
    "/pager/auto_map/store",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=status.HTTP_200_OK,
)
def get_pager_store_automapping(session: SessionDep) -> dict | SuccessResponse:
    if (
        settings.integrations
        and settings.integrations.pagerduty
        and settings.integrations.pagerduty.enabled
    ):
        try:

            data = (
                session.exec(select(ApplicationData))
                .filter(ApplicationData.name == "auto_page_teams")
                .first()
            )

            return {
                "data": data.json_data,
                "ts": data.updated_at,
            }

        except Exception as error:
            raise HTTPException(status_code=500, detail=str(error))
    else:
        return SuccessResponse(result="success", message="feature_not_enabled")


@router.patch(
    "/pager/auto_map/store",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=status.HTTP_200_OK,
)
def patch_pager_automapping(
    session: SessionDep,
    request: PagerAutoMappingRequest,
) -> SuccessResponse:
    if (
        settings.integrations
        and settings.integrations.pagerduty
        and settings.integrations.pagerduty.enabled
    ):
        v = request.json["value"]
        try:

            data = (
                session.exec(select(ApplicationData))
                .filter(ApplicationData.name == "auto_page_teams")
                .first()
            )
            data.json_data = {"teams": v}
            session.commit()

            return SuccessResponse(result="success", message="data stored")
        except Exception as error:
            raise HTTPException(status_code=500, detail=str(error))
    else:
        return SuccessResponse(result="success", message="feature_not_enabled")
