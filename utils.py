import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Change to DEBUG
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

# Пути к файлам конфигурации
CONFIG_FILE = "config.json"


def save_config(data):
    with open(CONFIG_FILE, "w") as file_without_prefix:
        json.dump(data, file_without_prefix, indent=4)

    logging.info("Конфигурация сохранена в обоих форматах.")


def load_config(with_prefix=True):
    try:
        file_path = CONFIG_FILE
        with open(file_path, "r") as file:
            data = json.load(file)
            logging.info(f"Конфигурация загружена из {file_path}: {data}")
            return data
    except FileNotFoundError:
        logging.error(f"Файл {file_path} не найден.")
        return {}
