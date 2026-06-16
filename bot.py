import asyncio
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# --- تنظیمات سرور فیک برای زنده نگه داشتن در Render ---
app = Flask('')
@app.route('/')
def home(): return "The Fell Omen Bot is Online!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- تنظیمات اصلی ---
TOKEN = "8975820451:AAEBZjhBGdFNCjnCcvld09oItdJYnkGCsGU"
# آیدی ادمین یا گروه استاف (آیدی جدیدت رو اینجا گذاشتم)
STAFF_CHAT_ID = 1256603181 
PHOTO_URL = "https://s6.uupload.ir/files/minecraft_server_bg_8v9a.jpg"

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

# --- کیبوردها ---
def main_menu():
    buttons = [
        [InlineKeyboardButton(text="📜 Whitelist Request", callback_data="req_whitelist")],
        [InlineKeyboardButton(text="🆘 Support Ticket", callback_data="open_ticket")],
        [InlineKeyboardButton(text="💎 Server Shop", callback_data="open_shop")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_decision_kb(user_id, ign):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Accept", callback_data=f"acc_{user_id}_{ign}"),
         InlineKeyboardButton(text="❌ Reject", callback_data=f"rej_{user_id}")]
    ])

# --- هندلرها ---
@router.message(Command("start"))
async def cmd_start(message: Message):
    # چاپ آیدی چت در کنسول برای پیدا کردن آیدی گروه
    print(f"Chat ID: {message.chat.id} | User: {message.from_user.full_name}")
    
    await message.answer_photo(
        photo=PHOTO_URL,
        caption=f"⚔️ **The Fell Omen Server**\n\nسلام **{message.from_user.first_name}** خوش آمدی!\nبرای درخواست وایت‌لیست یا ارتباط با ادمین‌ها از دکمه‌های زیر استفاده کن:",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

# بخش وایت لیست
@router.callback_query(F.data == "req_whitelist")
async def start_whitelist(callback: CallbackQuery):
    await callback.message.answer("🎮 لطفاً نام کاربری (IGN) خود را دقیقا وارد کنید:")
    await callback.answer()

# هندلر پیام‌های متنی (تیکت و وایت‌لیست)
@router.message(lambda m: m.chat.type == 'private' and not m.text.startswith('/'))
async def handle_incoming_messages(message: Message):
    user_id = message.from_user.id
    user_name = message.from_user.full_name
    text = message.text

    # اگر متن کوتاه بود (احتمالا IGN)
    if len(text) < 16 and " " not in text:
        await message.answer("⏳ درخواست وایت‌لیست شما برای تیم Staff ارسال شد.")
        await bot.send_message(
            STAFF_CHAT_ID,
            f"🆕 **Whitelist Request**\n👤 User: {user_name}\n🎮 IGN: `{text}`\n🆔 ID: `{user_id}`",
            reply_markup=admin_decision_kb(user_id, text),
            parse_mode="Markdown"
        )
    else:
        # ارسال به صورت تیکت پشتیبانی
        await message.answer("✅ پیام شما دریافت شد و به زودی پاسخ داده می‌شود.")
        await bot.send_message(
            STAFF_CHAT_ID,
            f"📩 **New Support Ticket**\n👤 From: {user_name}\n🆔 ID: `{user_id}`\n\n💬 Message: {text}\n\n⚠️ برای پاسخ دادن، روی این پیام ریپلای کنید.",
            parse_mode="Markdown"
        )

# پاسخ ادمین با ریپلای
@router.message(F.chat.id == STAFF_CHAT_ID, F.reply_to_message)
async def admin_reply(message: Message):
    try:
        # پیدا کردن آیدی کاربر از متن پیام ریپلای شده
        original_text = message.reply_to_message.text
        target_user_id = int(original_text.split("ID:")[1].split("\n")[0].strip())
        
        await bot.send_message(target_user_id, f"👨‍💻 **پاسخ ادمین:**\n\n{message.text}")
        await message.reply("✅ ارسال شد.")
    except:
        pass # اگر آیدی پیدا نشد کاری نکن

# دکمه‌های تایید/رد وایت لیست
@router.callback_query(F.data.startswith("acc_"))
async def accept_user(callback: CallbackQuery):
    _, user_id, ign = callback.data.split("_")
    await bot.send_message(user_id, f"✅ تبریک! اکانت `{ign}` وایت‌لیست شد. وارد سرور شوید.")
    await callback.message.edit_text(f"✅ اکانت `{ign}` توسط ادمین تایید شد.")

@router.callback_query(F.data.startswith("rej_"))
async def reject_user(callback: CallbackQuery):
    user_id = callback.data.split("_")[1]
    await bot.send_message(user_id, "❌ متاسفانه درخواست وایت‌لیست شما رد شد.")
    await callback.message.edit_text("❌ درخواست رد شد.")

# اجرای ربات
async def main():
    dp.include_router(router)
    keep_alive()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
