import asyncio
import os
import logging
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# --- Flask Server (Keep Alive) ---
app = Flask('')

@app.route('/')
def home():
    return "The Fell Omen Bot is Online!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- تنظیمات اصلی ---
TOKEN = "8975820451:AAEBZjhBGdFNCjnCcvld09oItdJYnkGCsGU"

# 🔴 اینجا آیدی گروه استاف را وارد کن (حتما با منفی شروع شود)
# اگر آیدی گروه را نداری، فعلاً همین بماند تا ربات لاگ بدهد
STAFF_GROUP_ID = -1002364859610  # مثال: آیدی گروه شما

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

    await message.answer(
        f"⚔️ **The Fell Omen Server**\n\nسلام {message.from_user.first_name}!\nبرای ارتباط با تیم مدیریت از دکمه‌های زیر استفاده کن:",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "req_whitelist")
async def req_wl(call: CallbackQuery):
    await call.message.answer("🎮 لطفاً نام کاربری (IGN) خود را بنویسید:")
    await call.answer()

@router.callback_query(F.data == "open_ticket")
async def req_ticket(call: CallbackQuery):
    await call.message.answer("📩 سوال یا گزارش خود را بنویسید:")
    await call.answer()

@router.callback_query(F.data == "open_shop")
async def show_shop(call: CallbackQuery):
    await call.message.answer("💎 **Shop**\n\nRank VIP: 10$\nRank MVP: 20$\n\nتیکت باز کنید.")
    await call.answer()

# دریافت پیام و ارسال به گروه استاف
@router.message(lambda m: m.chat.type == 'private' and not m.text.startswith('/'))
async def handle_msgs(message: Message):
    staff_msg = (
        f"🆕 **Message From User**\n"
        f"👤 User: {message.from_user.full_name}\n"
        f"🆔 ID: {message.from_user.id}\n\n"
        f"💬 Text: {message.text}\n\n"
        f"⚠️ برای پاسخ، روی همین پیام ریپلای کنید."
    )
    try:
        # ارسال به گروه
        await bot.send_message(STAFF_GROUP_ID, staff_msg)
        await message.answer("✅ پیام شما به گروه مدیریت ارسال شد.")
    except Exception as e:
        logging.error(f"Error: {e}")
        await message.answer("❌ خطا: ربات در گروه مدیریت عضو نیست یا آیدی اشتباه است.")

# سیستم ریپلای در گروه
@router.message(F.reply_to_message)
async def reply_handler(message: Message):
    # چک می‌کند که پیام حتما در گروه استاف باشد و ریپلای شده باشد
    if message.chat.id == STAFF_GROUP_ID:
        try:
            original_text = message.reply_to_message.text
            # استخراج آیدی کاربر از متن پیام
            target_id = int(original_text.split("ID:")[1].split("\n")[0].strip())
            
            await bot.send_message(target_id, f"👨‍💻 **Staff Response:**\n\n{message.text}")
            await message.reply("✅ پاسخ برای پلیر ارسال شد.")
        except:
            await message.reply("❌ خطا: نتوانستم آیدی کاربر را از این پیام پیدا کنم.")

async def main():
    dp.include_router(router)
    keep_alive()
    # حذف وب‌هوک‌های احتمالی قبلی برای رفع خطای Conflict
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
