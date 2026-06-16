import asyncio
import json
from datetime import datetime, timedelta
from collections import defaultdict

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode
from aiogram.utils.markdown import hlink, hcode

# --- Configuration ---
TOKEN = "8975820451:AAEBZjhBGdFNCjnCcvld09oItdJYnkGCsGU"  # **URGENT: Replace with your actual token!**
STAFF_GROUP_ID = -1004332150226  # Replace with your staff group ID
ADMINS = [1256603181]  # Replace with your admin user IDs

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
SPAM_LIMIT = 4
SPAM_INTERVAL = 5  # seconds
BAD_WORDS = ["porn", "sex", "xxx", "کص", "کون", "جنده"] # Added Persian bad words

user_warnings = defaultdict(int)
user_messages = defaultdict(list) # Stores timestamps of messages from each user

# --- Ticket System ---
TICKET_FILE = "tickets.json"
ticket_id_counter = 0
tickets = {} # {ticket_id: {"user_id": ..., "username": ..., "message": ..., "timestamp": ..., "replies": []}}

def load_tickets():
    global ticket_id_counter
    try:
        with open(TICKET_FILE, "r") as f:
            data = json.load(f)
            tickets.update(data)
            if tickets:
                ticket_id_counter = max(tickets.keys(), key=int)
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


# --- Menu ---
def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📜 درخواست لیست سفید")],
            [KeyboardButton(text="💎 فروشگاه سرور")],
            [KeyboardButton(text="🆘 تیکت پشتیبانی")]
        ],
        resize_keyboard=True
    )

def get_staff_reply_markup(ticket_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="پاسخ دادن", callback_data=f"reply_ticket_{ticket_id}")]
    ])

# --- Handlers ---

# /start command
@router.message(Command("start"))
async def start(message: Message):
    user_id = message.from_user.id
    if user_id not in users:
        users.add(user_id)
        save_users(users)
        welcome_message = (
            f"<b>👋 به سرور TheFellOmen خوش آمدید!</b>\n\n"
            "با استفاده از منوی زیر می‌توانید با ادمین‌ها در ارتباط باشید."
        )
    else:
        welcome_message = (
            f"<b>👋 خوش برگشتی به سرور TheFellOmen!</b>\n\n"
            "هنوز سوالی داری؟ از منوی زیر استفاده کن."
        )

    await message.answer(
        welcome_message,
        reply_markup=get_main_menu()
    )

# Whitelist Request button
@router.message(lambda m: m.text == "📜 درخواست لیست سفید")
async def whitelist_request(message: Message):
    await message.answer(
        "<b>📜 درخواست لیست سفید</b>\n\n"
        "لطفاً نام کاربری Minecraft و توضیحات خود را ارسال کنید."
    )

# Server Shop button
@router.message(lambda m: m.text == "💎 فروشگاه سرور")
async def server_shop(message: Message):
    await message.answer(
        "<b>💎 فروشگاه سرور</b>\n"
        "لینک فروشگاه: https://your-store-link.com" # Replace with your actual store link
    )

# Support Ticket button
@router.message(lambda m: m.text == "🆘 تیکت پشتیبانی")
async def support_ticket(message: Message):
    await message.answer(
        "<b>🆘 پشتیبانی</b>\n"
        "مشکل خود را شرح دهید تا ادمین‌ها شما را راهنمایی کنند."
    )

