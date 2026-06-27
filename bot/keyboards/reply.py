from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Main menu keyboard for private chat."""
    builder = ReplyKeyboardBuilder()

    builder.button(text="👤 Профиль")
    builder.button(text="💰 Баланс")
    builder.button(text="📊 Топ")
    builder.button(text="🎁 Ежедневка")
    builder.button(text="💼 Работа")
    builder.button(text="🔫 Преступления")
    builder.button(text="🏢 Бизнес")
    builder.button(text="🏰 Клан")
    builder.button(text="🛒 Магазин")
    builder.button(text="🎒 Инвентарь")
    builder.button(text="❓ Помощь")

    builder.adjust(2, 2, 2, 2, 1)
    return builder.as_markup(resize_keyboard=True, input_field_placeholder="Выбери действие...")


def admin_keyboard() -> ReplyKeyboardMarkup:
    """Admin keyboard for private chat."""
    builder = ReplyKeyboardBuilder()

    builder.button(text="📊 Статистика")
    builder.button(text="📢 Рассылка")
    builder.button(text="💰 Выдать деньги")
    builder.button(text="⭐ Выдать опыт")
    builder.button(text="🔧 Установить уровень")
    builder.button(text="🔄 Обновить ЧС")
    builder.button(text="👤 Профиль")
    builder.button(text="💰 Баланс")

    builder.adjust(2, 2, 2, 2)
    return builder.as_markup(resize_keyboard=True)


def cancel_keyboard() -> ReplyKeyboardMarkup:
    """Simple cancel keyboard."""
    builder = ReplyKeyboardBuilder()
    builder.button(text="❌ Отмена")
    return builder.as_markup(resize_keyboard=True)


def yes_no_keyboard() -> ReplyKeyboardMarkup:
    """Yes/No keyboard."""
    builder = ReplyKeyboardBuilder()
    builder.button(text="✅ Да")
    builder.button(text="❌ Нет")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)