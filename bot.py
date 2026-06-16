import asyncio
import json
from datetime import datetime, timedelta
from collections import defaultdict
import os # Import os for environment variables

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile
from aiogram.enums import ParseMode
from aiogram.utils.markdown import hlink, hcode
from aiogram.types import CallbackQuery

# --- Configuration ---
# **URGENT: Use environment variables for sensitive information!**
TOKEN = os.environ.get("BOT_TOKEN", "8975820451:AAEBZjhBGdFNCjnCcvld09oItdJYnkGCsGU") # Fallback to hardcoded if env var not set
STAFF_GROUP_ID = int(os.environ.get("STAFF_GROUP_ID", "-1004332150226")) # Fallback
ADMINS = [int(admin_id) for admin_id in os.environ.get("ADMINS", "1256603181").split(',')] # Fallback and comma-separated

# Webhook and Server Configuration
WEBHOOK_URL = os.environ.get("WEBHOOK_URL") # e.g., "https://your-render-app.onrender.com"
WEBHOOK_PORT = int(os.environ.get("PORT", 8080)) # Use the port provided by Render

# --- Bot Initialization ---
bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()
router = Router()

# --- User Database ---
USERS_FILE = "users.json"

def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()
    except json.JSONDecodeError:
        print(f"Error decoding {USERS_FILE}. Starting with an empty set.")
        return set()

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(list(users), f, indent=4)

users = load_users()

# --- Security Settings ---
WARN_LIMIT_MUTE = 3
WARN_LIMIT_BAN = 5

# Spam detection settings
SPAM_DETECTION_THRESHOLD = 4
SPAM_INTERVAL = 5 # seconds

# Bad words list
BAD_WORDS = [
    # Persian offensive terms
    "کیر", "کص", "کون", "جنده", "حرامزاده", "بی ناموس", "مادرجنده", "خواهر جنده",
    "کس ننه", "کس ننت", "کس ننش", "کس مادر", "کس خار", "کونی", "تخم", "گاییدن",
    "سکسی", "پورن", "سکس", "کصکش", "گوه", "لجن",
    # English offensive terms
    "fuck", "fucking", "shit", "shitty", "asshole", "motherfucker", "bitch",
    "cunt", "dick", "pussy", "cock", "bastard", "damn", "hell", "sex", "porn",
    "nigger", "faggot", "chink", "slut", "whore", "jizz", "cum", "rape",
    "kill", "murder", "die", "suicide", "terrorist"
]

user_warnings = defaultdict(int)
user_messages = defaultdict(list)

# --- Ticket System ---
TICKET_FILE = "tickets.json"
ticket_id_counter = 0
tickets = {}

def load_tickets():
    global ticket_id_counter
    try:
        with open(TICKET_FILE, "r") as f:
            data = json.load(f)
            tickets.update(data)
            if tickets:
                int_keys = [int(k) for k in tickets.keys()]
                if int_keys:
                    ticket_id_counter = max(int_keys)
            return data
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        print(f"Error decoding {TICKET_FILE}. Starting with an empty ticket system.")
        return {}

def save_tickets():
    with open(TICKET_FILE, "w") as f:
        json.dump(tickets, f, indent=4)

tickets = load_tickets()

# --- Menu Button Texts ---
BTN_WHITELIST = "📜 درخواست Whitelist" # Persian
BTN_SHOP = "💎 فروشگاه سرور" # Persian
BTN_SUPPORT = "🆘 پشتیبانی" # Persian

# --- Inline Keyboards for Ticket Reasons ---
def get_whitelist_reasons_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Griefing", callback_data="reason_Griefing")],
        [InlineKeyboardButton(text="Hacking", callback_data="reason_Hacking")],
        [InlineKeyboardButton(text="رفتار نامناسب", callback_data="reason_Inappropriate Behavior")], # Persian
        [InlineKeyboardButton(text="سایر موارد", callback_data="reason_Other")] # Persian
    ])

def get_staff_reply_markup(ticket_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="پاسخ دادن", callback_data=f"reply_ticket_{ticket_id}")]
    ])

# --- Main Menu Markup ---
def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_WHITELIST)],
            [KeyboardButton(text=BTN_SHOP)],
            [KeyboardButton(text=BTN_SUPPORT)]
        ],
        resize_keyboard=True
    )

