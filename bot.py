import asyncio
import json
from datetime import datetime, timedelta
from collections import defaultdict

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode
from aiogram.utils.markdown import hlink, hcode
from aiogram.types import CallbackQuery # Import CallbackQuery

# --- Configuration ---
# **URGENT: Replace with your actual token and IDs!**
TOKEN = "8975820451:AAEBZjhBGdFNCjnCcvld09oItdJYnkGCsGU"
STAFF_GROUP_ID = -1004332150226
ADMINS = [1256603181]

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
SPAM_DETECTION_THRESHOLD = 4  # Number of messages within SPAM_INTERVAL to trigger spam
SPAM_INTERVAL = 5  # seconds

# Bad words list - Combined Persian and English offensive terms
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
user_messages = defaultdict(list) # Stores timestamps of recent messages from each user

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

# --- Menu Button Texts ---
BTN_WHITELIST = "📜 Whitelist Request"
BTN_SHOP = "💎 Server Shop"
BTN_SUPPORT = "🆘 Support Ticket"

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

# --- Staff Reply Markup ---
def get_staff_reply_markup(ticket_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="پاسخ دادن", callback_data=f"reply_ticket_{ticket_id}")]
    ])

# --- Handlers ---

# /start command
@router.message(CommandStart())
async def start(message: Message):
    user_id = message.from_user.id
    if user_id not in users:
        users.add(user_id)
        save_users(users)
        welcome_message = (
            f"<b>👋 Welcome to TheFellOmen Server!</b>\n\n"
            "Use the menu below to interact with staff."
        )
    else:
        welcome_message = (
            f"<b>👋 Welcome back to TheFellOmen Server!</b>\n\n"
            "Need something? Use the menu below."
        )

    await message.answer(
        welcome_message,
        reply_markup=get_main_menu()
    )

# Whitelist Request button handler
@router.message(lambda m: m.text == BTN_WHITELIST)
async def whitelist_request(message: Message):
    await message.answer(
        "<b>📜 Whitelist Request</b>\n\n"
        "Please send your Minecraft username and a brief description."
    )

# Server Shop button handler
@router.message(lambda m: m.text == BTN_SHOP)
async def server_shop(message: Message):
    await message.answer(
        "<b>💎 Server Shop</b>\n"
        "Visit our store for amazing deals:\n"
        "https://your-store-link.com" # Replace with your actual store link
    )

# Support Ticket button handler
@router.message(lambda m: m.text == BTN_SUPPORT)
async def support_ticket(message: Message):
    await message.answer(
        "<b>🆘 Support</b>\n"
        "Please describe your issue, and our staff will assist you shortly."
    )

# Forwarding private messages to staff group (Ticket System)
@router.message(lambda m: m.chat.type == "private")
async def handle_private_message(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.full_name

    # Ignore commands
    if message.text and message.text.startswith("/"):
        return

    # Ignore media, ask user to send text
    if message.photo or message.video or message.animation or message.document or message.sticker:
        await message.answer("Please send your issue as a text message.")
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

    # Prepare message for staff group
    ticket_message_to_staff = (
        f"<b>📩 New Ticket #{current_ticket_id}</b>\n\n"
        f"<b>User:</b> {hlink(username, f'tg://user?id={user_id}')}\n"
        f"<b>User ID:</b> {hcode(str(user_id))}\n"
        f"<b>Time:</b> {timestamp}\n\n"
        f"<b>Message:</b>\n{message.text}"
    )

    try:
        await bot.send_message(
            STAFF_GROUP_ID,
            ticket_message_to_staff,
            reply_markup=get_staff_reply_markup(current_ticket_id)
        )
        await message.answer("✅ <b>Your ticket has been sent to staff.</b> They will reply soon.")
    except Exception as e:
        print(f"Error sending ticket to staff group: {e}")
        await message.answer("An error occurred while sending your ticket. Please try again.")


# Callback query handler for staff replies
@router.callback_query(lambda c: c.data and c.data.startswith("reply_ticket_"))
async def handle_reply_ticket_callback(callback_query: CallbackQuery):
    parts = callback_query.data.split("_")
    if len(parts) != 3:
        await callback_query.answer("Invalid callback data.", show_alert=True)
        return

    try:
        ticket_id = int(parts[2])
    except ValueError:
        await callback_query.answer("Invalid ticket ID.", show_alert=True)
        return

    # Store ticket_id in callback state for the next message handler
    await callback_query.message.answer(
        f"<b>Please type your reply for Ticket #{ticket_id}:</b>\n"
        "(This message will be sent to the user)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Cancel", callback_data=f"cancel_reply_{ticket_id}")]
        ])
    )
    # Set state to expect a reply for this ticket
    dp.current_state = callback_query.from_user.id # This is a simplified way, use FSM for better state management
    dp.state_data = {"replying_to_ticket": ticket_id}
    await callback_query.answer() # Acknowledge the callback


