import asyncio
import os
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

# --- بخش سرور فیک برای زنده نگه داشتن در Render ---
app = Flask('')

@app.route('/')
def home():
    return "I'm alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- تنظیمات ربات تلگرام ---
TOKEN = "8975820451:AAEBZjhBGdFNCjnCcvld09oItdJYnkGCsGU" # اگر توکن رو عوض کردی، اینجا جایگزین کن
ADMIN_ID = 5410185987 # آیدی عددی خودت

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

# کیبورد اصلی
def main_menu_keyboard():
    buttons = [
        [InlineKeyboardButton(text="📝 Whitelist", callback_data="whitelist")],
        [InlineKeyboardButton(text="🛒 Shop", callback_data="shop")],
        [InlineKeyboardButton(text="📞 Contact Staff", callback_data="contact")],
        [InlineKeyboardButton(text="❓ Support", callback_data="support")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "✨ سلام به سرور **The Fell Omen** خوش آمدید!\n\nلطفاً از منوی زیر استفاده کنید:",
        reply_markup=main_menu_keyboard()
    )

# اجرای ربات
async def main():
    dp.include_router(router)
    keep_alive() # فراخوانی سرور فیک
    print("TheFellOmen_Bot is running and keeping alive...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
