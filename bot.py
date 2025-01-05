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
from wildberries_api import validate_api_key, get_sales_report

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
# Configure logging
logger = logging.getLogger(__name__)

# Bot token
API_TOKEN = config("TELEGRAM_BOT_TOKEN")

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()


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


# Добавление других команд и обработчиков, например, для удаления магазина
@router.message(Command("delshop"))
async def delete_shop(message: Message):
    config = load_config()
    if not config:
        await message.answer("Нет сохраненных магазинов для удаления.")
        return

    try:
        buttons = [
            InlineKeyboardButton(text=str(name), callback_data=str(name))
            for name in config.keys()
        ]

        keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons])
        await message.answer("Выберите магазин для удаления:", reply_markup=keyboard)
    except Exception as e:
        logging.error(f"Ошибка при создании кнопок для удаления магазина: {e}")
        await message.answer(f"Ошибка при создании кнопок: {e}")


@router.callback_query()
async def handle_shop_deletion(callback_query: CallbackQuery):
    shop_name = callback_query.data
    config = load_config()
    if shop_name in config:
        del config[shop_name]
        save_config(config)
        await callback_query.message.edit_text(f"Магазин {shop_name} удален.")
    else:
        await callback_query.message.edit_text("Магазин не найден.")


@router.message(Command("shops"))
async def list_shops(message: Message):
    config = load_config()
    if not config:
        await message.answer("Нет сохраненных магазинов.")
    else:
        shop_list = "\n".join(config.keys())
        await message.answer(f"Сохраненные магазины:\n{shop_list}")


@router.message(Command("report"))
async def get_report(message: Message):
    config = load_config()
    if not config:
        await message.answer("Сначала добавьте магазины с помощью /addshop.")
        return

    if not config.keys():
        await message.answer("Нет доступных магазинов для отчёта.")
        return

    # Указываем inline_keyboard как пустой список
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for shop in config.keys():
        button = InlineKeyboardButton(text=shop, callback_data=f"report_{shop}")
        keyboard.inline_keyboard.append(
            [button]
        )  # Добавляем кнопки как вложенные списки

    await message.answer("Выберите магазин для отчёта:", reply_markup=keyboard)


@router.callback_query()
async def generate_report(callback_query: CallbackQuery):
    shop_name = callback_query.data[7:]
    config = load_config()
    shop_api_key = config.get(shop_name)

    if shop_api_key:
        try:
            report = get_sales_report(shop_api_key)
            await bot.answer_callback_query(callback_query.id)
            await bot.send_message(callback_query.from_user.id, report)
            logging.info(f"Отчет для магазина {shop_name} успешно получен.")
        except Exception as e:
            logging.error(f"Ошибка при получении отчета для магазина {shop_name}: {e}")
            await bot.answer_callback_query(
                callback_query.id, "Ошибка при получении отчета."
            )
            await bot.send_message(callback_query.from_user.id, f"Ошибка: {e}")
    else:
        logging.warning(f"Магазин {shop_name} не найден в конфигурации.")
        await bot.answer_callback_query(callback_query.id, "Магазин не найден!")
        await bot.send_message(callback_query.from_user.id, "Магазин не найден!")


async def main():
    """Запуск бота"""
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
