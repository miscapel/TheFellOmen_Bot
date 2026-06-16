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
user_ticket_statuses = {} # برای ردیابی وضعیت تیکت کاربران: {user_id: {'ticket_id': int, 'description': str, 'reason': str, 'admin_message_id': int, 'status': str, 'ticket_created_time': float}}

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
    # بررسی می‌کند که آیا کاراکتر فارسی در متن وجود دارد
    if not any('\u0600' <= char <= '\u06FF' for char in text):
        return text # اگر فارسی نیست، بدون تغییر برگردان

    try:
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
        return bidi_text
    except Exception as e:
        logger.error(f"Error formatting Persian text: {e}")
        # در صورت بروز خطا در قالب‌بندی، متن اصلی را برمی‌گرداند تا از نمایش خطا جلوگیری شود.
        return text

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

    # مدیریت وضعیت انتظار برای دلیل تیکت
    if current_state == TicketFlow.waiting_for_reason:
        await send_formatted_message(message.bot, message.chat.id, "لطفاً یکی از دلایل بالا را انتخاب کنید تا بتوانیم توضیحات شما را دریافت کنیم.")
        await state.set_state(TicketFlow.waiting_for_description)
        await message.reply("لطفا یکی از دلایل زیر را انتخاب کنید:", reply_markup=get_ticket_reasons_keyboard())
        return

    # مدیریت وضعیت انتظار برای توضیحات تیکت
    elif current_state == TicketFlow.waiting_for_description:
        if is_profane(message.text):
            await send_formatted_message(message.bot, message.chat.id, "متاسفانه پیام شما حاوی کلمات نامناسب است. لطفاً با رعایت ادب پیام خود را ارسال کنید.")
            # اینجا می‌توانیم وضعیت را پاک کنیم یا از کاربر بخواهیم مجدد تلاش کند
            # await state.clear()
            return

        # اگر کاربر مستقیماً توضیحات را ارسال کند بدون انتخاب دلیل (که نباید اتفاق بیفتد اما برای اطمینان)
        if user_id not in user_ticket_statuses or 'reason' not in user_ticket_statuses[user_id] or user_ticket_statuses[user_id]['reason'] is None:
             await send_formatted_message(message.bot, message.chat.id, "لطفاً ابتدا با انتخاب دلیل، روند ثبت تیکت را شروع کنید.")
             await state.set_state(TicketFlow.waiting_for_reason) # برگرداندن به وضعیت انتخاب دلیل
             await message.reply("لطفا یکی از دلایل زیر را انتخاب کنید:", reply_markup=get_ticket_reasons_keyboard())
             return

        ticket_id_counter += 1
        ticket_id = ticket_id_counter
        reason = user_ticket_statuses[user_id].get('reason', 'نامشخص') # گرفتن دلیل انتخاب شده

        # ذخیره اطلاعات تیکت
        user_ticket_statuses[user_id] = {
            'ticket_id': ticket_id,
            'user_id': user_id,
            'username': message.from_user.username or message.from_user.first_name,
            'description': message.text,
            'reason': reason,
            'status': 'open' # وضعیت اولیه تیکت
        }

        # ارسال به گروه ادمین‌ها
        admin_message_text = format_persian(
            f"#تیکت_جدید\n\n"
            f"**شناسه تیکت:** {ticket_id}\n"
            f"**کاربر:** {user_ticket_statuses[user_id]['username']} (ID: {user_id})\n"
            f"**دلیل:** {reason}\n\n"
            f"**توضیحات:**\n{message.text}"
        )

        try:
            # ارسال پیام به گروه ادمین و ذخیره شناسه پیام ادمین
            sent_message_to_admin = await message.bot.send_message(
                chat_id=STAFF_GROUP_ID,
                text=admin_message_text,
                # اینجا شناسه پیام کاربر را برای ریپلای ادمین ذخیره می‌کنیم
                reply_markup=get_staff_reply_keyboard(ticket_id, message.message_id)
            )
            user_ticket_statuses[user_id]['admin_message_id'] = sent_message_to_admin.message_id
            user_ticket_statuses[user_id]['ticket_created_time'] = asyncio.get_event_loop().time()

            await send_formatted_message(message.bot, message.chat.id,
                                         f"تیکت شما با شناسه {ticket_id} با موفقیت ثبت شد. منتظر پاسخ از سوی پشتیبانی باشید.")
            await state.clear() # پاک کردن وضعیت FSM پس از ثبت موفق تیکت
            user_ticket_statuses[user_id]['status'] = 'open'

        except Exception as e:
            logger.error(f"Error sending ticket to admin group: {e}")
            await send_formatted_message(message.bot, message.chat.id,
                                         "خطایی در ثبت تیکت رخ داد. لطفاً دقایقی دیگر مجدداً تلاش کنید.")
            await state.clear() # پاک کردن وضعیت حتی در صورت خطا
            if user_id in user_ticket_statuses: # اگر موقتا ذخیره شده بود، پاک کن
                 del user_ticket_statuses[user_id]
        return

    # اگر در وضعیت خاصی نباشیم و پیام متنی دریافت شود، پیام راهنما ارسال می‌شود.
    # این بخش همان خطی است که احتمالاً خطا داشته است.
    else:
        await send_formatted_message(message.bot, message.chat.id,
                                     "برای ثبت تیکت پشتیبانی، از دکمه 'پشتیبانی 💬' استفاده کنید.",
                                     reply_markup=get_main_menu_keyboard())


