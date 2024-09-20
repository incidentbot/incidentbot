from fastapi import APIRouter, Depends, HTTPException, status
from incidentbot.api.deps import get_current_active_superuser, SessionDep
from incidentbot.logging import logger
from incidentbot.models.database import (
    MaintenanceWindowRecord,
)
from pydantic import BaseModel
from sqlalchemy.exc import NoResultFound
from sqlmodel import select

router = APIRouter()


class MaintenanceWindows(BaseModel):
    data: list[MaintenanceWindowRecord]
    count: int


@router.get(
    "/maintenance_window",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=status.HTTP_200_OK,
)
async def get_maintenance_windows(session: SessionDep) -> MaintenanceWindows:
    try:
        maintenance_windows = session.exec(
            select(MaintenanceWindowRecord)
        ).all()

        return MaintenanceWindows(
            data=maintenance_windows, count=len(maintenance_windows)
        )
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.get(
    "/maintenance_window/{id}",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=status.HTTP_200_OK,
)
async def get_maintenance_window(session: SessionDep, id: str):
    try:
        maintenance_window = session.exec(
            select(MaintenanceWindowRecord).filter(
                MaintenanceWindowRecord.id == id
            )
        ).one()

        return maintenance_window
    except NoResultFound:
        raise HTTPException(
            status_code=404, detail="maintenance window not found"
        )
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.delete(
    "/maintenance_window",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=status.HTTP_200_OK,
)
async def delete_maintenance_window(
    session: SessionDep, maintenance_window: MaintenanceWindowRecord
):
    try:
        record = session.exec(
            select(MaintenanceWindowRecord).filter(
                MaintenanceWindowRecord.id == maintenance_window.id
            )
        ).one()

        logger.info(f"Deleting maintenance window {maintenance_window.title}")
        session.delete(record)
        session.commit()
    except NoResultFound:
        raise HTTPException(
            status_code=404, detail="maintenance window not found"
        )
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.patch(
    "/maintenance_window/{field}",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=status.HTTP_200_OK,
)
def patch_maintenance_window(
    maintenance_window: MaintenanceWindowRecord, field: str
):
    """
    Field is the value being changed:
    """

    match field:
        case _:
            pass
