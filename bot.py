import asyncio
import os
import logging
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# --- بخش حیاتی: سرور فیک برای زنده نگه داشتن ربات در پلن رایگان ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    # Render به این پورت نیاز دارد تا سرویس را فعال نگه دارد
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# --- تنظیمات ربات تلگرام ---
TOKEN = "8975820451:AAEBZjhBGdFNCjnCcvld09oItdJYnkGCsGU"
STAFF_CHAT_ID = 1256603181 
PHOTO_URL = "https://s6.uupload.ir/files/minecraft_server_bg_8v9a.jpg"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📜 Whitelist Request", callback_data="req_whitelist")],
        [InlineKeyboardButton(text="🆘 Support Ticket", callback_data="open_ticket")],
        [InlineKeyboardButton(text="💎 Server Shop", callback_data="open_shop")]
    ])

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer_photo(
        photo=PHOTO_URL,
        caption=f"⚔️ **The Fell Omen Server**\n\nسلام **{message.from_user.first_name}**!\nبه ربات ما خوش آمدی.",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "req_whitelist")
async def req_wl(call: CallbackQuery):
    await call.message.answer("🎮 نام کاربری (IGN) خود را بنویسید:")
    await call.answer()

@router.callback_query(F.data == "open_ticket")
async def req_ticket(call: CallbackQuery):
    await call.message.answer("📩 سوال یا گزارش خود را بنویسید:")
    await call.answer()

@router.message(lambda m: m.chat.type == 'private' and not m.text.startswith('/'))
async def handle_msgs(message: Message):
    staff_msg = f"📩 **New Msg**\n👤 {message.from_user.full_name}\n🆔 ID: `{message.from_user.id}`\n\n💬 `{message.text}`"
    try:
        await bot.send_message(STAFF_CHAT_ID, staff_msg, parse_mode="Markdown")
        await message.answer("✅ پیام شما برای ادمین‌ها ارسال شد.")
    except Exception as e:
        logging.error(f"Error: {e}")

@router.message(F.reply_to_message)
async def reply_handler(message: Message):
    if message.chat.id == STAFF_CHAT_ID:
        try:
            target_id = int(message.reply_to_message.text.split("ID:")[1].split("\n")[0].strip())
            await bot.send_message(target_id, f"👨‍💻 **Staff Response:**\n\n{message.text}")
            await message.reply("✅ پاسخ ارسال شد.")
        except:
            await message.reply("❌ خطا در استخراج آیدی کاربر.")

async def main():
    dp.include_router(router)
    # اجرای سرور وب در پس‌زمینه قبل از شروع پولینگ
    keep_alive()
    logging.info("Bot & Web Server Started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")