# ---- هندلر دکمه‌های Callback ----

@router.callback_query(lambda c: c.data == "show_help")
async def show_help_callback(callback_query: CallbackQuery, bot: Bot):
    help_text = format_persian(
        "**راهنمای استفاده از ربات:**\n\n"
        "1. **پشتیبانی 💬:** برای ثبت تیکت پشتیبانی، این دکمه را فشار دهید. سپس دلیل مشکل خود را انتخاب کرده و توضیحات را وارد کنید.\n"
        "2. **راهنمایی ❓:** این بخش برای نمایش راهنمایی‌ها و اطلاعات مفید است.\n"
        "3. **درباره ما ℹ️:** اطلاعاتی درباره این ربات و سازندگان آن."
    )
    await bot.send_message(callback_query.from_user.id, help_text, parse_mode=ParseMode.MARKDOWN)
    await callback_query.answer("راهنمایی نمایش داده شد.")

@router.callback_query(lambda c: c.data == "about_us")
async def about_us_callback(callback_query: CallbackQuery, bot: Bot):
    about_text = format_persian(
        "**درباره ما:**\n\n"
        "این ربات با استفاده از کتابخانه `aiogram` پایتون توسعه داده شده است.\n"
        "هدف اصلی این ربات، ارائه خدمات پشتیبانی و مدیریت ارتباط با کاربران است.\n\n"
        "نسخه فعلی: 1.0.0"
    )
    await bot.send_message(callback_query.from_user.id, about_text, parse_mode=ParseMode.MARKDOWN)
    await callback_query.answer("درباره ما نمایش داده شد.")

@router.callback_query(lambda c: c.data == "open_ticket")
async def open_ticket_callback(callback_query: CallbackQuery, state: FSMContext, bot: Bot):
    user_id = callback_query.from_user.id
    # بررسی کنید که آیا کاربر در حال حاضر تیکت باز دارد یا خیر
    if user_id in user_ticket_statuses and user_ticket_statuses[user_id].get('status') == 'open':
        ticket_id = user_ticket_statuses[user_id]['ticket_id']
        await send_formatted_message(bot, user_id,
                                     f"شما در حال حاضر تیکت باز با شناسه {ticket_id} دارید. لطفاً ابتدا وضعیت آن را پیگیری کنید یا منتظر پاسخ بمانید.",
                                     reply_markup=get_main_menu_keyboard())
        await callback_query.answer("شما تیکت باز دارید.")
        return

    await state.set_state(TicketFlow.waiting_for_reason)
    await send_formatted_message(bot, user_id, "لطفاً دلیل اصلی ثبت تیکت خود را انتخاب کنید:",
                                 reply_markup=get_ticket_reasons_keyboard())
    await callback_query.answer("شروع ثبت تیکت...")


