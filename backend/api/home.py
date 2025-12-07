from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse


router = APIRouter()

templates = Jinja2Templates(directory="backend/templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Router endpoint para la página principal.

    Usa la capa de servicios para obtener el mensaje y renderiza la plantilla.
    """
    message = "Hola, bienvenido a App-Finanzas - Demo!"
    return templates.TemplateResponse("index.html", {"request": request, "message": message})