# Handler for staff reply messages (now using state)
@router.message(lambda m: m.chat.id == STAFF_GROUP_ID)
async def handle_staff_reply(message: Message):
    # Check if the user is in a state where they are replying to a ticket
    if hasattr(dp, 'current_state') and dp.current_state == message.from_user.id and \
       hasattr(dp, 'state_data') and "replying_to_ticket" in dp.state_data:

        ticket_id = dp.state_data.get("replying_to_ticket")
        if ticket_id is None:
            # If no ticket ID is associated, ignore or handle as a normal message
            return

        reply_text = message.text
        if not reply_text:
            await message.answer("Please send a text reply.")
            return

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
            original_ticket_info = tickets[ticket_id]
            user_id_to_reply = original_ticket_info["user_id"]
            username = original_ticket_info["username"]

            try:
                await bot.send_message(
                    user_id_to_reply,
                    f"<b>💬 Staff Reply (Ticket #{ticket_id}):</b>\n\n{reply_text}"
                )
                await message.answer(f"✅ Reply sent to user {username} (ID: {user_id_to_reply}).")
            except Exception as e:
                print(f"Error sending reply to user {user_id_to_reply}: {e}")
                await message.answer(f"Error sending reply to user {username}. They might have blocked the bot.")
        else:
            await message.answer(f"Ticket #{ticket_id} not found.")

        # Clear state after sending reply
        del dp.current_state
        del dp.state_data

    # Handle messages that are direct replies to the bot's ticket message in staff chat
    elif message.reply_to_message and message.reply_to_message.text and "📩 New Ticket #" in message.reply_to_message.text:
        # Extract ticket ID from the replied message text
        try:
            ticket_id_str = message.reply_to_message.text.split("New Ticket #")[1].split("\n")[0]
            ticket_id = int(ticket_id_str)
        except (IndexError, ValueError):
            await message.answer("Could not determine ticket ID from the replied message.")
            return

        reply_text = message.text
        if not reply_text:
            await message.answer("Please send a text reply.")
            return

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
            original_ticket_info = tickets[ticket_id]
            user_id_to_reply = original_ticket_info["user_id"]
            username = original_ticket_info["username"]

            try:
                await bot.send_message(
                    user_id_to_reply,
                    f"<b>💬 Staff Reply (Ticket #{ticket_id}):</b>\n\n{reply_text}"
                )
                await message.answer(f"✅ Reply sent to user {username} (ID: {user_id_to_reply}).")
            except Exception as e:
                print(f"Error sending reply to user {user_id_to_reply}: {e}")
                await message.answer(f"Error sending reply to user {username}. They might have blocked the bot.")
        else:
            await message.answer(f"Ticket #{ticket_id} not found.")


# Handler for cancelling a reply action
@router.callback_query(lambda c: c.data and c.data.startswith("cancel_reply_"))
async def handle_cancel_reply_callback(callback_query: CallbackQuery):
    if hasattr(dp, 'current_state') and dp.current_state == callback_query.from_user.id:
        del dp.current_state
        del dp.state_data
    await callback_query.message.delete_reply_markup()
    await callback_query.answer("Reply cancelled.")