@router.callback_query(lambda c: c.data.startswith("ticket_reason_"))
async def ticket_reason_callback(callback_query: CallbackQuery, state: FSMContext, bot: Bot):
    reason = callback_query.data.split("_", 2)[-1] # استخراج دلیل (e.g., "technical", "question")
    user_id = callback_query.from_user.id

    # ذخیره دلیل انتخاب شده در وضعیت FSM یا دیکشنری کاربران
    # بهتر است در وضعیت FSM ذخیره شود تا با ارسال متن، پاک نشود.
    await state.update_data(reason=reason)
    user_ticket_statuses[user_id] = user_ticket_statuses.get(user_id, {}) # اطمینان از وجود دیکشنری کاربر
    user_ticket_statuses[user_id]['reason'] = reason # ذخیره دلیل
    user_ticket_statuses[user_id]['status'] = 'awaiting_description' # تغییر وضعیت

    await state.set_state(TicketFlow.waiting_for_description)
    await send_formatted_message(bot, user_id, f"دلیل شما '{reason}' ثبت شد. لطفاً اکنون توضیحات کامل مشکل یا سوال خود را بنویسید.")
    await callback_query.answer(f"دلیل انتخاب شد: {reason}")

# هندلر پاسخ ادمین
@router.callback_query(lambda c: c.data.startswith("staff_reply_"))
async def staff_reply_callback(callback_query: CallbackQuery, bot: Bot):
    data = callback_query.data.split("_")
    ticket_id = int(data[2])
    original_message_id = int(data[3]) # شناسه پیام کاربر اصلی برای ریپلای
    admin_user_id = callback_query.from_user.id

    # ذخیره شناسه پیام ادمین که دکمه ریپلای روی آن بوده
    admin_message_id = callback_query.message.message_id

    # دریافت اطلاعات تیکت بر اساس ticket_id
    ticket_info = None
    for user_id, data in user_ticket_statuses.items():
        if data.get('ticket_id') == ticket_id:
            ticket_info = data
            break

    if not ticket_info:
        await bot.send_message(admin_user_id, f"خطا: تیکت با شناسه {ticket_id} یافت نشد.")
        await callback_query.answer("خطا در یافتن تیکت")
        return

    # ذخیره اطلاعات مربوط به این پاسخ ادمین
    # این داده‌ها برای ارسال پاسخ به کاربر اصلی استفاده می‌شوند
    ticket_info['last_admin_reply_message_id'] = admin_message_id # شناسه پیام ادمین
    ticket_info['original_user_message_id'] = original_message_id # شناسه پیام کاربر اصلی
    ticket_info['replying_admin_id'] = admin_user_id # شناسه ادمینی که پاسخ می‌دهد

    # از ادمین بخواهید پیام خود را ارسال کند
    await send_formatted_message(bot, admin_user_id,
                                 f"لطفاً پاسخ خود را برای تیکت {ticket_id} وارد کنید. ربات آن را به کاربر ارسال خواهد کرد.")
    await callback_query.answer("آماده دریافت پاسخ شما...")

