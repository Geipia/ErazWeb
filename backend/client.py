import os
from webdav3.client import Client
from dotenv import load_dotenv

# Load .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_USERNAME = os.getenv("DATABASE_USERNAME")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")

WEBDAV_OPTIONS = {
    "webdav_hostname": DATABASE_URL,
    "webdav_login": DATABASE_USERNAME,
    "webdav_password": DATABASE_PASSWORD,
}

client = Client(WEBDAV_OPTIONS)