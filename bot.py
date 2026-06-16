import logging
import os
import asyncio
from typing import Union

import arabic_reshaper
from bidi.algorithm import get_display
from aiogram import Bot, Dispatcher, Router, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.markdown import hbold

# ---- پیکربندی اولیه ----

# تنظیمات لاگ‌گیری
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# خواندن متغیرهای محیطی
BOT_TOKEN = os.environ.get('BOT_TOKEN')
STAFF_GROUP_ID = int(os.environ.get('STAFF_GROUP_ID')) # شناسه عددی گروه ادمین‌ها
PORT = int(os.environ.get('PORT', 8080)) # پورت پیش‌فرض اگر تنظیم نشده باشد

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set")
if not STAFF_GROUP_ID:
    raise ValueError("STAFF_GROUP_ID environment variable not set")

# راه‌اندازی ربات و دیسپچر
# استفاده از MemoryStorage برای سادگی، برای تولید بهتر است از Redis یا موارد مشابه استفاده شود.
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

# ---- وضعیت‌های FSM برای مدیریت تیکت ----

class TicketFlow(StatesGroup):
    waiting_for_reason = State()
    waiting_for_description = State()

# ---- متغیرهای سراسری ----
ticket_id_counter = 0
user_ticket_statuses = {} # برای ردیابی وضعیت تیکت کاربران: {user_id: 'waiting_for_reason'/'waiting_for_description'}

# ---- لیست کلمات ممنوعه ----
BAD_WORDS = {
    "فاک", "کس", "کص", "کونی", "جنده", "حشر", "ممه", "کیر", "کون",
    "fuck", "shit", "asshole", "bitch", "dick", "pussy", "cunt", "motherfucker",
    "کصشعر", "کسکش", "فاک یو", "کیر توش", "گوه", "خراب", "لعنتی",
    # کلمات توهین آمیز دیگر را اینجا اضافه کنید
}

# ---- توابع کمکی ----

def is_profane(text: str) -> bool:
    """بررسی می‌کند که آیا متن حاوی کلمات ممنوعه است یا خیر."""
    text_lower = text.lower()
    for word in BAD_WORDS:
        if word in text_lower:
            return True
    return False

def format_persian(text: str) -> str:
    """متن فارسی را برای نمایش صحیح در تلگرام قالب‌بندی می‌کند."""
    if not any('\u0600' <= char <= '\u06FF' for char in text):
        return text # اگر فارسی نیست، تغییر نده
    try:
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
        return bidi_text
    except Exception as e:
        logger.error(f"Error formatting Persian text: {e}")
        return text # در صورت خطا، متن اصلی را برگردان

async def send_formatted_message(bot: Bot, chat_id: int, text: str, reply_markup=None, parse_mode=None):
    """یک پیام با متن فارسی قالب‌بندی شده ارسال می‌کند."""
    formatted_text = format_persian(text)
    await bot.send_message(chat_id=chat_id, text=formatted_text, reply_markup=reply_markup, parse_mode=parse_mode)

# ---- دکمه‌های منو و پاسخ ----

def get_main_menu_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="راهنمایی ❓", callback_data="show_help")],
        [InlineKeyboardButton(text="پشتیبانی 💬", callback_data="open_ticket")],
        [InlineKeyboardButton(text="درباره ما ℹ️", callback_data="about_us")]
    ])
    return keyboard

def get_ticket_reasons_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="مشکل فنی 🛠️", callback_data="ticket_reason_technical")],
        [InlineKeyboardButton(text="سوال ❓", callback_data="ticket_reason_question")],
        [InlineKeyboardButton(text="پیشنهاد 💡", callback_data="ticket_reason_suggestion")],
        [InlineKeyboardButton(text="موارد دیگر ➕", callback_data="ticket_reason_other")]
    ])
    return keyboard

def get_staff_reply_keyboard(ticket_id: int, original_message_id: int):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="پاسخ به کاربر", callback_data=f"staff_reply_{ticket_id}_{original_message_id}")]
    ])
    return keyboard

# ---- هندلرها ----

# پیام شروع
@router.message(CommandStart())
async def cmd_start(message: Message):
    await send_formatted_message(message.bot, message.chat.id,
                                 f"سلام {hbold(message.from_user.full_name)}! به ربات ما خوش آمدید. چطور می‌توانم کمکتان کنم؟",
                                 reply_markup=get_main_menu_keyboard())

# پیام‌های متنی معمولی در چت خصوصی
@router.message(lambda m: m.chat.type == "private", F.text)
async def handle_private_message_flows(message: Message, state: FSMContext):
    global ticket_id_counter
    user_id = message.from_user.id
    current_state = await state.get_state()

    if current_state == TicketFlow.waiting_for_reason:
        await send_formatted_message(message.bot, message.chat.id, "لطفاً یکی از دلایل بالا را انتخاب کنید تا بتوانیم توضیحات شما را دریافت کنیم.")
        await state.set_state(TicketFlow.waiting_for_description) # برگرداندن به وضعیت قبل از انتخاب دلیل
        await message.reply("لطفا یکی از دلایل زیر را انتخاب کنید:", reply_markup=get_ticket_reasons_keyboard())
        return

    elif current_state == TicketFlow.waiting_for_description:
        if is_profane(message.text):
            await send_formatted_message(message.bot, message.chat.id, "متاسفانه پیام شما حاوی کلمات نامناسب است. لطفاً با رعایت ادب پیام خود را ارسال کنید.")
            return

        ticket_id_counter += 1
        ticket_id = ticket_id_counter
        user_ticket_statuses[user_id] = {'ticket_id': ticket_id, 'description': message.text, 'reason': None} # ذخیره موقت

        # ارسال به گروه ادمین‌ها
        admin_message_text = format_persian(f"#تیکت_جدید\n"
                                             f"**شناسه تیکت:** {ticket_id}\n"
                                             f"**کاربر:** {message.from_user.full_name} (ID: {user_id})\n"
                                             f"**دلیل:** {user_ticket_statuses[user_id].get('reason', 'تعیین نشده')}\n"
                                             f"**توضیحات:** {message.text}")
        try:
            sent_message_to_admin = await message.bot.send_message(
                chat_id=STAFF_GROUP_ID,
                text=admin_message_text,
                reply_markup=get_staff_reply_keyboard(ticket_id, message.message_id) # ارسال شناسه پیام کاربر برای ریپلای
            )
            user_ticket_statuses[user_id]['admin_message_id'] = sent_message_to_admin.message_id
            user_ticket_statuses[user_id]['ticket_created_time'] = asyncio.get_event_loop().time() # زمان ایجاد تیکت

            await send_formatted_message(message.bot, message.chat.id,
                                         f"تیکت شما با شناسه {ticket_id} با موفقیت ثبت شد. منتظر پاسخ از سوی پشتیبانی باشید.")
            await state.clear() # پاک کردن وضعیت FSM پس از ثبت موفق تیکت
            user_ticket_statuses[user_id]['status'] = 'open' # وضعیت تیکت را باز علامت بزن

        except Exception as e:
            logger.error(f"Error sending ticket to admin group: {e}")
            await send_formatted_message(message.bot, message.chat.id,
                                         "خطایی در ثبت تیکت رخ داد. لطفاً دقایقی دیگر مجدداً تلاش کنید.")
            await state.clear()
        return

    # اگر در وضعیت خاصی نباشیم و پیام متنی دریافت شود
    await send_formatted_message(message.bot, message.chat.id, "برای ثبت تیکت پشتیبانی، از دکمه 'پشتیبانی 💬' استفاده کنید.",
