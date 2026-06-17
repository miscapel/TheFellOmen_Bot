import os
import asyncio
import threading
from flask import Flask

from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())

app = Flask(__name__)

# ---------------- MENU BUTTONS ----------------
def start_keyboard():
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="📜 Whitelist Request", callback_data="menu_whitelist")],
            [types.InlineKeyboardButton(text="💎 Server Shop", callback_data="menu_shop")],
            [types.InlineKeyboardButton(text="🆘 Support Ticket", callback_data="menu_support")],
        ]
    )

def back_keyboard():
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="🔙 Back", callback_data="menu_back")]
        ]
    )

# ---------------- START ----------------
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "Welcome to TheFellOmen Bot\n\n"
        "Please choose one of the options below:",
        reply_markup=start_keyboard()
    )

# ---------------- WHITELIST ----------------
@dp.callback_query(F.data == "menu_whitelist")
async def whitelist(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📜 Whitelist Request\n\n"
        "Please send your Minecraft username.",
        reply_markup=back_keyboard()
    )
    await callback.answer()

# ---------------- SHOP ----------------
@dp.callback_query(F.data == "menu_shop")
async def shop(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "💎 Server Shop\n\n"
        "Select your desired shop section.",
        reply_markup=back_keyboard()
    )
    await callback.answer()

# ---------------- SUPPORT ----------------
@dp.callback_query(F.data == "menu_support")
async def support(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🆘 Support Ticket\n\n"
        "Please describe your issue.",
        reply_markup=back_keyboard()
    )
    await callback.answer()

# ---------------- BACK ----------------
@dp.callback_query(F.data == "menu_back")
async def menu_back(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Welcome to TheFellOmen Bot\n\n"
        "Please choose one of the options below:",
        reply_markup=start_keyboard()
    )
    await callback.answer()

# ---------------- FLASK KEEP ALIVE ----------------
@app.route("/")
def home():
    return "Bot is running"

def run_flask():
    app.run(host="0.0.0.0", port=10000)

# ---------------- MAIN ----------------
async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
