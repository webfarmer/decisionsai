import json
import os
from distr.core.constants import CORE_DIR, MODELS_DIR

SETTINGS_DIR = os.path.join(MODELS_DIR, "settings")

import logging

logger = logging.getLogger(__name__)

def load_actions_config():
    path = os.path.join(CORE_DIR, "distr", "core", "actions.config.json")
    try:
        with open(path, "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        logger.error(f"Error: Config file not found at {path}")
        config = {"actions": []}
    except json.JSONDecodeError:
        logger.error(f"Error: Invalid JSON in config file at {path}")
        config = {"actions": []}
    return config


def load_preferences_config():    
    path = os.path.join(SETTINGS_DIR, "preferences.json")
    try:
        with open(path, "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        logger.error(f"Error: Preferences file not found at {path}")
        config = {}
    except json.JSONDecodeError:
        logger.error(f"Error: Invalid JSON in config file at {path}")
        config = {}
    return config

