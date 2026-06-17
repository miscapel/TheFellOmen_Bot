import asyncio
import html
import json
import logging
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatType, ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from dotenv import load_dotenv
from flask import Flask


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
STAFF_GROUP_ID = os.getenv("STAFF_GROUP_ID")
ADMIN_ID = os.getenv("ADMIN_ID", "0")
PORT = int(os.getenv("PORT", "10000"))

WELCOME_STICKER_ID = os.getenv("WELCOME_STICKER_ID", "")
SUCCESS_STICKER_ID = os.getenv("SUCCESS_STICKER_ID", "")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

if not STAFF_GROUP_ID:
    raise RuntimeError("STAFF_GROUP_ID is not set")

try:
    STAFF_GROUP_ID = int(STAFF_GROUP_ID)
except ValueError:
    raise RuntimeError("STAFF_GROUP_ID must be a number")

try:
    ADMIN_ID = int(ADMIN_ID)
except ValueError:
    ADMIN_ID = 0


bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

dp = Dispatcher(storage=MemoryStorage())
app = Flask(__name__)

USERS_FILE = Path("users.json")

TICKETS = {}
STAFF_MESSAGE_TO_TICKET = {}
USER_IDS = set()


class UserState(StatesGroup):
    punishment_appeal = State()
    whitelist = State()
    contact_staff = State()
    rank_shop_message = State()
    coin_shop_message = State()


class StaffState(StatesGroup):
    replying = State()


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def safe(value) -> str:
    if value is None:
        return "-"
    return html.escape(str(value))


def is_admin(user_id: int) -> bool:
    return ADMIN_ID != 0 and user_id == ADMIN_ID


def load_users():
    global USER_IDS

    if not USERS_FILE.exists():
        USER_IDS = set()
        return

    try:
        data = json.loads(USERS_FILE.read_text(encoding="utf-8"))
        USER_IDS = {int(user_id) for user_id in data}
    except Exception:
        USER_IDS = set()


def save_users():
    try:
        USERS_FILE.write_text(
            json.dumps(sorted(USER_IDS), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as error:
        logging.warning("Could not save users: %s", error)


def remember_user(user: types.User | None):
    if not user:
        return

    if user.id not in USER_IDS:
        USER_IDS.add(user.id)
        save_users()


def user_label(user: types.User) -> str:
    username = f"@{user.username}" if user.username else user.full_name
    return f"{safe(username)} | ID: <code>{user.id}</code>"


def main_menu_keyboard() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="⚖️ Punishment Appeal",
                    callback_data="menu:punishment",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="✅ Whitelist",
                    callback_data="menu:whitelist",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="🎧 Contact Staff",
                    callback_data="menu:contact",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="🛒 Shop",
                    callback_data="menu:shop",
                )
            ],
        ]
    )


def shop_keyboard() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="👑 Rank Shop",
                    callback_data="shop:rank",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="🪙 Coin Shop",
                    callback_data="shop:coin",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="🔙 Back",
                    callback_data="menu:back",
                )
            ],
        ]
    )


def staff_ticket_keyboard(ticket_id: str) -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="✅ Accept",
                    callback_data=f"ticket:accept:{ticket_id}",
                ),
                types.InlineKeyboardButton(
                    text="❌ Deny",
                    callback_data=f"ticket:deny:{ticket_id}",
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text="💬 Reply",
                    callback_data=f"ticket:reply:{ticket_id}",
                )
            ],
        ]
    )


async def set_bot_commands():
    commands = [
        BotCommand(command="start", description="Main menu"),
        BotCommand(command="help", description="Bot guide"),
        BotCommand(command="broadcast", description="Admin announcement"),
    ]
    await bot.set_my_commands(commands)


async def send_optional_sticker(chat_id: int, sticker_id: str):
    if not sticker_id:
        return

    try:
        await bot.send_sticker(chat_id=chat_id, sticker=sticker_id)
    except Exception as error:
        logging.warning("Could not send sticker: %s", error)


