"""Settings for the project."""
import os
from pathlib import Path
from dotenv import dotenv_values

PROJECT_PATH = Path(__file__).parent.parent
ENV_PATH = PROJECT_PATH / ".env"
config_env = dotenv_values(ENV_PATH)

REDDIT_SECRET = os.getenv(
    "REDDIT_SECRET", config_env.get("REDDIT_SECRET"))
REDDIT_CLIENT_ID = os.getenv(
    "REDDIT_CLIENT_ID", config_env.get("REDDIT_CLIENT_ID"))
REDDIT_APP_NAME = os.getenv(
    "REDDIT_APP_NAME", config_env.get("REDDIT_APP_NAME"))


RABBIT_HOST = os.getenv(
    "RABBIT_HOST", config_env.get("RABBIT_HOST"))
RABBIT_USER = os.getenv(
    "RABBIT_USER", config_env.get("RABBIT_USER"))
RABBIT_PASSWORD = os.getenv(
    "RABBIT_PASSWORD", config_env.get("RABBIT_PASSWORD"))
