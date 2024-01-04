import os
from dotenv import load_dotenv


load_dotenv()

# Environment variables (includes secrets)
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
USERNAME = os.getenv("SIAK_USERNAME")
PASSWORD = os.getenv("SIAK_PASSWORD")
DISCORD_UID = os.getenv("DISCORD_UID")
IS_DOCKER_ENV = os.getenv("IS_DOCKER_ENV", False) == "True"
