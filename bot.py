import os
import asyncio
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# --- تنظیمات اولیه ---
TOKEN = "8975820451:AAEBZjhBGdFNCjnCcvld09oItdJYnkGCsGU"
STAFF_GROUP_ID = -1004332150226

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

# --- سیستم Keep-Alive برای Render ---
app = Flask('')

@app.route('/')
def home():
    return "TheFellOmen Bot is Running!"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- کیبوردهای اصلی ---
def main_menu():
    kb = [
        [KeyboardButton(text="📜 Whitelist Request"), KeyboardButton(text="💎 Server Shop")],
        [KeyboardButton(text="🆘 Support Ticket")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def shop_link():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Open WebShop", url="https://your-shop-link.com")]
    ])
    return kb

# --- هندلرهای دستورات ---

@router.message(Command("start"))
async def cmd_start(message: Message):
    welcome_text = (
        f"👋 Welcome **{message.from_user.full_name}** to **TheFellOmen**!\n\n"
        "🎮 Use the buttons below to interact with our server staff."
    )
    await message.answer(welcome_text, reply_markup=main_menu(), parse_mode="Markdown")

@router.message(F.text == "📜 Whitelist Request")
@router.message(Command("whitelist"))
async def whitelist_info(message: Message):
    text = (
        "📝 **How to apply for Whitelist:**\n\n"
        "Please send your **Minecraft Username** and a short description of why you want to join.\n"
        "Our staff will review your request shortly."
    )
    await message.answer(text, parse_mode="Markdown")

@router.message(F.text == "💎 Server Shop")
@router.message(Command("shop"))
async def shop_info(message: Message):
    text = "💎 **TheFellOmen Store**\n\nSupport the server and get cool ranks & items!"
    await message.answer(text, reply_markup=shop_link(), parse_mode="Markdown")

@router.message(F.text == "🆘 Support Ticket")
@router.message(Command("support"))
async def support_info(message: Message):
    await message.answer("🆘 **Support Mode**\n\nJust type your message here and send it. Our admins will receive it and reply to you as soon as possible!")

# --- سیستم انتقال پیام به گروه ---

@router.message(lambda m: m.chat.type == 'private' and not m.text.startswith('/'))
async def forward_to_staff(message: Message):
    # فرمت پیام برای گروه ادمین
    staff_msg = (
        f"📩 **New Message from User**\n"
        f"👤 Name: {message.from_user.full_name}\n"
        f"🆔 ID: `{message.from_user.id}`\n"
        f"👤 Username: @{message.from_user.username if message.from_user.username else 'None'}\n"
        f"--------------------------\n"
        f"💬 Message:\n{message.text}"
    )
    
    await bot.send_message(STAFF_GROUP_ID, staff_msg, parse_mode="Markdown")
    await message.answer("✅ Your message has been sent to the staff. Please wait for a reply.")

# --- سیستم پاسخ ادمین از گروه به کاربر ---

@router.message(lambda m: m.chat.id == STAFF_GROUP_ID and m.reply_to_message)
async def reply_to_user(message: Message):
    try:
        # استخراج آیدی کاربر از متن پیام ریپلای شده
        original_msg = message.reply_to_message.text
        user_id = int(original_msg.split("🆔 ID: ")[1].split("\n")[0].strip())
        
        # ارسال جواب ادمین برای کاربر
        answer_text = f"🛡 **Admin Response:**\n\n{message.text}"
        await bot.send_message(user_id, answer_text, parse_mode="Markdown")
        await message.reply("✅ Answer sent to user.")
    except (IndexError, ValueError):
        await message.reply("❌ Error: Could not find User ID in the replied message.")
    except Exception as e:
        await message.reply(f"❌ Error sending message: {e}")

# --- اجرای ربات ---

async def main():
    dp.include_router(router)
    keep_alive()
    # حذف وبهوک برای جلوگیری از Conflict
    await bot.delete_webhook(drop_pending_updates=True)
    print("Bot is starting...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
