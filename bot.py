import asyncio
import os
import logging
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# --- Flask Server برای زنده نگه داشتن در Render ---
app = Flask('')

@app.route('/')
def home():
    return "The Fell Omen Bot is Online!"

def run_flask():
    # Render پورت را از متغیر محیطی می‌خواند
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- تنظیمات ربat ---
TOKEN = "8975820451:AAEBZjhBGdFNCjnCcvld09oItdJYnkGCsGU"
STAFF_CHAT_ID = 1256603181 

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

# کیبورد اصلی
def main_menu():
    buttons = [
        [InlineKeyboardButton(text="📜 Whitelist Request", callback_data="req_whitelist")],
        [InlineKeyboardButton(text="🆘 Support Ticket", callback_data="open_ticket")],
        [InlineKeyboardButton(text="💎 Server Shop", callback_data="open_shop")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# دستور Start
@router.message(Command("start"))
async def cmd_start(message: Message):
    text = (
        f"⚔️ **The Fell Omen Server**\n\n"
        f"سلام **{message.from_user.first_name}** خوش آمدی!\n"
        "برای مدیریت اکانت و ارتباط با ما از منوی زیر استفاده کن:"
    )
    await message.answer(text, reply_markup=main_menu(), parse_mode="Markdown")

# هندلر دکمه‌ها
@router.callback_query(F.data == "req_whitelist")
async def req_wl(call: CallbackQuery):
    await call.message.answer("🎮 لطفاً نام کاربری (IGN) خود را بنویسید و ارسال کنید:")
    await call.answer()

@router.callback_query(F.data == "open_ticket")
async def req_ticket(call: CallbackQuery):
    await call.message.answer("📩 سوال یا گزارش خود را بنویسید و ارسال کنید:")
    await call.answer()

@router.callback_query(F.data == "open_shop")
async def show_shop(call: CallbackQuery):
    shop_text = (
        "💎 **The Fell Omen Shop**\n\n"
        "🔸 Rank VIP: 10$\n"
        "🔹 Rank MVP: 20$\n"
        "🔸 Unban: 5$\n\n"
        "برای خرید، یک تیکت باز کنید."
    )
    await call.message.answer(shop_text, parse_mode="Markdown")
    await call.answer()

# دریافت پیام کاربر و ارسال به ادمین
@router.message(lambda m: m.chat.type == 'private' and not m.text.startswith('/'))
async def handle_msgs(message: Message):
    # ساختار پیام برای ادمین (آیدی کاربر حتماً باید باشد برای سیستم ریپلای)
    staff_msg = (
        f"🆕 **New Message**\n"
        f"👤 From: {message.from_user.full_name}\n"
        f"🆔 ID: {message.from_user.id}\n\n"
        f"💬 Text: {message.text}\n\n"
        f"⚠️ برای پاسخ، روی همین پیام 'Reply' کنید."
    )
    try:
        await bot.send_message(STAFF_CHAT_ID, staff_msg)
        await message.answer("✅ پیام شما دریافت شد.")
    except Exception as e:
        logging.error(f"Error sending to staff: {e}")

# سیستم پاسخ ادمین (Reply)
@router.message(F.reply_to_message)
async def reply_handler(message: Message):
    if message.chat.id == STAFF_CHAT_ID:
        try:
            # استخراج آیدی کاربر از پیام ریپلای شده
            original_text = message.reply_to_message.text
            target_id = int(original_text.split("ID:")[1].split("\n")[0].strip())
            
            await bot.send_message(target_id, f"👨‍💻 **Staff Response:**\n\n{message.text}")
            await message.reply("✅ ارسال شد.")
        except:
            await message.reply("❌ خطا: آیدی کاربر در این پیام پیدا نشد.")

async def main():
    dp.include_router(router)
    keep_alive()
    logging.info("Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
