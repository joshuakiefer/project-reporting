"""FastAPI local service — the bridge between the Python engine and the Tauri frontend."""

from workoptimize.api.server import create_app

__all__ = ["create_app"]
