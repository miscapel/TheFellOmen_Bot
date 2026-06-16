import os
import json
import asyncio
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8975820451:AAEBZjhBGdFNCjnCcvld09oItdJYnkGCsGU"
STAFF_GROUP_ID = -1004332150226
ADMINS = [1256603181]  # فقط ادمین‌هایی که می‌تونن اعلان عمومی بزنن

USERS_FILE = "users.json"

def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    return json.load(open(USERS_FILE, "r"))

def save_user(uid):
    users = load_users()
    if uid not in users:
        users.append(uid)
        json.dump(users, open(USERS_FILE, "w"))

# -----------------------------------------------------

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

# ------------------- KEEP ALIVE -------------------
app = Flask('')

@app.route('/')
def home():
    return "TheFellOmen Bot Running!"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

def keep_alive():
    Thread(target=run).start()

# ------------------- KEYBOARDS -------------------
def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("📜 Whitelist Request")],
            [KeyboardButton("💎 Server Shop")],
            [KeyboardButton("🆘 Support Ticket")]
        ],
        resize_keyboard=True
    )

def shop_link():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Visit WebShop", url="https://your-shop-link.com")]
    ])

# ------------------- START -------------------
@router.message(Command("start"))
async def start_cmd(message: Message):
    save_user(message.from_user.id)
    await message.answer(
        f"👋 خوش آمدی {message.from_user.full_name}!\n\n"
        "از منوی زیر یکی از گزینه‌ها را انتخاب کن:",
        reply_markup=main_menu()
    )

# ------------------- WHITELIST -------------------
@router.message(F.text == "📜 Whitelist Request")
@router.message(Command("whitelist"))
async def whitelist(message: Message):
    await message.answer(
        "📝 درخواست وایت‌لیست:\n\n"
        "لطفاً **نام ماینکرفت** و دلیل عضویت خود را ارسال کنید.\n"
        "درخواست تو به تیم مدیریت ارسال خواهد شد."
    )

# ------------------- SHOP -------------------
@router.message(F.text == "💎 Server Shop")
@router.message(Command("shop"))
async def shop(message: Message):
    await message.answer(
        "💎 فروشگاه رسمی سرور:\n\nبا خرید از فروشگاه از ما حمایت کن!",
        reply_markup=shop_link()
    )

# ------------------- SUPPORT -------------------
@router.message(F.text == "🆘 Support Ticket")
@router.message(Command("support"))
async def support(message: Message):
    await message.answer(
        "🆘 تیکت پشتیبانی:\n\n"
        "پیامت را ارسال کن. تیم مدیریت بررسی می‌کند."
    )

# ------------------- SEND MESSAGE TO STAFF -------------------
@router.message(lambda m: m.chat.type == "private" and not m.text.startswith("/"))
async def forward_to_staff(message: Message):
    save_user(message.from_user.id)

    msg = (
        "📩 **پیام جدید از کاربر**\n"
        f"👤 نام: {message.from_user.full_name}\n"
        f"🆔 آی‌دی: `{message.from_user.id}`\n"
        f"🔗 یوزرنیم: @{message.from_user.username or 'None'}\n"
        "--------------------------\n"
        f"💬 پیام:\n{message.text}"
    )

    await bot.send_message(STAFF_GROUP_ID, msg, parse_mode="Markdown")
    await message.answer("✅ پیام تو با موفقیت برای **تیم مدیریت** ارسال شد.")

# ------------------- STAFF REPLY -------------------
@router.message(lambda m: m.chat.id == STAFF_GROUP_ID and m.reply_to_message)
async def staff_reply(message: Message):
    try:
        original = message.reply_to_message.text
        user_id = int(original.split("🆔 آی‌دی: `")[1].split("`")[0])

        await bot.send_message(
            user_id,
            f"🛡 **پاسخ مدیریت:**\n\n{message.text}",
            parse_mode="Markdown"
        )
        await message.reply("✅ پیام برای کاربر ارسال شد.")

    except Exception as e:
        await message.reply("❌ خطا در ارسال پیام.")

# ------------------- ANNOUNCEMENT -------------------
@router.message(Command("announce"))
async def announce(message: Message):
    if message.from_user.id not in ADMINS:
        return await message.answer("❌ تو اجازه این فرمان را نداری.")

    text = message.text.replace("/announce", "").strip()
    if not text:
        return await message.answer("لطفاً متن اعلان را بعد از دستور بنویس:\n/announce متن اعلان")

    users = load_users()
    sent = 0

    for uid in users:
        try:
            await bot.send_message(uid, f"📢 **اعلان جدید:**\n\n{text}", parse_mode="Markdown")
            sent += 1
        except:
            pass

    await message.answer(f"📣 اعلان با موفقیت برای {sent} کاربر ارسال شد.")

# ------------------- RUN BOT -------------------
async def main():
    dp.include_router(router)
    keep_alive()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
