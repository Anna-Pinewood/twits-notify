"""Settings for the project."""
import os
from pathlib import Path
from dotenv import dotenv_values

PROJECT_PATH = Path(__file__).parent.parent
ENV_PATH = PROJECT_PATH / ".env"
config_env = dotenv_values(ENV_PATH)

TWITTER_API_KEY = os.getenv(
    "TWITTER_API_KEY", config_env.get("TWITTER_API_KEY"))
TWITTER_API_KEY_SECRET = os.getenv(
    "TWITTER_API_KEY_SECRET", config_env.get("TWITTER_API_KEY_SECRET"))