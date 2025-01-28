"""Settings for the project."""
import os
from pathlib import Path
from dotenv import dotenv_values

PROJECT_PATH = Path(__file__).parent.parent
ENV_PATH = PROJECT_PATH / ".env"
config_env = dotenv_values(ENV_PATH)

RABBIT_HOST = os.getenv(
    "RABBIT_HOST", config_env.get("RABBIT_HOST"))
RABBIT_USER = os.getenv(
    "RABBIT_USER", config_env.get("RABBIT_USER"))
RABBIT_PASSWORD = os.getenv(
    "RABBIT_PASSWORD", config_env.get("RABBIT_PASSWORD"))
RABBIT_QUEUE = os.getenv(
    "RABBIT_QUEUE", config_env.get("RABBIT_QUEUE"))


LLM_MODEL_NAME = os.getenv(
    "LLM_MODEL_NAME", config_env.get("LLM_MODEL_NAME"))
LLM_API_KEY = os.getenv(
    "LLM_API_KEY", config_env.get("LLM_API_KEY"))
LLM_BASE_URL = os.getenv(
    "LLM_BASE_URL", config_env.get("LLM_BASE_URL"))