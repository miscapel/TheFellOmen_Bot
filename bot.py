import asyncio
import os
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# --- تنظیمات سرور فیک برای رفع مشکل پورت در Render ---
app = Flask('')

@app.route('/')
def home():
    return "The Fell Omen Bot is Online!"

def run():
    # Render از پورت 8080 استفاده می‌کند
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- تنظیمات اصلی ربات ---
TOKEN = "8975820451:AAEBZjhBGdFNCjnCcvld09oItdJYnkGCsGU"
STAFF_CHAT_ID = 1256603181  # آیدی عددی شما
PHOTO_URL = "https://s6.uupload.ir/files/minecraft_server_bg_8v9a.jpg"

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

# --- کیبورد اصلی ---
def main_menu():
    buttons = [
        [InlineKeyboardButton(text="📜 Whitelist Request", callback_data="req_whitelist")],
        [InlineKeyboardButton(text="🆘 Support Ticket", callback_data="open_ticket")],
        [InlineKeyboardButton(text="💎 Server Shop", callback_data="open_shop")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- هندلر دستور /start ---
@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer_photo(
        photo=PHOTO_URL,
        caption=(
            f"⚔️ **The Fell Omen Server**\n\n"
            f"سلام **{message.from_user.first_name}** خوش آمدی!\n"
            "برای شروع بازی یا ارتباط با ادمین‌ها از منوی زیر استفاده کن:"
        ),
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

# --- شروع فرآیند وایت لیست ---
@router.callback_query(F.data == "req_whitelist")
async def start_whitelist(callback: CallbackQuery):
    await callback.message.answer("🎮 لطفاً نام کاربری (IGN) خود را وارد کنید:")
    await callback.answer()

# --- مدیریت پیام‌های دریافتی (تیکت و IGN) ---
@router.message(lambda m: m.chat.type == 'private' and not m.text.startswith('/'))
async def handle_messages(message: Message):
    user_id = message.from_user.id
    user_name = message.from_user.full_name
    text = message.text

    # ارسال به ادمین/گروه استاف
    try:
        header = "🆕 **Whitelist Request**" if len(text) < 16 else "📩 **New Support Ticket**"
        staff_msg = (
            f"{header}\n"
            f"👤 User: {user_name}\n"
            f"🆔 ID: `{user_id}`\n"
            f"💬 Message: `{text}`\n\n"
            f"⚠️ برای پاسخ دادن، روی این پیام ریپلای کنید."
        )
        await bot.send_message(STAFF_CHAT_ID, staff_msg, parse_mode="Markdown")
        await message.answer("✅ پیام شما دریافت شد. ادمین‌ها به زودی بررسی می‌کنند.")
    except Exception as e:
        print(f"Error sending to staff: {e}")
        await message.answer("❌ متاسفانه در ارسال پیام خطایی رخ داد. بعداً تلاش کنید.")

# --- پاسخ ادمین با ریپلای ---
@router.message(F.reply_to_message)
async def admin_reply(message: Message):
    # فقط اگر ادمین در چت اصلی ریپلای کند
    if message.chat.id == STAFF_CHAT_ID:
        try:
            original_text = message.reply_to_message.text
            # استخراج آیدی کاربر از متن پیام قبلی
            target_id = int(original_text.split("ID:")[1].split("\n")[0].strip())
            
            await bot.send_message(target_id, f"👨‍💻 **پاسخ ادمین:**\n\n{message.text}")
            await message.reply("✅ پاسخ برای پلیر ارسال شد.")
        except:
            await message.reply("❌ خطا در پیدا کردن آیدی کاربر.")

# --- اجرای نهایی ---
async def main():
    dp.include_router(router)
    keep_alive() # فعال کردن سرور فیک
    print("TheFellOmen_Bot is starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
