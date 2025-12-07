from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.api.home import router as home_router


app = FastAPI(title="App-Finanzas - Demo")

# Static files (css/js)
app.mount("/static", StaticFiles(directory="backend/static"), name="static")

# Registrar routers (estructura -> `backend/api/`)
app.include_router(home_router)