async def copy_message_to_user(target_user_id: int, message: types.Message):
    try:
        await message.copy_to(chat_id=target_user_id)
        return True
    except Exception as error:
        logging.warning("Could not copy message to user %s: %s", target_user_id, error)
        return False


async def create_ticket(
    *,
    ticket_type: str,
    user: types.User,
    header_text: str,
    user_message: types.Message | None = None,
) -> str:
    ticket_id = uuid.uuid4().hex[:10]

    TICKETS[ticket_id] = {
        "id": ticket_id,
        "type": ticket_type,
        "user_id": user.id,
        "user_name": user.full_name,
        "username": user.username,
        "created_at": now_text(),
        "status": "open",
    }

    sent_header = await bot.send_message(
        chat_id=STAFF_GROUP_ID,
        text=header_text,
        reply_markup=staff_ticket_keyboard(ticket_id),
    )

    TICKETS[ticket_id]["staff_message_id"] = sent_header.message_id
    STAFF_MESSAGE_TO_TICKET[sent_header.message_id] = ticket_id

    if user_message:
        copied = await user_message.copy_to(chat_id=STAFF_GROUP_ID)
        STAFF_MESSAGE_TO_TICKET[copied.message_id] = ticket_id

    return ticket_id


async def finish_user_ticket(message: types.Message, state: FSMContext):
    await send_optional_sticker(message.chat.id, SUCCESS_STICKER_ID)
    await message.answer(
        "✅ درخواست شما برای استف ارسال شد.\n\n"
        "لطفاً منتظر بررسی بمانید. اگر رسید خرید، عکس یا ویدیو فرستاده باشید، همان هم برای استف ارسال شده است."
    )
    await state.clear()


@dp.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    remember_user(message.from_user)
    await state.clear()

    await send_optional_sticker(message.chat.id, WELCOME_STICKER_ID)

    text = (
        "🌙 <b>Welcome to TheFellOmen</b>\n\n"
        "یکی از بخش‌های زیر را انتخاب کن:\n\n"
        "⚖️ <b>Punishment Appeal</b> - درخواست بررسی بن/میوت\n"
        "✅ <b>Whitelist</b> - درخواست وایت‌لیست\n"
        "🎧 <b>Contact Staff</b> - ارتباط مستقیم با استف\n"
        "🛒 <b>Shop</b> - خرید رنک و کوین"
    )

    await message.answer(text, reply_markup=main_menu_keyboard())


@dp.message(Command("help"))
async def help_command(message: types.Message):
    remember_user(message.from_user)

    text = (
        "📌 <b>راهنمای ربات</b>\n\n"
        "از /start منوی اصلی را باز کن.\n\n"
        "در تیکت‌ها می‌توانی این‌ها را بفرستی:\n"
        "• متن\n"
        "• عکس\n"
        "• ویدیو\n"
        "• رسید خرید\n"
        "• فایل\n"
        "• استیکر\n\n"
        "استف هم می‌تواند با ریپلای کردن روی تیکت، متن یا مدیا برای شما ارسال کند."
    )

    await message.answer(text)


