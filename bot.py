import asyncio
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# --- تنظیمات سرور فیک ---
app = Flask('')
@app.route('/')
def home(): return "Staff System Online!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- تنظیمات اصلی ---
TOKEN = "8975820451:AAEBZjhBGdFNCjnCcvld09oItdJYnkGCsGU"
STAFF_GROUP_ID = -1002448374828  # آیدی عددی گروه استاف خودت را اینجا بذار
PHOTO_URL = "https://s6.uupload.ir/files/minecraft_server_bg_8v9a.jpg"

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

# --- کیبوردها ---
def main_menu():
    buttons = [
        [InlineKeyboardButton(text="📜 Whitelist Request", callback_data="req_whitelist")],
        [InlineKeyboardButton(text="🆘 Open Support Ticket", callback_data="open_ticket")],
        [InlineKeyboardButton(text="💎 Server Shop", callback_data="open_shop")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def ticket_reasons():
    buttons = [
        [InlineKeyboardButton(text="🚫 Report Player", callback_data="res_report")],
        [InlineKeyboardButton(text="🐛 Bug Report", callback_data="res_bug")],
        [InlineKeyboardButton(text="💰 Payment Issue", callback_data="res_pay")],
        [InlineKeyboardButton(text="⚙️ General", callback_data="res_general")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_whitelist_kb(user_id, ign):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Accept", callback_data=f"acc_{user_id}_{ign}"),
         InlineKeyboardButton(text="❌ Reject", callback_data=f"rej_{user_id}")]
    ])

# --- هندلرها ---
@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer_photo(
        photo=PHOTO_URL,
        caption=f"⚔️ **The Fell Omen Staff System**\n\nسلام **{message.from_user.first_name}**\nبرای ارتباط با تیم مدیریت از دکمه‌های زیر استفاده کنید:",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

# --- سیستم تیکت (Support) ---
@router.callback_query(F.data == "open_ticket")
async def select_reason(callback: CallbackQuery):
    await callback.message.edit_caption(
        caption="⚠️ **لطفاً دلیل تیکت خود را انتخاب کنید:**",
        reply_markup=ticket_reasons()
    )

@router.callback_query(F.data.startswith("res_"))
async def get_message_for_ticket(callback: CallbackQuery):
    reason = callback.data.split("_")[1].upper()
    await callback.message.answer(f"📝 شما بخش **{reason}** را انتخاب کردید.\nلطفاً پیام خود را بفرستید تا برای Staff ارسال شود:")
    # ذخیره موقت موضوع در دیتای دیسپچر برای این کاربر (ساده‌سازی شده)
    # در اینجا از Reply استفاده می‌کنیم تا بفهمیم پیام بعدی تیکت است.
    await callback.answer()

@router.message(lambda m: m.chat.type == 'private' and not m.text.startswith('/'))
async def handle_user_messages(message: Message):
    # این بخش هم برای Whitelist و هم برای Support کار می‌کند
    user_id = message.from_user.id
    user_name = message.from_user.full_name
    
    # ارسال به گروه استاف به صورت کارت مرتب
    staff_msg = (
        f"📩 **New Ticket/Message**\n"
        f"━━━━━━━━━━━━━━\n"
        f"👤 **From:** {user_name}\n"
        f"🆔 **ID:** `{user_id}`\n"
        f"💬 **Message:** {message.text}\n"
        f"━━━━━━━━━━━━━━\n"
        f"⚠️ برای پاسخ دادن به این کاربر، روی همین پیام **Reply** کنید."
    )
    
    # اگر پیام کوتاه بود (مثلاً برای وایت لیست)
    if len(message.text) < 20:
        await bot.send_message(STAFF_GROUP_ID, f"🆕 **Whitelist Request**\nIGN: `{message.text}`", 
                               reply_markup=admin_whitelist_kb(user_id, message.text))
    else:
        await bot.send_message(STAFF_GROUP_ID, staff_msg)
    
    await message.answer("✅ پیام شما با موفقیت برای تیم Staff ارسال شد.")

# --- سیستم پاسخگویی (Admin Reply) ---
@router.message(F.chat.id == STAFF_GROUP_ID, F.reply_to_message)
async def reply_to_user(message: Message):
    # استخراج آیدی کاربر از متن پیام اصلی که ربات فرستاده بود
    try:
        # متد ساده: پیدا کردن آیدی عددی در متن پیام ریپلای شده
        original_msg = message.reply_to_message.text
        if "ID:" in original_msg:
            user_id = int(original_msg.split("ID:")[1].split("\n")[0].strip())
            
            await bot.send_message(
                user_id, 
                f"👨‍💻 **پاسخ از طرف Staff:**\n\n{message.text}\n\n"
                "━━━━━━━━━━━━━━\n"
                "The Fell Omen Support"
            )
            await message.reply("✅ پاسخ شما برای کاربر ارسال شد.")
    except Exception as e:
        await message.reply("❌ خطا: نتوانستم آیدی کاربر را برای ارسال پاسخ پیدا کنم.")

# --- بخش وایت لیست (قبلی) ---
@router.callback_query(F.data.startswith("acc_"))
async def accept_user(callback: CallbackQuery):
    data = callback.data.split("_")
    user_id, ign = data[1], data[2]
    await bot.send_message(user_id, f"✅ درخواست وایت‌لیست شما (`{ign}`) تایید شد!")
    await callback.message.edit_text(f"✅ `{ign}` تایید شد توسط {callback.from_user.first_name}")

@router.callback_query(F.data.startswith("rej_"))
async def reject_user(callback: CallbackQuery):
    user_id = callback.data.split("_")[1]
    await bot.send_message(user_id, "❌ درخواست وایت‌لیست شما رد شد.")
    await callback.message.edit_text(f"❌ رد شد توسط {callback.from_user.first_name}")

async def main():
    dp.include_router(router)
    keep_alive()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
