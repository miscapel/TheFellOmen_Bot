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
from aiogram.types import CallbackQuery

# --- Configuration ---
# **URGENT: Replace with your actual token and IDs!**
TOKEN = "8975820451:AAEBZjhBGdFNCjnCcvld09oItdJYnkGCsGU" # Replace with your actual token
STAFF_GROUP_ID = -1004332150226 # Replace with your staff group ID
ADMINS = [1256603181] # Replace with your admin user IDs

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

# --- Inline Keyboards for Ticket Reasons ---
def get_whitelist_reasons_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Griefing", callback_data="reason_Griefing")],
        [InlineKeyboardButton(text="Hacking", callback_data="reason_Hacking")],
        [InlineKeyboardButton(text="Inappropriate Behavior", callback_data="reason_Inappropriate Behavior")],
        [InlineKeyboardButton(text="Other", callback_data="reason_Other")]
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

# --- State Management for Ticket Process ---
# We'll use a simple dictionary to store user states
user_states = {} # {user_id: {"state": "awaiting_reason" or "awaiting_description", "reason": "...", "ticket_id": ...}}

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
async def whitelist_request_start(message: Message):
    user_id = message.from_user.id
    user_states[user_id] = {"state": "awaiting_reason"}
    await message.answer(
        "<b>📜 Whitelist Request</b>\n\n"
        "Please select the reason for your request:",
        reply_markup=get_whitelist_reasons_keyboard()
    )

# Callback query handler for selecting whitelist reason
@router.callback_query(lambda c: c.data and c.data.startswith("reason_"))
async def handle_whitelist_reason(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    reason = callback_query.data.split("_")[1]

    if user_id not in user_states or user_states[user_id].get("state") != "awaiting_reason":
        await callback_query.answer("Please start again by clicking the 'Whitelist Request' button.", show_alert=True)
        return

    user_states[user_id]["reason"] = reason
    user_states[user_id]["state"] = "awaiting_description"

    # Remove the reason keyboard and ask for description
    await callback_query.message.edit_reply_markup(reply_markup=None)
    await callback_query.message.answer(
        f"<b>Reason selected:</b> {reason}\n\n"
        "Now, please send your Minecraft username and a brief description."
    )
    await callback_query.answer() # Acknowledge the callback

# Handler for sending description after reason is selected
@router.message(lambda m: m.chat.type == "private")
async def handle_whitelist_description(message: Message):
    user_id = message.from_user.id

    if user_id not in user_states or user_states[user_id].get("state") != "awaiting_description":
        # If not in the expected state, treat as a normal private message or ticket
        # Or, if it's a menu button click that didn't update state, handle normally
        if message.text in [BTN_SHOP, BTN_SUPPORT]:
             await handle_other_menu_buttons(message) # Call the handler for shop/support
        elif message.text == BTN_WHITELIST:
             await whitelist_request_start(message) # Restart whitelist process
        else:
             await handle_private_message_as_ticket(message) # Treat as a general ticket if not handled
        return

    description = message.text
    reason = user_states[user_id].get("reason")
    username = message.from_user.username or message.from_user.full_name

    if not reason or not description:
        await message.answer("An error occurred. Please try requesting a whitelist again.")
        del user_states[user_id]
        return

    # Create ticket
    global ticket_id_counter
    ticket_id_counter += 1
    current_ticket_id = ticket_id_counter
    timestamp = datetime.now().isoformat()

    tickets[current_ticket_id] = {
        "user_id": user_id,
        "username": username,
        "reason": reason, # Store the selected reason
        "message": description,
        "timestamp": timestamp,
        "replies": []
    }
    save_tickets()

    # Prepare message for staff group
    ticket_message_to_staff = (
        f"<b>📩 New Whitelist Request #{current_ticket_id}</b>\n\n"
        f"<b>User:</b> {hlink(username, f'tg://user?id={user_id}')}\n"
        f"<b>User ID:</b> {hcode(str(user_id))}\n"
        f"<b>Reason:</b> {reason}\n"
        f"<b>Time:</b> {timestamp}\n\n"
        f"<b>Details:</b>\n{description}"
    )

    try:
        await bot.send_message(
            STAFF_GROUP_ID,
            ticket_message_to_staff,
            reply_markup=get_staff_reply_markup(current_ticket_id)
        )
        await message.answer("✅ <b>Your whitelist request has been sent to staff.</b> They will review it shortly.")
    except Exception as e:
        print(f"Error sending whitelist request to staff group: {e}")
        await message.answer("An error occurred while sending your request. Please try again.")

    # Clear user state after successful submission
    del user_states[user_id]


# Generic handler for other private messages (treat as support ticket if not handled)
@router.message(lambda m: m.chat.type == "private")
async def handle_private_message_as_ticket(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.full_name

    # Ignore commands
    if message.text and message.text.startswith("/"):
        return

    # Ignore media, ask user to send text
    if message.photo or message.video or message.animation or message.document or message.sticker:
        await message.answer("Please send your issue as a text message.")
        return

    if not message.text:
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

    ticket_message_to_staff = (
        f"<b>📩 New Support Ticket #{current_ticket_id}</b>\n\n"
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
        await message.answer("✅ <b>Your support ticket has been sent to staff.</b> They will reply soon.")
    except Exception as e:
        print(f"Error sending support ticket to staff group: {e}")
        await message.answer("An error occurred while sending your ticket. Please try again.")

# Separate handler for shop and support buttons to avoid recursion
async def handle_other_menu_buttons(message: Message):
    if message.text == BTN_SHOP:
        await message.answer(
            "<b>💎 Server Shop</b>\n"
            "Visit our store for amazing deals:\n"
            "https://your-store-link.com" # Replace with your actual store link
        )
    elif message.text == BTN_SUPPORT:
        await message.answer(
            "<b>🆘 Support</b>\n"
            "Please describe your issue, and our staff will assist you shortly."
        )


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

    # Set state for the staff user to expect a reply message
    staff_user_id = callback_query.from_user.id
    user_states[staff_user_id] = {"state": "staff_replying", "ticket_id": ticket_id}

    await callback_query.message.answer(
        f"<b>Please type your reply for Ticket #{ticket_id}:</b>\n"
        "(This message will be sent to the user)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Cancel", callback_data=f"cancel_reply_{ticket_id}")]
        ])
    )
    await callback_query.answer()