# هندلر پیام متنی ادمین که پاسخ می‌دهد
@router.message(lambda m: m.chat.id == STAFF_GROUP_ID, F.text)
async def handle_staff_reply_text(message: Message, bot: Bot):
    global user_ticket_statuses
    admin_user_id = message.from_user.id

    # پیدا کردن تیکتی که این ادمین در حال پاسخ دادن به آن است
    # این فرض می‌کند که ادمین‌ها از طریق callback_query دکمه reply را زده‌اند
    # و وضعیت یا داده‌ای برای پیگیری وجود دارد.
    # یک راه بهتر: ذخیره موقت ادمین در حال پاسخ در یک دیکشنری جداگانه.

    # جستجو در بین تیکت‌های باز یا در حال پیگیری
    ticket_to_reply = None
    target_user_id = None
    for user_id, data in user_ticket_statuses.items():
        # چک می‌کنیم آیا این ادمین پیام ریپلای را برای این تیکت زده بود؟
        # و آیا هنوز وضعیت مناسبی دارد؟
        if data.get('replying_admin_id') == admin_user_id and data.get('status') in ['open', 'awaiting_reply']:
             # ممکن است چندین تیکت باز وجود داشته باشد، باید دقیق‌تر مشخص شود.
             # فرض می‌کنیم آخرین تیکتی که ادمین انتخاب کرده، همین است.
             ticket_to_reply = data
             target_user_id = user_id
             break

    if not ticket_to_reply:
        # اگر نتوانستیم تیکت مربوطه را پیدا کنیم، ممکن است ادمین پیام را بدون زدن دکمه ریپلای فرستاده باشد.
        await send_formatted_message(bot, STAFF_GROUP_ID, "لطفاً ابتدا روی دکمه 'پاسخ به کاربر' کلیک کنید تا ربات بداند به کدام تیکت پاسخ می‌دهید.")
        return

    if is_profane(message.text):
        await send_formatted_message(bot, STAFF_GROUP_ID, "پیام شما حاوی کلمات نامناسب است. لطفاً با رعایت ادب پاسخ دهید.")
        return

    ticket_id = ticket_to_reply['ticket_id']
    user_id = target_user_id
    original_user_message_id = ticket_to_reply.get('original_user_message_id')

    reply_text = format_persian(
        f"**پاسخ از پشتیبانی (تیکت {ticket_id}):**\n\n"
        f"{message.text}"
    )

    try:
        # ارسال پاسخ به کاربر اصلی
        await bot.send_message(
            chat_id=user_id,
            text=reply_text,
            reply_to_message_id=original_user_message_id # ریپلای به پیام اصلی کاربر
        )

        # به‌روزرسانی وضعیت تیکت به "پاسخ داده شده" یا "در انتظار پاسخ کاربر"
        ticket_to_reply['status'] = 'awaiting_reply'
        ticket_to_reply['last_reply_timestamp'] = asyncio.get_event_loop().time()

        # حذف اطلاعات موقت مربوط به پاسخ ادمین
        if 'replying_admin_id' in ticket_to_reply:
            del ticket_to_reply['replying_admin_id']
        if 'original_user_message_id' in ticket_to_reply:
            del ticket_to_reply['original_user_message_id']
        if 'admin_message_id' in ticket_to_reply: # پاک کردن شناسه پیام ادمین اگر دیگر لازم نیست
             # ما ممکن است بخواهیم پیام اصلی ادمین را نگه داریم برای ارجاع
             pass

        await send_formatted_message(bot, STAFF_GROUP_ID, f"پاسخ شما به کاربر (تیکت {ticket_id}) با موفقیت ارسال شد.")

    except Exception as e:
        logger.error(f"Error sending reply to user: {e}")
        await send_formatted_message(bot, STAFF_GROUP_ID, f"خطایی در ارسال پاسخ به کاربر برای تیکت {ticket_id} رخ داد.")

