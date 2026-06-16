import asyncio
import os
import logging
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# --- Flask Server برای زنده نگه داشتن در پلن رایگان ---
app = Flask('')

@app.route('/')
def home():
    return "The Fell Omen Bot is Online!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# --- تنظیمات ربات ---
TOKEN = "8975820451:AAEBZjhBGdFNCjnCcvld09oItdJYnkGCsGU"
STAFF_CHAT_ID = 1256603181 

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

# منوی اصلی (فقط دکمه)
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📜 Whitelist Request", callback_data="req_whitelist")],
        [InlineKeyboardButton(text="🆘 Support Ticket", callback_data="open_ticket")],
        [InlineKeyboardButton(text="💎 Server Shop", callback_data="open_shop")]
    ])

@router.message(Command("start"))
async def cmd_start(message: Message):
    welcome_text = (
        f"⚔️ **The Fell Omen Server**\n\n"
        f"سلام **{message.from_user.first_name}** خوش آمدی!\n"
        "برای درخواست وایت‌لیست یا ارتباط با ادمین‌ها از دکمه‌های زیر استفاده کن:"
    )
    await message.answer(welcome_text, reply_markup=main_menu(), parse_mode="Markdown")

# دکمه وایت لیست
@router.callback_query(F.data == "req_whitelist")
async def req_wl(call: CallbackQuery):
    await call.message.answer("🎮 لطفاً نام کاربری (IGN) خود را بنویسید و ارسال کنید:")
    await call.answer()

# دکمه تیکت
@router.callback_query(F.data == "open_ticket")
async def req_ticket(call: CallbackQuery):
    await call.message.answer("📩 سوال، گزارش یا مشکل خود را بنویسید و ارسال کنید:")
    await call.answer()

# دکمه شاپ
@router.callback_query(F.data == "open_shop")
async def show_shop(call: CallbackQuery):
    shop_text = (
        "💎 **The Fell Omen Shop**\n\n"
        "🔸 Rank VIP: 10$\n"
        "🔹 Rank MVP: 20$\n"
        "🔸 Unban: 5$\n\n"
        "برای خرید، یک تیکت باز کنید و پیام دهید."
    )
    await call.message.answer(shop_text, parse_mode="Markdown")
    await call.answer()

# دریافت پیام‌ها و ارسال به ادمین
@router.message(lambda m: m.chat.type == 'private' and not m.text.startswith('/'))
async def handle_msgs(message: Message):
    staff_msg = (
        f"🆕 **New Notification**\n"
        f"👤 User: {message.from_user.full_name}\n"
        f"🆔 ID: `{message.from_user.id}`\n\n"
        f"💬 Message: {message.text}\n\n"
        f"⚠️ برای پاسخ دادن، روی همین پیام ریپلای کنید."
    )
    try:
        await bot.send_message(STAFF_CHAT_ID, staff_msg, parse_mode="Markdown")
        await message.answer("✅ پیام شما دریافت شد و به زودی توسط Staff بررسی می‌شود.")
    except Exception as e:
        logging.error(f"Error: {e}")
        await message.answer("❌ خطا در ارسال پیام. لطفاً مطمئن شوید ربات را استارت کرده‌اید.")

# سیستم پاسخ ادمین
@router.message(F.reply_to_message)
async def reply_handler(message: Message):
    if message.chat.id == STAFF_CHAT_ID:
        try:
            # استخراج آیدی عددی کاربر از متن پیام قبلی
            target_id = int(message.reply_to_message.text.split("ID:")[1].split("\n")[0].strip())
            await bot.send_message(target_id, f"👨‍💻 **Staff Response:**\n\n{message.text}")
            await message.reply("✅ پاسخ شما برای کاربر ارسال شد.")
        except Exception as e:
            logging.error(f"Reply error: {e}")
            await message.reply("❌ خطا: آیدی کاربر پیدا نشد (مطمئن شوید روی پیام ربات ریپلای می‌کنید).")

async def main():
    dp.include_router(router)
    keep_alive() # زنده نگه داشتن در رندر
    logging.info("Bot is starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