@dp.callback_query(F.data == "menu:back")
async def back_to_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()

    await callback.message.edit_text(
        "🌙 <b>TheFellOmen Menu</b>\n\n"
        "یکی از بخش‌های زیر را انتخاب کن:",
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()


@dp.callback_query(F.data == "menu:punishment")
async def open_punishment_appeal(callback: types.CallbackQuery, state: FSMContext):
    remember_user(callback.from_user)
    await state.set_state(UserState.punishment_appeal)

    text = (
        "⚖️ <b>Punishment Appeal</b>\n\n"
        "پیام خودت را بفرست.\n"
        "می‌توانی متن، عکس، ویدیو یا فایل ارسال کنی.\n\n"
        "فرمت پیشنهادی:\n"
        "<code>Username: Steve\n"
        "Punishment ID: 12345\n"
        "Reason: درخواست آن‌بن\n"
        "Message: توضیحات کامل</code>"
    )

    await callback.message.edit_text(text)
    await callback.answer()


@dp.message(UserState.punishment_appeal)
async def receive_punishment_appeal(message: types.Message, state: FSMContext):
    remember_user(message.from_user)

    text_content = message.text or message.caption or "Media/File message"

    header = (
        "⚖️ <b>New Punishment Appeal</b>\n\n"
        f"👤 User: {user_label(message.from_user)}\n"
        f"🕒 Time: {safe(now_text())}\n"
        f"🆔 Ticket: <code>pending</code>\n\n"
        f"📝 Preview:\n{safe(text_content)}"
    )

    ticket_id = await create_ticket(
        ticket_type="Punishment Appeal",
        user=message.from_user,
        header_text=header,
        user_message=message,
    )

    await bot.send_message(
        chat_id=STAFF_GROUP_ID,
        text=f"🆔 Ticket ID: <code>{ticket_id}</code>",
    )

    await finish_user_ticket(message, state)


@dp.callback_query(F.data == "menu:whitelist")
async def open_whitelist(callback: types.CallbackQuery, state: FSMContext):
    remember_user(callback.from_user)
    await state.set_state(UserState.whitelist)

    text = (
        "✅ <b>Whitelist Request</b>\n\n"
        "یوزرنیم ماینکرفت خودت را بفرست.\n"
        "اگر لازم بود، می‌توانی عکس یا ویدیو هم بفرستی."
    )

    await callback.message.edit_text(text)
    await callback.answer()


@dp.message(UserState.whitelist)
async def receive_whitelist(message: types.Message, state: FSMContext):
    remember_user(message.from_user)

    text_content = message.text or message.caption or "Media/File message"

    header = (
        "✅ <b>New Whitelist Request</b>\n\n"
        f"👤 User: {user_label(message.from_user)}\n"
        f"🕒 Time: {safe(now_text())}\n\n"
        f"📝 Message:\n{safe(text_content)}"
    )

    await create_ticket(
        ticket_type="Whitelist",
        user=message.from_user,
        header_text=header,
        user_message=message,
    )

    await finish_user_ticket(message, state)


@dp.callback_query(F.data == "menu:contact")
async def open_contact_staff(callback: types.CallbackQuery, state: FSMContext):
    remember_user(callback.from_user)
    await state.set_state(UserState.contact_staff)

    text = (
        "🎧 <b>Contact Staff</b>\n\n"
        "پیام خودت را برای استف بفرست.\n"
        "می‌توانی متن، عکس، ویدیو، فایل یا استیکر ارسال کنی.\n\n"
        "فرمت پیشنهادی:\n"
        "<code>Reason: مشکل خرید\n"
        "Message: توضیحات کامل</code>"
    )

    await callback.message.edit_text(text)
    await callback.answer()


@dp.message(UserState.contact_staff)
async def receive_contact_staff(message: types.Message, state: FSMContext):
    remember_user(message.from_user)

    text_content = message.text or message.caption or "Media/File message"

    header = (
        "🎧 <b>New Contact Staff Ticket</b>\n\n"
        f"👤 User: {user_label(message.from_user)}\n"
        f"🕒 Time: {safe(now_text())}\n\n"
        f"📝 Message:\n{safe(text_content)}"
    )

    await create_ticket(
        ticket_type="Contact Staff",
        user=message.from_user,
        header_text=header,
        user_message=message,
    )

    await finish_user_ticket(message, state)


@dp.callback_query(F.data == "menu:shop")
async def open_shop(callback: types.CallbackQuery, state: FSMContext):
    remember_user(callback.from_user)
    await state.clear()

    text = (
        "🛒 <b>TheFellOmen Shop</b>\n\n"
        "بخش مورد نظر را انتخاب کن:"
    )

    await callback.message.edit_text(text, reply_markup=shop_keyboard())
    await callback.answer()


@dp.callback_query(F.data == "shop:rank")
async def open_rank_shop(callback: types.CallbackQuery, state: FSMContext):
    remember_user(callback.from_user)
    await state.set_state(UserState.rank_shop_message)

    text = (
        "👑 <b>Rank Shop</b>\n\n"
        "VIP » 49,000 Toman\n"
        "Elite » 100,000 Toman\n"
        "TheFellOmen » 190,000 Toman\n"
        "Sponsor » 250,000 Toman\n"
        "Lover » 400,000 Toman\n\n"
        "رنک مورد نظر، یوزرنیم و رسید خرید را بفرست.\n"
        "می‌توانی عکس رسید یا ویدیو هم ارسال کنی."
    )

    await callback.message.edit_text(text)
    await callback.answer()


@dp.message(UserState.rank_shop_message)
async def receive_rank_shop_message(message: types.Message, state: FSMContext):
    remember_user(message.from_user)

    text_content = message.text or message.caption or "Media/File message"

    header = (
        "👑 <b>New Rank Shop Request</b>\n\n"
        f"👤 User: {user_label(message.from_user)}\n"
        f"🕒 Time: {safe(now_text())}\n\n"
        f"📝 Message:\n{safe(text_content)}"
    )

    await create_ticket(
        ticket_type="Shop - Rank",
        user=message.from_user,
        header_text=header,
        user_message=message,
    )

    await finish_user_ticket(message, state)


@dp.callback_query(F.data == "shop:coin")
async def open_coin_shop(callback: types.CallbackQuery, state: FSMContext):
    remember_user(callback.from_user)
    await state.set_state(UserState.coin_shop_message)

    text = (
        "🪙 <b>Coin Shop</b>\n\n"
        "50 Coin » 15,000 Toman\n"
        "100 Coins » 30,000 Toman\n"
        "150 Coins » 55,000 Toman\n"
        "200 Coins » 80,000 Toman\n"
        "250 Coins » 150,000 Toman\n\n"
        "مقدار کوین، یوزرنیم و رسید خرید را بفرست.\n"
        "می‌توانی عکس رسید یا ویدیو هم ارسال کنی."
    )

    await callback.message.edit_text(text)
    await callback.answer()


@dp.message(UserState.coin_shop_message)
async def receive_coin_shop_message(message: types.Message, state: FSMContext):
    remember_user(message.from_user)

    text_content = message.text or message.caption or "Media/File message"

    header = (
        "🪙 <b>New Coin Shop Request</b>\n\n"
        f"👤 User: {user_label(message.from_user)}\n"
        f"🕒 Time: {safe(now_text())}\n\n"
        f"📝 Message:\n{safe(text_content)}"
    )

    await create_ticket(
        ticket_type="Shop - Coin",
        user=message.from_user,
        header_text=header,
        user_message=message,
    )

    await finish_user_ticket(message, state)


@dp.callback_query(F.data.startswith("ticket:"))
async def handle_ticket_buttons(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")

    if len(parts) != 3:
        await callback.answer("Invalid data.", show_alert=True)
        return

    _, action, ticket_id = parts
    ticket = TICKETS.get(ticket_id)

    if not ticket:
        await callback.answer("Ticket not found. Bot may have restarted.", show_alert=True)
        return

    player_id = ticket["user_id"]

    if action == "accept":
        ticket["status"] = "accepted"

        await send_optional_sticker(player_id, SUCCESS_STICKER_ID)
        await bot.send_message(
            chat_id=player_id,
            text=(
                "✅ <b>Your request has been accepted.</b>\n\n"
                "درخواست شما توسط استف تایید شد."
            ),
        )

        await callback.message.reply("✅ Accepted")
        await callback.answer("Accepted")

    elif action == "deny":
        ticket["status"] = "denied"

        await bot.send_message(
            chat_id=player_id,
            text=(
                "❌ <b>Your request has been denied.</b>\n\n"
                "درخواست شما توسط استف رد شد."
            ),
        )

        await callback.message.reply("❌ Denied")
        await callback.answer("Denied")

    elif action == "reply":
        await state.set_state(StaffState.replying)
        await state.update_data(ticket_id=ticket_id)

        await callback.message.reply(
            "💬 پیام بعدی شما برای پلیر ارسال می‌شود.\n"
            "می‌توانید متن، عکس، ویدیو، فایل یا استیکر بفرستید."
        )
        await callback.answer("Send your reply now")

    else:
        await callback.answer("Invalid action.", show_alert=True)


@dp.message(StaffState.replying, F.chat.id == STAFF_GROUP_ID)
async def staff_reply_by_button(message: types.Message, state: FSMContext):
    data = await state.get_data()
    ticket_id = data.get("ticket_id")
    ticket = TICKETS.get(ticket_id)

    if not ticket:
        await message.reply("Ticket not found. Bot may have restarted.")
        await state.clear()
        return

    ok = await copy_message_to_user(ticket["user_id"], message)

    if ok:
        await message.reply("✅ Reply sent to player.")
    else:
        await message.reply("❌ Could not send reply.")

    await state.clear()


@dp.message(F.chat.id == STAFF_GROUP_ID)
async def staff_direct_reply(message: types.Message):
    if not message.reply_to_message:
        return

    ticket_id = STAFF_MESSAGE_TO_TICKET.get(message.reply_to_message.message_id)

    if not ticket_id:
        return

    ticket = TICKETS.get(ticket_id)

    if not ticket:
        await message.reply("Ticket not found. Bot may have restarted.")
        return

    ok = await copy_message_to_user(ticket["user_id"], message)

    if ok:
        await message.reply("✅ Reply sent to player.")
    else:
        await message.reply("❌ Could not send reply.")


@dp.message(Command("broadcast"))
async def broadcast_command(message: types.Message):
    remember_user(message.from_user)

    if not is_admin(message.from_user.id):
        await message.reply("❌ You are not allowed to use broadcast.")
        return

    if not USER_IDS:
        await message.reply("No users found yet.")
        return

    sent_count = 0
    failed_count = 0

    if message.reply_to_message:
        for user_id in list(USER_IDS):
            try:
                await message.reply_to_message.copy_to(chat_id=user_id)
                sent_count += 1
                await asyncio.sleep(0.05)
            except Exception:
                failed_count += 1

        await message.reply(
            f"📣 Broadcast finished.\n\n"
            f"✅ Sent: {sent_count}\n"
            f"❌ Failed: {failed_count}"
        )
        return

    text = message.text or ""
    announcement = text.replace("/broadcast", "", 1).strip()

    if not announcement:
        await message.reply(
            "برای ارسال همگانی یکی از این دو روش را استفاده کن:\n\n"
            "1) <code>/broadcast متن پیام</code>\n"
            "2) روی عکس/ویدیو/پیام ریپلای کن و بنویس <code>/broadcast</code>"
        )
        return

    final_text = (
        "📣 <b>TheFellOmen Announcement</b>\n\n"
        f"{safe(announcement)}"
    )

    for user_id in list(USER_IDS):
        try:
            await bot.send_message(chat_id=user_id, text=final_text)
            sent_count += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed_count += 1

    await message.reply(
        f"📣 Broadcast finished.\n\n"
        f"✅ Sent: {sent_count}\n"
        f"❌ Failed: {failed_count}"
    )


@dp.message(F.chat.type == ChatType.PRIVATE)
async def private_fallback(message: types.Message):
    remember_user(message.from_user)

    await message.answer(
        "برای استفاده از ربات، از منوی زیر انتخاب کن:",
        reply_markup=main_menu_keyboard(),
    )


@app.route("/")
def home():
    return "TheFellOmen Bot is running!"


def run_flask():
    app.run(host="0.0.0.0", port=PORT)


async def main():
    load_users()
    await set_bot_commands()

    logging.info("Starting Flask server thread...")
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    logging.info("Starting bot polling...")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