# ---- هندلر دریافت فایل در چت خصوصی ----
# این بخش بهینه شده است تا با دقت بیشتری کار کند
@router.message(lambda m: m.chat.type == "private", F.document | F.photo | F.video | F.audio | F.voice | F.sticker)
async def handle_private_file_message(message: Message, state: FSMContext, bot: Bot):
    global ticket_id_counter
    user_id = message.from_user.id

    # اگر کاربر در وضعیت انتخاب دلیل یا توضیحات باشد، فایل را به عنوان بخشی از تیکت در نظر می‌گیریم.
    current_state = await state.get_state()
    if current_state == TicketFlow.waiting_for_reason:
        await send_formatted_message(bot, user_id, "لطفاً ابتدا دلیل تیکت را از لیست انتخاب کنید.")
        await message.reply("لطفا یکی از دلایل زیر را انتخاب کنید:", reply_markup=get_ticket_reasons_keyboard())
        return

    # دریافت اطلاعات فایل
    file_info = None
    file_type = "Unknown"
    file_name = "Unknown File"

    if message.document:
        file_info = message.document
        file_type = file_info.mime_type if file_info.mime_type else "document"
        file_name = file_info.file_name if file_info.file_name else "document"
    elif message.photo:
        file_info = message.photo[-1] # گرفتن بزرگترین سایز عکس
        file_type = "photo"
        file_name = f"photo_{file_info.file_unique_id}.jpg" # نامگذاری تقریبی
    elif message.video:
        file_info = message.video
        file_type = "video"
        file_name = file_info.file_name if file_info.file_name else "video.mp4"
    elif message.audio:
        file_info = message.audio
        file_type = "audio"
        file_name = file_info.file_name if file_info.file_name else "audio.mp3"
    elif message.voice:
        file_info = message.voice
        file_type = "voice"
        file_name = f"voice_{file_info.file_unique_id}.ogg"
    elif message.sticker:
        file_info = message.sticker
        file_type = "sticker"
        file_name = file_info.file_name if file_info.file_name else f"sticker_{file_info.file_unique_id}.webp"


    if not file_info:
        await send_formatted_message(bot, user_id, "متأسفانه فایل شما دریافت نشد. لطفاً مجدداً تلاش کنید.")
        return

    # اینجا تیکت را بر اساس فایل ایجاد می‌کنیم
    # اگر کاربر در وضعیت انتظار برای توضیحات باشد، فایل را به توضیحات اضافه می‌کنیم
    if current_state == TicketFlow.waiting_for_description and user_id in user_ticket_statuses:
        user_ticket_statuses[user_id]['description'] = user_ticket_statuses[user_id].get('description', '') + f"\n[فایل ارسال شد: {file_name} ({file_type})]"
        # ما نیاز نداریم که فایل را دانلود کنیم، فقط نام و نوع آن را ثبت می‌کنیم.
        # اگر نیاز به دانلود و ذخیره فایل بود، باید اینجا کد دانلود اضافه شود.

        # ارسال به ادمین‌ها با اطلاعات فایل
        reason = user_ticket_statuses[user_id].get('reason', 'نامشخص')
        ticket_id = user_ticket_statuses[user_id].get('ticket_id')

        if not ticket_id: # اگر تیکت هنوز ایجاد نشده بود (مثلا فقط فایل ارسال شده)
            ticket_id_counter += 1
            ticket_id = ticket_id_counter
            user_ticket_statuses[user_id]['ticket_id'] = ticket_id
            user_ticket_statuses[user_id]['status'] = 'open'

        admin_message_text = format_persian(
            f"#تیکت_جدید (فایل)\n\n"
            f"**شناسه تیکت:** {ticket_id}\n"
            f"**کاربر:** {message.from_user.username or message.from_user.first_name} (ID: {user_id})\n"
            f"**دلیل:** {reason}\n\n"
            f"**توضیحات:**\n{user_ticket_statuses[user_id]['description']}\n\n"
            f"**فایل پیوست:** {file_name} ({file_type})"
        )

        try:
            sent_message_to_admin = await bot.send_message(
                chat_id=STAFF_GROUP_ID,
                text=admin_message_text,
                reply_markup=get_staff_reply_keyboard(ticket_id, message.message_id)
            )
            user_ticket_statuses[user_id]['admin_message_id'] = sent_message_to_admin.message_id
            user_ticket_statuses[user_id]['ticket_created_time'] = asyncio.get_event_loop().time()

            await send_formatted_message(bot, user_id,
                                         f"تیکت شما با شناسه {ticket_id} با موفقیت ثبت شد. فایل شما نیز ضمیمه شد.")
            await state.clear() # پاک کردن وضعیت FSM

        except Exception as e:
            logger.error(f"Error sending file ticket to admin group: {e}")
            await send_formatted_message(bot, user_id,
                                         "خطایی در ثبت تیکت شما رخ داد. لطفاً دقایقی دیگر مجدداً تلاش کنید.")
            await state.clear()
            # پاک کردن موقت اطلاعات تیکت در صورت خطا
            if user_id in user_ticket_statuses and user_ticket_statuses[user_id].get('ticket_id') == ticket_id:
                del user_ticket_statuses[user_id]

    else:
        # اگر کاربر در وضعیت تیکت نبود، فایل را به عنوان یک تیکت جدید در نظر می‌گیریم
        ticket_id_counter += 1
        ticket_id = ticket_id_counter
        user_info = message.from_user
        user_ticket_statuses[user_id] = {
            'ticket_id': ticket_id,
            'user_id': user_id,
            'username': user_info.username or user_info.first_name,
            'description': f"[فایل ارسال شد: {file_name} ({file_type})]",
            'reason': 'فایل', # دلیل پیش‌فرض برای تیکت فایل
            'status': 'open'
        }

        admin_message_text = format_persian(
            f"#تیکت_جدید (فایل)\n\n"
            f"**شناسه تیکت:** {ticket_id}\n"
            f"**کاربر:** {user_ticket_statuses[user_id]['username']} (ID: {user_id})\n"
            f"**دلیل:** {user_ticket_statuses[user_id]['reason']}\n\n"
            f"**فایل پیوست:** {file_name} ({file_type})"
        )

        try:
            sent_message_to_admin = await bot.send_message(
                chat_id=STAFF_GROUP_ID,
                text=admin_message_text,
                reply_markup=get_staff_reply_keyboard(ticket_id, message.message_id)
            )
            user_ticket_statuses[user_id]['admin_message_id'] = sent_message_to_admin.message_id
            user_ticket_statuses[user_id]['ticket_created_time'] = asyncio.get_event_loop().time()

            await send_formatted_message(bot, user_id,
                                         f"تیکت پشتیبانی با شناسه {ticket_id} برای فایل ارسالی شما ثبت شد. منتظر پاسخ باشید.")

        except Exception as e:
            logger.error(f"Error sending file ticket to admin group: {e}")
            await send_formatted_message(bot, user_id,
                                         "خطایی در ثبت تیکت شما رخ داد. لطفاً دقایقی دیگر مجدداً تلاش کنید.")
            # پاک کردن موقت اطلاعات تیکت در صورت خطا
            if user_id in user_ticket_statuses and user_ticket_statuses[user_id].get('ticket_id') == ticket_id:
                del user_ticket_statuses[user_id]