# --- State Management ---
user_states = {} # {user_id: {"state": "awaiting_reason" or "awaiting_description", "reason": "...", "ticket_id": ...}}
staff_reply_state = {} # {staff_user_id: {"state": "staff_replying", "ticket_id": ...}}

# --- Handlers ---

@router.message(CommandStart())
async def start(message: Message):
    user_id = message.from_user.id
    if user_id not in users:
        users.add(user_id)
        save_users(users)
        welcome_message = (
            f"<b>👋 به سرور TheFellOmen خوش آمدید!</b>\n\n"
            "از منوی زیر برای تعامل با ادمین‌ها استفاده کنید.\n\n"
            "<b>دلایل درخواست Whitelist:</b>\n"
            "- Griefing\n"
            "- Hacking\n"
            "- رفتار نامناسب\n"
            "- سایر موارد"
        )
    else:
        welcome_message = (
            f"<b>👋 دوباره به سرور TheFellOmen خوش آمدید!</b>\n\n"
            "مشکلی دارید؟ از منوی زیر استفاده کنید.\n\n"
            "<b>دلایل درخواست Whitelist:</b>\n"
            "- Griefing\n"
            "- Hacking\n"
            "- رفتار نامناسب\n"
            "- سایر موارد"
        )

    await message.answer(
        welcome_message,
        reply_markup=get_main_menu()
    )

@router.message(lambda m: m.text == BTN_WHITELIST)
async def whitelist_request_start(message: Message):
    user_id = message.from_user.id
    user_states[user_id] = {"state": "awaiting_reason"}
    await message.answer(
        "<b>📜 درخواست Whitelist</b>\n\n"
        "لطفاً دلیل درخواست خود را انتخاب کنید:",
        reply_markup=get_whitelist_reasons_keyboard()
    )

