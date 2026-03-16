from fastapi import FastAPI
from app.core.exceptions import register_exception_handlers

app = FastAPI(title="Archive API")

register_exception_handlers(app)