# ---- اجرای ربات ----
async def main():
    # راه‌اندازی وب‌سرور برای Render
    # Render به طور خودکار متغیر محیطی PORT را تنظیم می‌کند
    from aiohttp import web
    import aiogram.web

    # ایجاد اپلیکیشن وب
    #Dp=Dispatcher()
    app = web.Application()
    # ثبت webhook برای Render
    # dp.register_webhook_handler(app, "/webhook", dp.process_update) # برای Webhook
    # از آنجایی که شما از Polling استفاده می‌کنید، این بخش برای Render متفاوت است.
    # Render با اجرای فایل `bot.py` و گوش دادن به پورت مشخص شده، ربات را فعال نگه می‌دارد.
    # ما نیاز داریم که ربات به پورت مشخص شده توسط Render گوش دهد.

    # برای Render، معمولاً فایل `bot.py` مستقیماً اجرا می‌شود و پورت را از متغیر محیطی می‌خواند.
    # برای اجرای پولینگ، نیازی به اپلیکیشن وب جداگانه نیست، مگر اینکه بخواهیم webhook را هم پشتیبانی کنیم.
    # در اینجا، فقط ربات را با polling اجرا می‌کنیم که Render آن را با اجرای `python bot.py` فعال نگه می‌دارد.

    # تنظیمات ربات
    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML) # از HTML برای hbold استفاده می‌کنیم

    # برای Render، لازم است که ربات به پورت مشخص شده گوش دهد.
    # این کار معمولاً با اجرای مستقیم فایل پایتون و مدیریت پورت انجام می‌شود.
    # برای پولینگ، نیازی به app.run_server نیست، بلکه خود Render پروسه را مدیریت می‌کند.

    # اگر بخواهیم از Webhook برای Render استفاده کنیم:
    # webhook_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/webhook"
    # await bot.set_webhook(webhook_url)
    # app.router.add_post("/webhook", dp.process_update) # باید dp به جای router استفاده شود
    # runner = web.AppRunner(app)
    # await runner.setup()
    # site = web.TCPSite(runner, '0.0.0.0', PORT)
    # await site.start()
    # logger.info(f"Starting webhook server on port {PORT}")
    # await dp.start_polling(bot, skip_updates=True)

    # برای Polling (که به نظر می‌رسد در حال حاضر استفاده می‌کنید):
    # Render پروسه `python bot.py` را اجرا می‌کند و به پورت مشخص شده گوش می‌دهد.
    # برای اینکه Render متوجه شود که ربات فعال است، پروسه باید در حال اجرا بماند.
    # اجرای `dp.start_polling` به خودی خود این کار را انجام می‌دهد.
    logger.info("Starting bot with polling...")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    # اجرای تابع main در یک event loop
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped manually.")
    except Exception as e:
        logger.critical(f"Bot crashed: {e}", exc_info=True)