# Forwarding private messages to staff group (Ticket System)
@router.message(lambda m: m.chat.type == "private")
async def handle_private_message(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.full_name

    # Ignore commands
    if message.text and message.text.startswith("/"):
        return

    # Ignore media messages for ticket content, ask user to send text
    if message.photo or message.video or message.animation or message.document or message.sticker:
        await message.answer("لطفاً مشکل خود را به صورت متنی ارسال کنید.")
        return

    if not message.text: # Ignore empty messages
        return

    # Create ticket
    global ticket_id_counter
    ticket_id_counter += 1
    current_ticket_id = ticket_id_counter
    timestamp = datetime.now().isoformat()

    tickets[current_ticket_id] = {
        "user_id": user_id,
        "username": username,
        "message": message.text,
        "timestamp": timestamp,
        "replies": []
    }
    save_tickets()

    # Prepare message for staff group (using invisible markdown for message content)
    ticket_message_to_staff = (
        f"<b>📩 تیکت جدید #{current_ticket_id}</b>\n\n"
        f"<b>کاربر:</b> {hlink(username, f'tg://user?id={user_id}')}\n"
        f"<b>آی‌دی کاربر:</b> {hcode(str(user_id))}\n"
        f"<b>زمان:</b> {timestamp}\n\n"
        f"<b>پیام:</b>\n{message.text}" # User's message is directly visible here
    )

    # Send to staff group with an inline button to reply
    try:
        await bot.send_message(
            STAFF_GROUP_ID,
            ticket_message_to_staff,
            reply_markup=get_staff_reply_markup(current_ticket_id)
        )
        await message.answer("✅ <b>تیکت شما با موفقیت ارسال شد.</b> ادمین‌ها به زودی پاسخ خواهند داد.")
    except Exception as e:
        print(f"Error sending ticket to staff group: {e}")
        await message.answer("خطایی در ارسال تیکت رخ داد. لطفاً دوباره تلاش کنید.")


# Callback query handler for staff replies
@router.callback_query(lambda c: c.data and c.data.startswith("reply_ticket_"))
async def handle_reply_ticket_callback(callback_query: CallbackQuery):
    ticket_id_str = callback_query.data.split("_")[2]
    try:
        ticket_id = int(ticket_id_str)
    except ValueError:
        await callback_query.answer("شناسه تیکت نامعتبر است.", show_alert=True)
        return

    # Ask staff for the reply message
    await callback_query.message.answer(
        f"<b>پاسخ خود را برای تیکت #{ticket_id} ارسال کنید:</b>\n"
        "(این پیام به کاربر ارسال خواهد شد)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="لغو", callback_data=f"cancel_reply_{ticket_id}")]
        ])
    )
    # Store the ticket ID in the callback data state for the next message
    callback_query.data += f"_{ticket_id}" # Append ticket_id for the next handler


# Handler for staff reply messages
@router.message(lambda m: m.chat.id == STAFF_GROUP_ID and m.reply_to_message)
async def handle_staff_reply(message: Message):
    replied_message = message.reply_to_message
    if not replied_message.reply_markup or not replied_message.reply_markup.inline_keyboard:
        return # Not a ticket message

    # Extract ticket ID from the original ticket message
    ticket_id_str = None
    if replied_message.text and "<b>ای‌دی کاربر:</b>" in replied_message.text:
         for line in replied_message.text.split('\n'):
            if "<b>ای‌دی کاربر:</b>" in line:
                 # Extract user ID from the reply_to_message's text
                 parts = line.split("<code>")
                 if len(parts) > 1:
                    user_id_str = parts[1].split("</code>")[0]
                    try:
                        user_id = int(user_id_str)
                    except ValueError:
                        await message.answer("خطا در استخراج آی‌دی کاربر.")
                        return
                    break
    else:
        # Fallback if the structure is different, try to parse from callback data if available
        # This part might need adjustment based on how you store ticket IDs in the DB
        # For now, we assume direct text parsing is primary
        await message.answer("لطفاً به پیام تیکت اصلی ریپلای کنید.")
        return


    if user_id and message.text:
        reply_text = message.text
        timestamp = datetime.now().isoformat()

        # Add reply to the ticket data
        if ticket_id in tickets:
            tickets[ticket_id]["replies"].append({
                "sender": "staff",
                "message": reply_text,
                "timestamp": timestamp
            })
            save_tickets()

        # Forward the reply to the user
        try:
            await bot.send_message(
                user_id,
                f"<b>💬 پاسخ از پشتیبانی (تیکت #{ticket_id}):</b>\n\n{reply_text}"
            )
            await message.answer(f"✅ پاسخ به کاربر (ID: {user_id}) ارسال شد.")
        except Exception as e:
            print(f"Error sending reply to user {user_id}: {e}")
            await message.answer(f"خطا در ارسال پاسخ به کاربر (ID: {user_id}).")
    else:
        await message.answer("لطفاً متن پاسخی را ارسال کنید.")


