import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

client_name = os.getenv('CLIENT_NAME', 'default')

# Load feature flags
with open(f'src/config/themes/{client_name}/feature_flags.json', 'r') as f:
    FEATURE_FLAGS = json.load(f)

def get_client_name():
    return os.getenv('CLIENT_NAME', 'acme')

def load_theme():    
    client_name = get_client_name()    
    theme_path = f"src/config/themes/{client_name}/config.toml"
    if not os.path.exists(theme_path):
        theme_path = "src/themes/default_config.toml"
    return theme_path

def is_assistant_enabled(assistant_name):
    env_var = f"ENABLE_{assistant_name.upper().replace(' ', '_')}"
    env_enabled = os.getenv(env_var, 'false').lower() == 'true'
    feature_flag_enabled = FEATURE_FLAGS.get(f"enable_{assistant_name.lower().replace(' ', '_')}", False)
    return env_enabled and feature_flag_enabled

# List of all available assistants
AVAILABLE_ASSISTANTS = [
    "Enhanced Data Analyst",
    "Enhanced Financial Analyst",
    "Product Owner",
    "Business Analyst",
    "Enhanced Quality Analyst",
    "React Assistant",
    "Web Search",
    "Research Assistant",
    "Investment Assistant",
    "Company Analyst",
    "Maintenance Engineer",
]

# Get enabled assistants
ENABLED_ASSISTANTS = [assistant for assistant in AVAILABLE_ASSISTANTS if is_assistant_enabled(assistant)]