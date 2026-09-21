"""Ponto de entrada usado por servidores WSGI de produção (ex.: gunicorn)."""
from app import create_app

app = create_app("production")
