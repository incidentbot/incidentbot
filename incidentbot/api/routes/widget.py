from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).parent.parent.parent / "templates")
)


@router.get("/widget/incident", response_class=HTMLResponse)
async def incident_widget(request: Request):
    """Serve the incident creation widget for embedding in Matrix/Element."""
    return templates.TemplateResponse(
        "incident_widget.html",
        {"request": request},
    )