# Announcement command (for admins)
@router.message(CommandStart("announce")) # Using CommandStart for a simple command handler
async def announce_command(message: Message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        await message.answer("You are not an administrator and do not have permission to send broadcast messages.")
        return

    text_to_announce = message.text.replace("/announce", "").strip()

    if not text_to_announce:
        await message.answer("Please provide a message after the /announce command.\nExample: `/announce Server maintenance starting soon.`")
        return

    sent_count = 0
    failed_users = []
    for uid in users:
        try:
            await bot.send_message(
                uid,
                f"<b>📢 Server Announcement</b>\n\n{text_to_announce}"
            )
            sent_count += 1
        except Exception as e:
            failed_users.append(uid)
            print(f"Failed to send announcement to user {uid}: {e}")
            # Optionally remove user if they block the bot
            # if "bot was blocked by the user" in str(e):
            #     users.remove(uid)

    # save_users(users) # Save if users were removed
    await message.answer(f"✅ Message sent to {sent_count} users.")
    if failed_users:
        await message.answer(f"⚠️ Failed to send to {len(failed_users)} users.")

# Group Security Handler
@router.message(lambda m: m.chat.type in ["group", "supergroup"])
async def group_security_check(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    now = datetime.now()

    # --- Spam Detection ---
    # Filter out old messages outside the interval
    user_messages[user_id] = [
        t for t in user_messages[user_id]
        if (now - t) < timedelta(seconds=SPAM_INTERVAL)
    ]
    user_messages[user_id].append(now)

    if len(user_messages[user_id]) > SPAM_DETECTION_THRESHOLD:
        user_warnings[user_id] += 1
        try:
            await message.delete()
        except Exception as e:
            print(f"Could not delete spam message from user {user_id} in chat {chat_id}: {e}")

        warning_text = (
            f"⚠️ User {hlink(message.from_user.full_name, f'tg://user?id={user_id}')} "
            f"detected for spamming.\n"
            f"<b>Warning Score:</b> {user_warnings[user_id]}/{WARN_LIMIT_BAN}"
        )
        await message.answer(warning_text)
        # Optionally delete warning message after some time
        # await asyncio.sleep(5)
        # await warning_msg.delete()

    # --- Media Blocking ---
    # Check if message contains media (photo, video, animation, sticker)
    if message.photo or message.video or message.animation or message.sticker:
        user_warnings[user_id] += 1
        try:
            await message.delete()
        except Exception as e:
            print(f"Could not delete media message from user {user_id} in chat {chat_id}: {e}")

        warning_text = (
            f"🚫 Sending media (photos, videos, GIFs, stickers) is not allowed in this group.\n"
            f"<b>Warning Score:</b> {user_warnings[user_id]}/{WARN_LIMIT_BAN}"
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
                f"🚫 Message contains inappropriate words ({', '.join(detected_words)}).\n"
                f"<b>Warning Score:</b> {user_warnings[user_id]}/{WARN_LIMIT_BAN}"
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
                f"🔇 User {hlink(message.from_user.full_name, f'tg://user?id={user_id}')} "
                f"has been muted for 10 minutes."
            )
        except Exception as e:
            print(f"Error muting user {user_id} in chat {chat_id}: {e}")
            await message.answer("Error muting user.")

    # --- Ban Logic ---
    if user_warnings[user_id] >= WARN_LIMIT_BAN:
        try:
            await bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            await message.answer(
                f"⛔ User {hlink(message.from_user.full_name, f'tg://user?id={user_id}')} "
                f"has been banned for repeated violations."
            )
            # Clean up warnings after ban
            del user_warnings[user_id]
        except Exception as e:
            print(f"Error banning user {user_id} in chat {chat_id}: {e}")
            await message.answer("Error banning user.")


# --- Main Execution ---
async def main():
    # Delete webhook to ensure polling works correctly
    await bot.delete_webhook(drop_pending_updates=True)

    dp.include_router(router)

    # Start polling for updates
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    # Load tickets on startup
    load_tickets()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped manually.")
    except Exception as e:
        print(f"An error occurred: {e}")
