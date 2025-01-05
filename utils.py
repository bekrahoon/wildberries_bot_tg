import json

# Config file for storing shops
CONFIG_FILE = "config.json"


def load_config():
    try:
        with open(CONFIG_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}


def save_config(data):
    with open(CONFIG_FILE, "w") as file:
        json.dump(data, file, indent=4)
