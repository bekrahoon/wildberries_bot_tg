import asyncio
import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    CallbackQuery,
)
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from decouple import config

from wildberries_api import validate_api_key, get_sales_report, calculate_key_metrics
from utils import load_config, save_config


# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Change to DEBUG
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
    waiting_for_start_date = State()
    waiting_for_end_date = State()
    waiting_for_report_period = State()


# FSM states
class ShopForm(StatesGroup):
    waiting_for_api_key = State()
    waiting_for_shop_name = State()


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


#! ----------------- ADDSHOPS -----------------
@router.message(Command("addshop"))
async def add_shop(message: Message, state: FSMContext):
    await message.answer("Введите API ключ вашего магазина Wildberries:")
    await state.set_state(ShopForm.waiting_for_api_key)


@router.message(ShopForm.waiting_for_api_key)
async def get_api_key(msg: Message, state: FSMContext):
    api_key = msg.text
    logging.info(f"Получен API ключ: {api_key}")

    if validate_api_key(api_key):
        logging.info("API ключ валиден.")
        await msg.answer("API ключ валиден. Теперь введите имя магазина:")
        await state.update_data(api_key=api_key)
        await state.set_state(ShopForm.waiting_for_shop_name)
    else:
        logging.warning(f"Неверный API ключ: {api_key}")
        await msg.answer("Неверный API ключ. Попробуйте снова.")


@router.message(ShopForm.waiting_for_shop_name)
async def get_shop_name(msg: Message, state: FSMContext):
    shop_name = msg.text
    logging.info(f"Получено имя магазина: {shop_name}")

    # Получаем данные, сохраненные в FSM
    user_data = await state.get_data()
    api_key = user_data.get("api_key")

    config = load_config()
    if not isinstance(config, dict):
        config = {}

    # Сохраняем API ключ с именем магазина
    config[shop_name] = api_key
    save_config(config)

    await msg.answer(f"API ключ и имя магазина '{shop_name}' успешно сохранены.")
    await state.set_state(None)  # Correct way to finish the FSM state


#! ----------------- ADDSHOPS -----------------


# ! -------------------SHOPS--------------------
@router.message(Command("shops"))
async def list_shops(message: Message):
    config = load_config()
    if not config:
        await message.answer("Нет сохраненных магазинов.")
    else:
        shop_list = "\n".join(config.keys())
        await message.answer(f"Сохраненные магазины:\n{shop_list}")


# ! -------------------SHOPS--------------------


# ! -------------------DELSHOP--------------------
@router.message(Command("delshop"))
async def delete_shop(message: Message):
    config = load_config()
    if not config:
        await message.answer("Нет сохраненных магазинов для удаления.")
        return

    try:
        buttons = [
            InlineKeyboardButton(text=str(name), callback_data=f"delshop_{name}")
            for name in config.keys()
        ]

        keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons])
        await message.answer("Выберите магазин для удаления:", reply_markup=keyboard)
    except Exception as e:
        logging.error(f"Ошибка при создании кнопок для удаления магазина: {e}")
        await message.answer(f"Ошибка при создании кнопок: {e}")


@router.callback_query(
    lambda callback_query: callback_query.data.startswith("delshop_")
)
async def handle_shop_deletion(callback_query: CallbackQuery):
    shop_name = callback_query.data.split("_", 1)[1]  # Извлекаем имя магазина
    config = load_config()

    if shop_name in config:
        # Отправляем сообщение с подтверждением
        confirm_buttons = [
            InlineKeyboardButton(
                text="Да, удалить", callback_data=f"confirm_delshop_{shop_name}"
            ),
            InlineKeyboardButton(
                text="Отмена", callback_data=f"cancel_delshop_{shop_name}"
            ),
        ]
        confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[confirm_buttons])

        await callback_query.message.edit_text(
            f"Вы уверены, что хотите удалить магазин {shop_name}?",
            reply_markup=confirm_keyboard,
        )
    else:
        await callback_query.message.edit_text("Магазин не найден.")


@router.callback_query(
    lambda callback_query: callback_query.data.startswith("confirm_delshop_")
)
async def confirm_shop_deletion(callback_query: CallbackQuery):
    shop_name = callback_query.data.split("_", 2)[2]  # Извлекаем имя магазина
    config = load_config()

    if shop_name in config:
        del config[shop_name]
        save_config(config)
        await callback_query.message.edit_text(f"Магазин {shop_name} удален.")
    else:
        await callback_query.message.edit_text("Магазин не найден.")


@router.callback_query(
    lambda callback_query: callback_query.data.startswith("cancel_delshop_")
)
async def cancel_shop_deletion(callback_query: CallbackQuery):
    shop_name = callback_query.data.split("_", 2)[2]  # Извлекаем имя магазина
    await callback_query.message.edit_text(f"Удаление магазина {shop_name} отменено.")


# ! -------------------DELSHOP--------------------


#! -------------------------------------- REPOTR --------------------------------------
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
        button = InlineKeyboardButton(text=shop, callback_data=f"shop_{shop}")
        keyboard.inline_keyboard.append([button])

    await message.answer("Выберите магазин для отчёта:", reply_markup=keyboard)
    await state.set_state(ReportForm.waiting_for_shop_name)


