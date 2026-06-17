import asyncio
import html
import logging
import os
import threading
import uuid
from datetime import datetime

from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from dotenv import load_dotenv
from flask import Flask

# تنظیمات اولیه
logging.basicConfig(level=logging.INFO)
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
STAFF_GROUP_ID = int(os.getenv("STAFF_GROUP_ID"))
ADMIN_ID = int(os.getenv("ADMIN_ID", "0")) # آیدی عددی خودتان را در Env بگذارید
PORT = int(os.getenv("PORT", "10000"))

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
app = Flask(__name__)

# حافظه برای تیکت‌ها و آیدی کاربران جهت Broadcast
TICKETS = {}
STAFF_MESSAGE_TO_TICKET = {}
USER_IDS = set() 

# تنظیم منوی کشویی
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="شروع ربات"),
        BotCommand(command="help", description="راهنما"),
        BotCommand(command="whitelist", description="وایت‌لیست"),
        BotCommand(command="shop", description="فروشگاه"),
    ]
    await bot.set_my_commands(commands)

# --- توابع کمکی ---
def safe(value): return html.escape(str(value))

# --- Broadcast برای مدیر ---
@dp.message(Command("broadcast"))
async def broadcast(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    text = message.text.replace("/broadcast ", "")
    for user_id in USER_IDS:
        try:
            await bot.send_message(user_id, text)
        except: continue
    await message.reply("پیام برای همه ارسال شد.")

# --- ارسال عکس (به‌جای پیام متنی در صورت نیاز) ---
# در توابع تیکت، می‌توانید به جای await message.answer از این استفاده کنید:
# await bot.send_photo(chat_id=..., photo=photo_id, caption=...)

# --- اصلاح پاسخ استف برای پشتیبانی از عکس ---
@dp.message(F.chat.id == STAFF_GROUP_ID)
async def staff_reply(message: types.Message):
    if not message.reply_to_message: return
    
    ticket_id = STAFF_MESSAGE_TO_TICKET.get(message.reply_to_message.message_id)
    if not ticket_id: return
    
    ticket = TICKETS[ticket_id]
    
    # اگر پیام استف عکس باشد
    if message.photo:
        await bot.send_photo(ticket["user_id"], message.photo[-1].file_id, caption=message.caption)
    else:
        await bot.send_message(ticket["user_id"], f"پاسخ استف:\n{message.text}")
    
    await message.reply("ارسال شد.")

# (بقیه توابع مربوط به کیبوردها و هندلرها مانند کد قبلی است...)
# کافیست در هر جایی که می‌خواهید عکس بفرستید از:
# await message.answer_photo(photo="URL_OR_FILE_ID", caption="...") استفاده کنید.

async def main():
    await set_commands(bot) # فعال‌سازی منوی کشویی
    # ... بقیه کد استارت
