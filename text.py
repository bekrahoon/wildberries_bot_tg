import asyncio
import json
import logging
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    CallbackQuery,
)
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup  # Добавить импорт здесь
from decouple import config
from utils import load_config, save_config
from wildberries_api import validate_api_key, get_sales_report, calculate_key_metrics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

# Bot token
API_TOKEN = config("TELEGRAM_BOT_TOKEN")

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()


# FSM states
class ReportForm(StatesGroup):
    waiting_for_shop_name = State()
    waiting_for_report_period = State()
    waiting_for_custom_period = State()


# Add other FSM states, as required


@router.message(Command("start", "help"))
async def send_welcome(message: Message):
    await message.answer(
        """Добро пожаловать! Используйте

        /addshop для добавления магазина,
        /delshop для удаления магазина, 
        /shops для вывода списка магазинов, 
        /report для получения отчёта о продажах, 
        /help - получить справку.
        """
    )


@router.message(Command("report"))
async def get_report(message: Message, state: FSMContext):
    config = load_config()
    if not config:
        await message.answer("Сначала добавьте магазины с помощью /addshop.")
        return

    if not config.keys():
        await message.answer("Нет доступных магазинов для отчёта.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for shop in config.keys():
        button = InlineKeyboardButton(text=shop, callback_data=f"report_{shop}")
        keyboard.inline_keyboard.append([button])  # Add buttons as nested lists

    await message.answer("Выберите магазин для отчёта:", reply_markup=keyboard)
    await state.set_state(ReportForm.waiting_for_shop_name)


@router.callback_query()
async def handle_shop_selection(callback_query: CallbackQuery, state: FSMContext):
    shop_name = callback_query.data[7:]  # Strip "report_" from callback_data
    config = load_config()

    if shop_name not in config:
        await bot.answer_callback_query(callback_query.id, "Магазин не найден!")
        return

    # Save the selected shop name in FSM context
    await state.update_data(shop_name=shop_name)

    # Ask for report period
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Сегодня", callback_data="today")],
            [InlineKeyboardButton(text="Вчера", callback_data="yesterday")],
            [
                InlineKeyboardButton(
                    text="Последние 7 дней", callback_data="last_7_days"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Произвольный период", callback_data="custom_period"
                )
            ],
        ]
    )

    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(
        callback_query.from_user.id, "Выберите период отчета:", reply_markup=keyboard
    )
    await state.set_state(ReportForm.waiting_for_report_period)


@router.callback_query()
async def handle_report_period(callback_query: CallbackQuery, state: FSMContext):
    period = callback_query.data
    user_data = await state.get_data()
    shop_name = user_data.get("shop_name")
    shop_api_key = load_config().get(shop_name)

    if period == "custom_period":
        # If custom period, ask for dates
        await bot.send_message(
            callback_query.from_user.id, "Введите дату начала в формате YYYY-MM-DD:"
        )
        await state.set_state(ReportForm.waiting_for_custom_period)
        return

    # Fetch report from Wildberries API
    try:
        report_data = get_sales_report(shop_api_key, period)

        # Calculate key metrics
        key_metrics = calculate_key_metrics(report_data)

        # Format the report
        report = format_report(key_metrics)

        await bot.answer_callback_query(callback_query.id)
        await bot.send_message(
            callback_query.from_user.id, report, parse_mode="Markdown"
        )

    except Exception as e:
        logging.error(f"Ошибка при получении отчета для магазина {shop_name}: {e}")
        await bot.answer_callback_query(
            callback_query.id, "Ошибка при получении отчета."
        )
        await bot.send_message(callback_query.from_user.id, f"Ошибка: {e}")


@router.message(ReportForm.waiting_for_custom_period)
async def handle_custom_period(message: Message, state: FSMContext):
    date_start = message.text
    await message.answer("Введите дату окончания в формате YYYY-MM-DD:")
    await state.update_data(date_start=date_start)
    await state.set_state(ReportForm.waiting_for_custom_period)


@router.message(ReportForm.waiting_for_custom_period)
async def handle_end_date(message: Message, state: FSMContext):
    date_end = message.text
    user_data = await state.get_data()

    date_start = user_data.get("date_start")
    shop_name = user_data.get("shop_name")
    shop_api_key = load_config().get(shop_name)

    # Fetch report from Wildberries API with custom period
    try:
        report_data = get_sales_report(shop_api_key, "custom", date_start, date_end)

        # Calculate key metrics
        key_metrics = calculate_key_metrics(report_data)

        # Format the report
        report = format_report(key_metrics)

        await bot.send_message(message.chat.id, report, parse_mode="Markdown")
        await state.set_state(None)  # End FSM state

    except Exception as e:
        logging.error(f"Ошибка при получении отчета для магазина {shop_name}: {e}")
        await message.answer(f"Ошибка при получении отчета: {e}")


# Utility function to format the report
def format_report(key_metrics):
    report = (
        f"**Отчёт о продажах:**\n\n"
        f"Общая сумма продаж: {key_metrics['total_sales']}\n"
        f"Комиссия Wildberries: {key_metrics['wildberries_commission']}\n"
        f"Скидки Wildberries: {key_metrics['wildberries_discounts']}\n"
        f"Комиссия эквайринга: {key_metrics['acquiring_commission']}\n"
        f"Стоимость логистики: {key_metrics['logistics_cost']}\n"
        f"Стоимость хранения: {key_metrics['storage_cost']}\n"
        f"Средняя цена продажи: {key_metrics['avg_sale_price']}\n"
        f"Количество проданных единиц: {key_metrics['units_sold']}\n"
    )
    return report


async def main():
    """Запуск бота"""
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())


# ---------------------------------------------------------


@router.callback_query()
async def handle_report_period(callback_query: CallbackQuery, state: FSMContext):
    period = callback_query.data
    user_data = await state.get_data()
    shop_name = user_data.get("shop_name")
    shop_api_key = load_config().get(shop_name)

    if period == "custom_period":
        # Если выбран произвольный период, запросим даты
        await bot.send_message(
            callback_query.from_user.id, "Введите дату начала в формате YYYY-MM-DD:"
        )
        await state.set_state(ReportForm.waiting_for_start_date)
        return

    # Получаем отчет для выбранного периода
    try:
        if period == "custom" and not (
            user_data.get("date_start") and user_data.get("date_end")
        ):
            raise ValueError("Необходимо указать дату начала и окончания")

        report_data = get_sales_report(shop_api_key, period)

        # Логирование полученных данных
        logging.info(f"Полученные данные отчета: {report_data}")

        # Рассчитываем ключевые показатели
        try:
            key_metrics = calculate_key_metrics(report_data)
        except KeyError as e:
            logging.error(f"Ошибка при расчете ключевых показателей: {e}")
            key_metrics = {}

        # Форматируем отчет
        report = format_report(key_metrics)

        await bot.answer_callback_query(callback_query.id)
        await bot.send_message(
            callback_query.from_user.id, report, parse_mode="Markdown"
        )

    except Exception as e:
        logging.error(f"Ошибка при получении отчета для магазина {shop_name}: {e}")
        await bot.answer_callback_query(
            callback_query.id, "Ошибка при получении отчета."
        )
        await bot.send_message(callback_query.from_user.id, f"Ошибка: {e}")
# --------------------------------------------