@router.callback_query(lambda c: c.data and c.data.startswith("reason_"))
async def handle_whitelist_reason(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    reason = callback_query.data.split("_")[1]

    if user_id not in user_states or user_states[user_id].get("state") != "awaiting_reason":
        await callback_query.answer("لطفاً با کلیک مجدد روی دکمه 'درخواست Whitelist' شروع کنید.", show_alert=True)
        return

    user_states[user_id]["reason"] = reason
    user_states[user_id]["state"] = "awaiting_description"

    await callback_query.message.edit_reply_markup(reply_markup=None)
    await callback_query.message.answer(
        f"<b>دلیل انتخاب شده:</b> {reason}\n\n"
        "حالا لطفاً نام کاربری ماینکرفت و توضیح مختصر خود را ارسال کنید."
    )
    await callback_query.answer()

# Handler for private messages (description, menu, support text)
@router.message(lambda m: m.chat.type == "private")
async def handle_private_message_flows(message: Message):
    user_id = message.from_user.id
    user_text = message.text

    # --- Handle Whitelist Description ---
    if user_id in user_states and user_states[user_id].get("state") == "awaiting_description":
        reason = user_states[user_id].get("reason")
        username = message.from_user.username or message.from_user.full_name
        description = user_text

        if not reason or not description:
            await message.answer("خطایی رخ داد. لطفاً دوباره درخواست whitelist خود را ارسال کنید.")
            if user_id in user_states: del user_states[user_id]
            return

        # Create ticket
        global ticket_id_counter
        ticket_id_counter += 1
        current_ticket_id = ticket_id_counter
        timestamp = datetime.now().isoformat()

        tickets[current_ticket_id] = {
            "user_id": user_id,
            "username": username,
            "reason": reason,
            "message": description,
            "timestamp": timestamp,
            "replies": []
        }
        save_tickets()

        ticket_message_to_staff = (
            f"<b>📩 درخواست Whitelist جدید #{current_ticket_id}</b>\n\n"
            f"<b>کاربر:</b> {hlink(username, f'tg://user?id={user_id}')}\n"
            f"<b>آیدی کاربر:</b> {hcode(str(user_id))}\n"
            f"<b>دلیل:</b> {reason}\n"
            f"<b>زمان:</b> {timestamp}\n\n"
            f"<b>جزئیات:</b>\n{description}"
        )

        try:
            await bot.send_message(
                STAFF_GROUP_ID,
                ticket_message_to_staff,
                reply_markup=get_staff_reply_markup(current_ticket_id)
            )
            await message.answer("✅ <b>درخواست whitelist شما برای بررسی به ادمین‌ها ارسال شد.</b>")
        except Exception as e:
            print(f"Error sending whitelist request to staff group: {e}")
            await message.answer("خطا در ارسال درخواست. لطفاً دوباره تلاش کنید.")

        if user_id in user_states: del user_states[user_id]
        return

    # --- Handle Menu Buttons ---
    if user_text == BTN_WHITELIST:
        await whitelist_request_start(message)
    elif user_text == BTN_SHOP:
        await message.answer(
            "<b>💎 فروشگاه سرور</b>\n"
            "برای خرید آیتم‌ها و بسته‌های ویژه از فروشگاه ما دیدن کنید:\n"
            "https://your-store-link.com" # Replace with your actual store link
        )
    elif user_text == BTN_SUPPORT:
        await message.answer(
            "<b>🆘 پشتیبانی</b>\n"
            "لطفاً مشکل خود را شرح دهید تا ادمین‌ها به شما کمک کنند."
        )
    # --- Handle general private messages as support tickets ---
    else:
        if user_id in user_states and user_states[user_id].get("state") == "awaiting_reason":
            await message.answer(
                "لطفاً ابتدا یکی از دلایل را انتخاب کنید:",
                reply_markup=get_whitelist_reasons_keyboard()
            )
            return

        # Ignore commands
        if user_text and user_text.startswith("/"):
            return

        # Ignore media, ask user to send text (unless it's a reply to a bot message where we expect text)
        if message.photo or message.video or message.animation or message.document or message.sticker:
            await message.answer("لطفاً مشکل خود را به صورت پیام متنی ارسال کنید.")
            return

        if not user_text:
            return

        # Create ticket
        global ticket_id_counter
        ticket_id_counter += 1
        current_ticket_id = ticket_id_counter
        timestamp = datetime.now().isoformat()
        username = message.from_user.username or message.from_user.full_name

        tickets[current_ticket_id] = {
            "user_id": user_id,
            "username": username,
            "message": user_text,
            "timestamp": timestamp,
            "replies": []
        }
        save_tickets()

        ticket_message_to_staff = (
            f"<b>📩 تیکت پشتیبانی جدید #{current_ticket_id}</b>\n\n"
            f"<b>کاربر:</b> {hlink(username, f'tg://user?id={user_id}')}\n"
            f"<b>آیدی کاربر:</b> {hcode(str(user_id))}\n"
            f"<b>زمان:</b> {timestamp}\n\n"
            f"<b>پیام:</b>\n{user_text}"
        )

        try:
            await bot.send_message(
                STAFF_GROUP_ID,
                ticket_message_to_staff,
                reply_markup=get_staff_reply_markup(current_ticket_id)
            )
            await message.answer("✅ <b>تیکت پشتیبانی شما با موفقیت ارسال شد.</b> ادمین‌ها به زودی پاسخ خواهند داد.")
        except Exception as e:
            print(f"Error sending support ticket to staff group: {e}")
            await message.answer("خطا در ارسال تیکت. لطفاً دوباره تلاش کنید.")

# Handler for receiving files (photos) in private chat
@router.message(lambda m: m.chat.type == "private", content_types=['photo', 'document', 'video', 'audio', 'voice', 'sticker'])
async def handle_private_file_message(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.full_name

    # Check if this is part of an ongoing ticket or whitelist process
    if user_id in user_states and user_states[user_id].get("state") == "awaiting_description":
        # This is a description for whitelist, but user sent a file instead of text
        await message.answer("لطفاً نام کاربری ماینکرفت و توضیح خود را به صورت متنی ارسال کنید. ارسال فایل در این مرحله پشتیبانی نمی‌شود.")
        return

    # --- Handle as a general support ticket with file attachment ---
    file_info = ""
    if message.photo:
        file_info = f"<b>نوع فایل:</b> عکس\n<b>کپشن:</b> {message.caption or 'بدون کپشن'}\n"
        # You can download and save the photo if needed, e.g., using message.photo[-1].file_id
    elif message.document:
        file_info = f"<b>نوع فایل:</b> سند\n<b>نام فایل:</b> {message.document.file_name}\n<b>کپشن:</b> {message.caption or 'بدون کپشن'}\n"
    elif message.video:
        file_info = f"<b>نوع فایل:</b> ویدیو\n<b>کپشن:</b> {message.caption or 'بدون کپشن'}\n"
    # Add more types if needed (audio, voice, sticker)

    global ticket_id_counter
    ticket_id_counter += 1
    current_ticket_id = ticket_id_counter
    timestamp = datetime.now().isoformat()

    tickets[current_ticket_id] = {
        "user_id": user_id,
        "username": username,
        "message": f"[فایل ارسال شد] {message.caption or ''}", # Store a placeholder and caption
        "file_info": file_info, # Store file type and name
        "timestamp": timestamp,
        "replies": []
    }
    save_tickets()

    ticket_message_to_staff = (
        f"<b>📩 تیکت پشتیبانی با فایل جدید #{current_ticket_id}</b>\n\n"
        f"<b>کاربر:</b> {hlink(username, f'tg://user?id={user_id}')}\n"
        f"<b>آیدی کاربر:</b> {hcode(str(user_id))}\n"
        f"<b>زمان:</b> {timestamp}\n\n"
        f"{file_info}"
        f"<b>کپشن (در صورت وجود):</b> {message.caption or 'ندارد'}"
    )

    try:
        await bot.send_message(
            STAFF_GROUP_ID,
            ticket_message_to_staff,
            reply_markup=get_staff_reply_markup(current_ticket_id)
        )
        await message.answer("✅ <b>تیکت پشتیبانی شما با فایل ضمیمه ارسال شد.</b> ادمین‌ها به زودی پاسخ خواهند داد.")
    except Exception as e:
        print(f"Error sending support ticket with file to staff group: {e}")
        await message.answer("خطا در ارسال تیکت. لطفاً دوباره تلاش کنید.")


# --- Staff Interaction Handlers ---
@router.callback_query(lambda c: c.data and c.data.startswith("reply_ticket_"))
async def handle_reply_ticket_callback(callback_query: CallbackQuery):
    parts = callback_query.data.split("_")
    if len(parts) != 3:
        await callback_query.answer("داده نامعتبر.", show_alert=True)
        return

    try:
        ticket_id = int(parts[2])
    except ValueError:
        await callback_query.answer("شناسه تیکت نامعتبر.", show_alert=True)
        return

    staff_user_id = callback_query.from_user.id
    staff_reply_state[staff_user_id] = {"state": "staff_replying", "ticket_id": ticket_id}

    await callback_query.message.answer(
        f"<b>لطفاً پاسخ خود را برای تیکت #{ticket_id} بنویسید:</b>\n"
        "(این پیام برای کاربر ارسال خواهد شد)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="لغو", callback_data=f"cancel_reply_{ticket_id}")]
        ])
    )
    await callback_query.answer()

