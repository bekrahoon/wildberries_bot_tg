import requests
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)


def validate_api_key(api_key):
    url = "https://common-api.wildberries.ru/ping"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            logging.info("API ключ валиден")
            return True
        elif response.status_code == 401:
            # Неверный API ключ
            logging.error("Неверный API ключ: Статус 401")
            return False
        else:
            # Обработка других ошибок
            logging.error(
                f"Ошибка: Статус {response.status_code}, Тело ответа: {response.text}"
            )
            return False
    except requests.RequestException as e:
        # Ошибка подключения
        logging.error(f"Ошибка подключения: {e}")
        return False


def get_sales_report(api_key):
    url = "https://suppliers-stats.wildberries.ru/api/v1/supplier/sales"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            # Обработка данных для отчёта
            logging.info(f"Отчет успешно получен: {data}")
            return f"Ваш отчет: {data}"
        else:
            # Ошибка получения данных
            logging.error(
                f"Ошибка при получении отчета: Статус {response.status_code}, Тело ответа: {response.text}"
            )
            return "Ошибка получения данных!"
    except requests.RequestException as e:
        # Ошибка подключения
        logging.error(f"Ошибка подключения: {e}")
        return "Ошибка подключения!"