# Handler for cancelling a reply action
@router.callback_query(lambda c: c.data and c.data.startswith("cancel_reply_"))
async def handle_cancel_reply_callback(callback_query: CallbackQuery):
    await callback_query.message.delete_reply_markup()
    await callback_query.answer("عملیات لغو شد.")


# Announcement command (for admins)
@router.message(Command("announce"))
async def announce_command(message: Message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        await message.answer("شما ادمین نیستید و اجازه ارسال پیام عمومی ندارید.")
        return

    text_to_announce = message.text.replace("/announce", "").strip()

    if not text_to_announce:
        await message.answer("لطفاً بعد از دستور /announce، متن پیام خود را بنویسید.\nمثال: `/announce به زودی سرور آپدیت می‌شود.`")
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
            # Optionally remove user if they block the bot
            # if "bot was blocked by the user" in str(e):
            #     users.remove(uid)

    # save_users(users) # Save if users were removed
    await message.answer(f"✅ پیام به {sent_count} کاربر ارسال شد.")
    if failed_users:
        await message.answer(f"⚠️ ارسال به {len(failed_users)} کاربر ناموفق بود.")

# Group Security Handler
@router.message(lambda m: m.chat.type in ["group", "supergroup"])
async def group_security_check(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    now = datetime.now()

    # --- Spam Detection ---
    user_messages[user_id] = [
        t for t in user_messages[user_id]
        if (now - t) < timedelta(seconds=SPAM_INTERVAL)
    ]
    user_messages[user_id].append(now)

    if len(user_messages[user_id]) > SPAM_LIMIT:
        user_warnings[user_id] += 1
        await message.delete()
        warning_msg = await message.answer(
            f"⚠️ کاربر {hlink(message.from_user.full_name, f'tg://user?id={user_id}')} "
            f"به دلیل اسپم شناسایی شد.\n"
            f"<b>امتیاز هشدار:</b> {user_warnings[user_id]}/{WARN_LIMIT_BAN}"
        )
        # Optionally delete warning message after some time
        # await asyncio.sleep(5)
        # await warning_msg.delete()

    # --- Media Blocking ---
    if message.photo or message.video or message.animation or message.sticker:
        user_warnings[user_id] += 1
        await message.delete()
        warning_msg = await message.answer(
            f"🚫 ارسال مدیا (عکس، ویدیو، گیف، استیکر) در این گروه ممنوع است.\n"
            f"<b>امتیاز هشدار:</b> {user_warnings[user_id]}/{WARN_LIMIT_BAN}"
        )

    # --- Bad Words Filter ---
    if message.text:
        txt_lower = message.text.lower()
        detected_words = [word for word in BAD_WORDS if word in txt_lower]
        if detected_words:
            user_warnings[user_id] += 1
            await message.delete()
            warning_msg = await message.answer(
                f"🚫 پیام حاوی کلمات نامناسب ({', '.join(detected_words)}) است.\n"
                f"<b>امتیاز هشدار:</b> {user_warnings[user_id]}/{WARN_LIMIT_BAN}"
            )

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
            await message.answer("خطا در میوت کردن کاربر.")

    # --- Ban Logic ---
    if user_warnings[user_id] >= WARN_LIMIT_BAN:
        try:
            await bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            await message.answer(
                f"⛔ کاربر {hlink(message.from_user.full_name, f'tg://user?id={user_id}')} "
                f"به دلیل نقض مکرر قوانین بن شد."
            )
            # Remove warnings after ban to prevent re-warning if unbanned later
            del user_warnings[user_id]
        except Exception as e:
            print(f"Error banning user {user_id} in chat {chat_id}: {e}")
            await message.answer("خطا در بن کردن کاربر.")


# --- Main Execution ---
async def main():
    # It's recommended to delete webhook if using polling, especially on Render
    await bot.delete_webhook(drop_pending_updates=True)

    dp.include_router(router)

    # Start polling
    await dp.start_polling(bot, skip_updates=True) # skip_updates=True is good for production

if __name__ == "__main__":
    # Load tickets on startup
    load_tickets()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped manually.")
    except Exception as e:
        print(f"An error occurred: {e}")
