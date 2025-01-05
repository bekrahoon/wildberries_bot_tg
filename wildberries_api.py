import requests
import logging
import datetime
import logging
import requests
import json

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


def get_sales_report(api_key, period=None, date_start=None, date_end=None):
    url = "https://statistics-api.wildberries.ru/api/v1/supplier/sales"
    headers = {"Authorization": f"Bearer {api_key}"}
    params = {}

    # Обработка параметров периода
    if period == "today":
        params["dateFrom"] = datetime.datetime.now().strftime("%Y-%m-%d")
        params["dateTo"] = datetime.datetime.now().strftime("%Y-%m-%d")
    elif period == "yesterday":
        params["dateFrom"] = (
            datetime.datetime.now() - datetime.timedelta(days=1)
        ).strftime("%Y-%m-%d")
        params["dateTo"] = (
            datetime.datetime.now() - datetime.timedelta(days=1)
        ).strftime("%Y-%m-%d")
    elif period == "last_7_days":
        params["dateFrom"] = (
            datetime.datetime.now() - datetime.timedelta(days=7)
        ).strftime("%Y-%m-%d")
        params["dateTo"] = datetime.datetime.now().strftime("%Y-%m-%d")
    elif period == "custom" and date_start and date_end:
        params["dateFrom"] = date_start
        params["dateTo"] = date_end
    else:
        logging.error(
            "Неверный параметр периода или отсутствуют даты для периода 'custom'"
        )
        return None

    try:
        # Отправка запроса к API с параметрами
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()

            # Проверка на пустые данные
            if not data:
                logging.error("Полученные данные пустые.")
                return None

            # Возвращаем данные в нужном формате
            logging.info(f"Отчет успешно получен: {data}")
            return data  # Возвращаем список, если данные корректны

        elif response.status_code == 401:
            # Неверный API ключ
            logging.error("Неверный API ключ: Статус 401")
            return "Неверный API ключ"
        else:
            # Ошибка получения данных
            logging.error(
                f"Ошибка при получении отчета: Статус {response.status_code}, Тело ответа: {response.text}"
            )
            return f"Ошибка получения данных: Статус {response.status_code}"

    except requests.RequestException as e:
        # Ошибка подключения
        logging.error(f"Ошибка подключения: {e}")
        return f"Ошибка подключения: {e}"


def calculate_key_metrics(data):
    try:
        # Проверка типа данных
        if not isinstance(data, list):
            logging.error(f"Ожидался список, но получено: {type(data)}")
            return None

        # Проверка типа каждого элемента в списке
        for item in data:
            if not isinstance(item, dict):
                logging.error(f"Ожидался словарь, но получено: {type(item)}")
                return None

            # Проверка наличия необходимых ключей в каждом элементе
            required_keys = [
                "totalPrice",
                "discountPercent",
                "spp",
                "paymentSaleAmount",
                "forPay",
                "finishedPrice",
                "priceWithDisc",
            ]
            missing_keys = [key for key in required_keys if key not in item]
            if missing_keys:
                logging.error(
                    f"Отсутствуют обязательные ключи: {', '.join(missing_keys)}"
                )
                return None

        total_sales = sum(item["totalPrice"] for item in data)  # Сумма всех продаж
        total_discount = sum(
            item["totalPrice"] * (item["discountPercent"] / 100) for item in data
        )  # Сумма скидок
        spp = sum(item["spp"] for item in data)  # Стоимость товара
        payment_sale_amount = sum(
            item["paymentSaleAmount"] for item in data
        )  # Общая сумма по продажам
        for_pay = sum(item["forPay"] for item in data)  # Сумма к оплате
        finished_price = sum(
            item["finishedPrice"] for item in data
        )  # Финальная стоимость
        price_with_disc = sum(
            item["priceWithDisc"] for item in data
        )  # Цена с учётом скидки

        # Расчёт средней цены продажи, если возможно
        avg_sale_price = total_sales / len(data) if data else 0

        key_metrics = {
            "total_sales": total_sales,
            "total_discount": total_discount,
            "spp": spp,
            "payment_sale_amount": payment_sale_amount,
            "for_pay": for_pay,
            "finished_price": finished_price,
            "price_with_disc": price_with_disc,
            "avg_sale_price": avg_sale_price,
        }

        logging.info(f"Ключевые показатели: {key_metrics}")
        return key_metrics

    except Exception as e:
        logging.error(f"Ошибка при расчете ключевых показателей: {e}")
        return None