# Handler for staff reply messages (using state)
@router.message(lambda m: m.chat.id == STAFF_GROUP_ID)
async def handle_staff_reply(message: Message):
    staff_user_id = message.from_user.id
    reply_text = message.text

    if staff_user_id in staff_reply_state and staff_reply_state[staff_user_id].get("state") == "staff_replying":
        ticket_id = staff_reply_state[staff_user_id].get("ticket_id")

        if not reply_text:
            await message.answer("لطفاً یک پیام متنی ارسال کنید.")
            return

        timestamp = datetime.now().isoformat()

        if ticket_id and ticket_id in tickets:
            tickets[ticket_id]["replies"].append({
                "sender": "staff",
                "message": reply_text,
                "timestamp": timestamp
            })
            save_tickets()

            original_ticket_info = tickets[ticket_id]
            user_id_to_reply = original_ticket_info["user_id"]
            username = original_ticket_info.get("username", "Unknown User")

            try:
                # Check if the ticket included a file
                if "file_info" in original_ticket_info and original_ticket_info["file_info"]:
                    # If it was a photo, try to send a generic message acknowledging the file
                    await bot.send_message(
                        user_id_to_reply,
                        f"<b>💬 پاسخ ادمین (تیکت #{ticket_id}):</b>\n\n{reply_text}\n\n"
                        f"<i>(این تیکت شامل یک فایل بود که توسط ادمین بررسی شد.)</i>"
                    )
                else:
                    await bot.send_message(
                        user_id_to_reply,
                        f"<b>💬 پاسخ ادمین (تیکت #{ticket_id}):</b>\n\n{reply_text}"
                    )
                await message.answer(f"✅ پاسخ به کاربر {username} (ID: {user_id_to_reply}) ارسال شد.")
            except Exception as e:
                print(f"Error sending reply to user {user_id_to_reply}: {e}")
                await message.answer(f"خطا در ارسال پاسخ به کاربر {username}. ممکن است ربات را بلاک کرده باشد.")
        else:
            await message.answer(f"تیکت #{ticket_id} یافت نشد.")

        del staff_reply_state[staff_user_id]
        return

    # Handle direct replies to the bot's ticket message in staff chat
    elif message.reply_to_message and message.reply_to_message.text and ("تیکت پشتیبانی جدید #" in message.reply_to_message.text or "درخواست Whitelist جدید #" in message.reply_to_message.text):
        try:
            ticket_id_str = message.reply_to_message.text.split("#")[1].split("\n")[0].strip()
            ticket_id = int(ticket_id_str)
        except (IndexError, ValueError):
            await message.answer("امکان تعیین شناسه تیکت از پیام پاسخ داده شده وجود ندارد.")
            return

        reply_text = message.text
        if not reply_text:
            await message.answer("لطفاً یک پیام متنی ارسال کنید.")
            return

        timestamp = datetime.now().isoformat()

        if ticket_id in tickets:
            tickets[ticket_id]["replies"].append({
                "sender": "staff",
                "message": reply_text,
                "timestamp": timestamp
            })
            save_tickets()

            original_ticket_info = tickets[ticket_id]
            user_id_to_reply = original_ticket_info["user_id"]
            username = original_ticket_info.get("username", "Unknown User")

            try:
                if "file_info" in original_ticket_info and original_ticket_info["file_info"]:
                    await bot.send_message(
                        user_id_to_reply,
                        f"<b>💬 پاسخ ادمین (تیکت #{ticket_id}):</b>\n\n{reply_text}\n\n"
                        f"<i>(این تیکت شامل یک فایل بود که توسط ادمین بررسی شد.)</i>"
                    )
                else:
                    await bot.send_message(
                        user_id_to_reply,
                        f"<b>💬 پاسخ ادمین (تیکت #{ticket_id}):</b>\n\n{reply_text}"
                    )
                await message.answer(f"✅ پاسخ به کاربر {username} (ID: {user_id_to_reply}) ارسال شد.")
            except Exception as e:
                print(f"Error sending reply to user {user_id_to_reply}: {e}")
                await message.answer(f"خطا در ارسال پاسخ به کاربر {username}. ممکن است ربات را بلاک کرده باشد.")
        else:
            await message.answer(f"تیکت #{ticket_id} یافت نشد.")