@router.callback_query(lambda callback_query: callback_query.data.startswith("shop_"))
async def handle_shop_selection(callback_query: CallbackQuery, state: FSMContext):
    logging.info(f"callback_query.data: {callback_query.data}")
    shop_name = callback_query.data.split("_", 1)[1]  # Извлекаем имя магазина
    logging.info(f"Извлеченное имя магазина: {shop_name}")

    config = load_config()

    if shop_name not in config:
        await bot.answer_callback_query(
            callback_query.id, "Магазин не найден в конфигурации."
        )
        logging.error(f"Магазин {shop_name} не найден в конфигурации.")
        return

    # Проверка наличия API ключа
    shop_api_key = config.get(shop_name)
    if not shop_api_key:
        await bot.answer_callback_query(
            callback_query.id, "API ключ для магазина не найден."
        )
        logging.error(f"API ключ для магазина {shop_name} не найден.")
        return

    # Сохраняем имя магазина в контексте FSM
    await state.update_data(shop_name=shop_name)

    # Отправляем клавиатуру для выбора периода отчета
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
    shop_api_key = load_config()

    if not shop_api_key or shop_name not in shop_api_key:
        await bot.answer_callback_query(
            callback_query.id, "API ключ для магазина не найден."
        )
        logging.error(f"API ключ для магазина {shop_name} не найден.")
        return

    if period == "custom_period":
        await bot.send_message(
            callback_query.from_user.id, "Введите дату начала в формате YYYY-MM-DD:"
        )
        await state.set_state(ReportForm.waiting_for_start_date)
        return

    try:
        report_data = get_sales_report(shop_api_key[shop_name], period)
        # Если данные не в списке, возможно, их нужно преобразовать
        if isinstance(report_data, dict) and "reports" in report_data:
            report_data = report_data["reports"]

        # Рассчитываем ключевые показатели
        key_metrics = calculate_key_metrics(report_data)

        # Форматируем отчет
        report = format_report(key_metrics)

        await bot.send_message(
            callback_query.from_user.id, report, parse_mode="Markdown"
        )
        await state.set_state(None)  # Завершаем состояние FSM

    except AttributeError as e:
        # Специальная обработка ошибки AttributeError (NoneType)
        logging.error(f"Ошибка при получении отчета для магазина {shop_name}: {e}")
        await bot.answer_callback_query(
            callback_query.id, "К сожалению, за выбранный период данных нет."
        )
        await bot.send_message(
            callback_query.from_user.id, "К сожалению, за выбранный период данных нет."
        )

    except Exception as e:
        logging.error(f"Ошибка при получении отчета для магазина {shop_name}: {e}")
        await bot.answer_callback_query(
            callback_query.id, "Ошибка при получении отчета."
        )
        await bot.send_message(callback_query.from_user.id, f"Ошибка: {e}")


@router.message(ReportForm.waiting_for_start_date)
async def handle_start_date(message: Message, state: FSMContext):
    date_start = message.text
    await state.update_data(date_start=date_start)
    # Запрашиваем дату окончания
    await message.answer("Введите дату окончания в формате YYYY-MM-DD:")
    await state.set_state(ReportForm.waiting_for_end_date)


@router.message(ReportForm.waiting_for_end_date)
async def handle_end_date(message: Message, state: FSMContext):
    date_end = message.text
    user_data = await state.get_data()

    date_start = user_data.get("date_start")
    shop_name = user_data.get("shop_name")
    shop_api_key = load_config().get(shop_name)

    # Проверка дат
    if not (date_start and date_end):
        await message.answer("Необходимо указать обе даты.")
        return

    try:
        report_data = get_sales_report(shop_api_key, "custom", date_start, date_end)

        # Если данные не в списке, возможно, их нужно преобразовать
        if isinstance(report_data, dict) and "reports" in report_data:
            report_data = report_data["reports"]

        # Рассчитываем ключевые показатели
        key_metrics = calculate_key_metrics(report_data)

        # Форматируем отчет
        report = format_report(key_metrics)

        await bot.send_message(message.chat.id, report, parse_mode="Markdown")
        await state.set_state(None)  # Завершаем состояние FSM

    except AttributeError as e:
        logging.error(f"Ошибка при получении отчета для магазина {shop_name}: {e}")
        await message.answer("К сожалению, за выбранный период данных нет.")

    except Exception as e:
        logging.error(f"Ошибка при получении отчета для магазина {shop_name}: {e}")
        await message.answer(f"Ошибка при получении отчета: {e}")


# Utility function to format the report
def format_report(key_metrics):
    def format_number(value):
        return round(value, 2) if isinstance(value, (int, float)) else value

    report = (
        "*📊 Отчёт о продажах:*\n\n"
        f"• *Общая сумма продаж:* {format_number(key_metrics.get('total_sales', 'N/A'))}\n"
        f"• *Процент скидки:* {format_number(key_metrics.get('total_discount', 'N/A'))}\n\n"
        f"• *SPP:* {format_number(key_metrics.get('spp', 'N/A'))}\n"
        f"• *Сумма оплаты:* {format_number(key_metrics.get('payment_sale_amount', 'N/A'))}\n"
        f"• *Сумма для оплаты:* {format_number(key_metrics.get('for_pay', 'N/A'))}\n\n"
        f"• *Финальная цена:* {format_number(key_metrics.get('finished_price', 'N/A'))}\n"
        f"• *Цена со скидкой:* {format_number(key_metrics.get('price_with_disc', 'N/A'))}\n"
    )
    return report


#! -------------------------------------- REPOTR --------------------------------------


async def main():
    """Запуск бота"""
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
