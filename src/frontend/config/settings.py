import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Backend URL
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# List of enabled assistants
ENABLED_ASSISTANTS = ["General Assistant", "Code Assistant", "Data Analyst"]

# Client name
CLIENT_NAME = os.getenv("CLIENT_NAME", "default_client")

# Other configuration variables
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

def get_client_name():
    return CLIENT_NAME