@router.callback_query(lambda c: c.data and c.data.startswith("cancel_reply_"))
async def handle_cancel_reply_callback(callback_query: CallbackQuery):
    staff_user_id = callback_query.from_user.id
    if staff_user_id in staff_reply_state and staff_reply_state[staff_user_id].get("state") == "staff_replying":
        del staff_reply_state[staff_user_id]
    await callback_query.message.delete_reply_markup()
    await callback_query.answer("عملیات پاسخ لغو شد.")

# Announcement command (for admins)
@router.message(Command("announce"))
async def announce_command(message: Message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        await message.answer("شما ادمین نیستید و اجازه ارسال پیام عمومی را ندارید.")
        return

    text_to_announce = message.text.replace("/announce", "").strip()

    if not text_to_announce:
        await message.answer("لطفاً پس از دستور /announce، متن پیام خود را وارد کنید.\nمثال: `/announce تعمیرات سرور به زودی آغاز می‌شود.`")
        return

    sent_count = 0
    failed_users = []
    for uid in users:
        try:
            await bot.send_message(
                uid,
                f"<b>📢 اطلاعیه سرور</b>\n\n{text_to_announce}"
            )
            sent_count += 1
        except Exception as e:
            failed_users.append(uid)
            print(f"Failed to send announcement to user {uid}: {e}")

    await message.answer(f"✅ پیام برای {sent_count} کاربر ارسال شد.")
    if failed_users:
        await message.answer(f"⚠️ ارسال پیام برای {len(failed_users)} کاربر ناموفق بود.")

# Group Security Handler
@router.message(lambda m: m.chat.type in ["group", "supergroup"])
async def group_security_check(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    now = datetime.now()

    # --- Spam Detection ---
    user_messages[user_id] = [t for t in user_messages[user_id] if (now - t) < timedelta(seconds=SPAM_INTERVAL)]
    user_messages[user_id].append(now)

    if len(user_messages[user_id]) > SPAM_DETECTION_THRESHOLD:
        user_warnings[user_id] += 1
        try:
            await message.delete()
        except Exception as e:
            print(f"Could not delete spam message from user {user_id} in chat {chat_id}: {e}")

        warning_text = (
            f"⚠️ کاربر {hlink(message.from_user.full_name, f'tg://user?id={user_id}')} "
            f"به دلیل اسپم شناسایی شد.\n"
            f"<b>امتیاز هشدار:</b> {user_warnings[user_id]}/{WARN_LIMIT_BAN}"
        )
        await message.answer(warning_text)

    # --- Media Blocking ---
    if message.photo or message.video or message.animation or message.sticker or message.document:
        user_warnings[user_id] += 1
        try:
            await message.delete()
        except Exception as e:
            print(f"Could not delete media message from user {user_id} in chat {chat_id}: {e}")

        warning_text = (
            f"🚫 ارسال مدیا (عکس، ویدیو، گیف، استیکر، فایل) در این گروه مجاز نیست.\n"
            f"<b>امتیاز هشدار:</b> {user_warnings[user_id]}/{WARN_LIMIT_BAN}"
        )
        await message.answer(warning_text)

    # --- Bad Words Filter ---
    if message.text:
        txt_lower = message.text.lower()
        detected_words = [word for word in BAD_WORDS if word in txt_lower]
        if detected_words:
            user_warnings[user_id] += 1
            try:
                await message.delete()
            except Exception as e:
                print(f"Could not delete bad word message from user {user_id} in chat {chat_id}: {e}")

            warning_text = (
                f"🚫 پیام حاوی کلمات نامناسب است ({', '.join(detected_words)}).\n"
                f"<b>امتیاز هشدار:</b> {user_warnings[user_id]}/{WARN_LIMIT_BAN}"
            )
            await message.answer(warning_text)

    # --- Mute Logic ---
    if user_warnings[user_id] == WARN_LIMIT_MUTE:
        mute_until = datetime.now() + timedelta(minutes=10)
        try:
            await bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=mute_until
            )
            await message.answer(
                f"🔇 کاربر {hlink(message.from_user.full_name, f'tg://user?id={user_id}')} "
                f"به مدت ۱۰ دقیقه میوت شد."
            )
        except Exception as e:
            print(f"Error muting user {user_id} in chat {chat_id}: {e}")
            await message.answer("خطا در میوت کاربر.")

    # --- Ban Logic ---
    if user_warnings[user_id] >= WARN_LIMIT_BAN:
        try:
            await bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            await message.answer(
                f"⛔ کاربر {hlink(message.from_user.full_name, f'tg://user?id={user_id}')} "
                f"به دلیل تکرار تخلفات بن شد."
            )
            del user_warnings[user_id]
        except Exception as e:
            print(f"Error banning user {user_id} in chat {chat_id}: {e}")
            await message.answer("خطا در بن کردن کاربر.")

# --- Main Execution ---
async def webhook_listener():
    # This part is mainly for Render to detect that the app is running and listening.
    # The actual Telegram bot logic runs via Dispatcher.
    # We don't need a separate web framework like Flask/FastAPI if we are only using aiogram.
    # aiogram's Polling method can be run alongside a minimal web server for health checks if needed.
    # For simplicity with aiogram's polling, we rely on Render's internal health checks.
    # If Render requires an explicit HTTP server, we'd need to add Flask/FastAPI.
    print(f"Bot is running in polling mode. Listening on port {WEBHOOK_PORT} for Render.")
    # In a real webhook setup, this would start an HTTP server.
    # For polling, we just keep the script alive.
    while True:
        await asyncio.sleep(3600) # Keep the loop running

async def main():
    # For Web Service on Render, we don't typically set a webhook directly in the bot code
    # unless Render provides the URL and we configure it.
    # We will use polling for receiving messages, but keep the process running for Render.
    await bot.delete_webhook(drop_pending_updates=True) # Ensure no webhook is active initially

    dp.include_router(router)

    # Run the bot polling in one task
    polling_task = asyncio.create_task(dp.start_polling(bot, skip_updates=True))

    # Run a simple task to keep the process alive for Render's Web Service monitoring
    # If Render checks the root URL, this keeps the process running.
    # If Render requires a specific health check endpoint, more setup is needed.
    await webhook_listener() # This loop keeps the main task alive

if __name__ == "__main__":
    load_tickets()
    try:
        # For Render's Web Service, aiogram's polling will run,
        # and Render will monitor the process staying alive.
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped manually.")
    except Exception as e:
        print(f"An error occurred: {e}")
