from fastapi import APIRouter, Depends, HTTPException, status
from incidentbot.api.deps import get_current_active_superuser
from incidentbot.configuration.settings import settings
from incidentbot.models.response import SuccessResponse
from incidentbot.scheduler.core import (
    process as TaskScheduler,
    scrape_for_aging_incidents,
)
from incidentbot.slack.client import (
    store_slack_channel_list_db,
    store_slack_user_list_db,
)

router = APIRouter()


protected_jobs = [
    "scrape_for_aging_incidents",
    "update_opsgenie_oc_data",
    "update_pagerduty_oc_data",
    "update_slack_channel_list",
    "update_slack_user_list",
]


@router.get(
    "/job",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=status.HTTP_200_OK,
)
async def get_jobs() -> list[dict]:
    try:
        return [
            {
                "id": job.id,
                "name": job.name,
                "function": job.func_ref,
                "trigger": str(job.trigger),
                "next_run": str(job.next_run_time),
            }
            for job in TaskScheduler.list_jobs()
        ]
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.post(
    "/job/run/{job_id}",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=status.HTTP_200_OK,
)
async def run_job(job_id) -> SuccessResponse:
    match job_id:
        case "scrape_for_aging_incidents":
            try:
                scrape_for_aging_incidents()
            except Exception as error:
                raise HTTPException(status_code=500, detail=str(error))
        case "update_opsgenie_oc_data":
            if (
                settings.integrations
                and settings.integrations.atlassian
                and settings.integrations.atlassian.opsgenie
                and settings.integrations.atlassian.opsgenie.enabled
            ):
                from incidentbot.opsgenie.api import OpsgenieAPI

                try:
                    api = OpsgenieAPI()
                    api.store_on_call_data()
                except Exception as error:
                    raise HTTPException(status_code=500, detail=str(error))
            else:
                raise HTTPException(
                    status_code=500,
                    detail="opsgenie integration not enabled",
                )
        case "update_pagerduty_oc_data":
            if (
                settings.integrations
                and settings.integrations.pagerduty
                and settings.integrations.pagerduty.enabled
            ):
                from incidentbot.pagerduty.api import PagerDutyInterface

                pagerduty_interface = PagerDutyInterface()

                try:
                    pagerduty_interface.store_on_call_data()
                except Exception as error:
                    raise HTTPException(status_code=500, detail=str(error))
            else:
                raise HTTPException(
                    status_code=500,
                    detail="pagerduty integration not enabled",
                )
        case "update_slack_channel_list":
            try:
                store_slack_channel_list_db()
            except Exception as error:
                raise HTTPException(status_code=500, detail=str(error))
        case "update_slack_user_list":
            try:
                store_slack_user_list_db()
            except Exception as error:
                raise HTTPException(status_code=500, detail=str(error))
        case _:
            raise HTTPException(
                status_code=500, detail=f"{job_id} is not a valid option"
            )

    return SuccessResponse(result="success", message="job ran successfully")


@router.delete(
    "/job/run/{job_id}",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=status.HTTP_200_OK,
)
async def delete_job(job_id) -> SuccessResponse:
    if job_id not in protected_jobs:
        try:
            TaskScheduler.delete_job(job_id)

            return SuccessResponse(result="success", message="job deleted")
        except Exception as error:
            raise HTTPException(status_code=500, detail=str(error))
    else:
        raise HTTPException(
            status_code=500, detail=f"{job_id} cannot be deleted"
        )