# Handler for staff reply messages (using state)
@router.message(lambda m: m.chat.id == STAFF_GROUP_ID)
async def handle_staff_reply(message: Message):
    staff_user_id = message.from_user.id

    if staff_user_id in user_states and user_states[staff_user_id].get("state") == "staff_replying":
        ticket_id = user_states[staff_user_id].get("ticket_id")
        reply_text = message.text

        if not reply_text:
            await message.answer("Please send a text reply.")
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
        del user_states[staff_user_id]
        return

    # Handle direct replies to the bot's ticket message in staff chat (if not using state)
    elif message.reply_to_message and message.reply_to_message.text and ("New Ticket #" in message.reply_to_message.text or "New Whitelist Request #" in message.reply_to_message.text):
        try:
            ticket_id_str = message.reply_to_message.text.split("#")[1].split("\n")[0]
            ticket_id = int(ticket_id_str)
        except (IndexError, ValueError):
            await message.answer("Could not determine ticket ID from the replied message.")
            return

        reply_text = message.text
        if not reply_text:
            await message.answer("Please send a text reply.")
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
    staff_user_id = callback_query.from_user.id
    if staff_user_id in user_states and user_states[staff_user_id].get("state") == "staff_replying":
        del user_states[staff_user_id]
    await callback_query.message.delete_reply_markup()
    await callback_query.answer("Reply cancelled.")


# Announcement command (for admins)
@router.message(CommandStart("announce"))
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
    user_messages[user_id] = [t for t in user_messages[user_id] if (now - t) < timedelta(seconds=SPAM_INTERVAL)]
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

    # --- Media Blocking ---
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
            del user_warnings[user_id]
        except Exception as e:
            print(f"Error banning user {user_id} in chat {chat_id}: {e}")
            await message.answer("Error banning user.")


# --- Main Execution ---
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    dp.include_router(router)
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    load_tickets()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped manually.")
    except Exception as e:
        print(f"An error occurred: {e}")
