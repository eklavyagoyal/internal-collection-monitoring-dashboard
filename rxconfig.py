"""Reflex configuration for Nexus-Track."""

import os

import reflex as rx
from dotenv import load_dotenv

load_dotenv()

config = rx.Config(
    app_name="nexus_track",
    api_url=os.getenv("API_URL", "http://localhost:8000"),
    state_manager_redis_url=os.getenv("REDIS_URL"),
)
