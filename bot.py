import os
import uuid
import asyncio
import threading

from flask import Flask
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# --- CONFIG ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
STAFF_GROUP_ID = int(os.getenv("STAFF_GROUP_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# دیتابیس موقت برای ذخیره یوزرهای تیکت
TICKETS = {}

# --- KEEP ALIVE (FOR RENDER) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "TheFellOmen Bot is Online"

def run_web():
    app.run(host="0.0.0.0", port=10000)

# --- STATES ---
class PunishmentFlow(StatesGroup):
    username = State()
    punish_id = State()
    reason = State()
    message = State()

class WhitelistFlow(StatesGroup):
    username = State()

class SupportFlow(StatesGroup):
    message = State()

class StaffReplyFlow(StatesGroup):
    message = State()

# --- KEYBOARDS ---
def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📜 Whitelist Request", callback_data="btn_whitelist")],
        [InlineKeyboardButton(text="💎 Server Shop", callback_data="btn_shop")],
        [InlineKeyboardButton(text="🆘 Support Ticket", callback_data="btn_support")],
        [InlineKeyboardButton(text="⚖️ Punishment Appeal", callback_data="btn_punishment")]
    ])

def back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back to Menu", callback_data="start_menu")]
    ])

def staff_action_kb(ticket_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Accept", callback_data=f"staff_accept_{ticket_id}"),
            InlineKeyboardButton(text="❌ Deny", callback_data=f"staff_deny_{ticket_id}")
        ],
        [InlineKeyboardButton(text="💬 Reply to User", callback_data=f"staff_reply_{ticket_id}")]
    ])

# --- BASIC HANDLERS ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "Welcome to TheFellOmen Official Bot\n\n"
        "Please select an option from the menu below to continue.",
        reply_markup=main_menu_kb()
    )

@dp.callback_query(F.data == "start_menu")
async def back_to_menu(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text(
        "Main Menu\n\n"
        "Please select an option from the menu below.",
        reply_markup=main_menu_kb()
    )

# --- WHITELIST SECTION ---
@dp.callback_query(F.data == "btn_whitelist")
async def start_whitelist(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        "Whitelist Request\n\n"
        "Please enter your Minecraft Username exactly as it appears in-game.",
        reply_markup=back_kb()
    )
    await state.set_state(WhitelistFlow.username)

@dp.message(WhitelistFlow.username)
async def process_whitelist(message: types.Message, state: FSMContext):
    ticket_id = str(uuid.uuid4())[:8]
    TICKETS[ticket_id] = message.from_user.id
    
    # Notify Staff
    staff_msg = (
        "New Whitelist Request\n\n"
        f"User: {message.from_user.full_name}\n"
        f"ID: {message.from_user.id}\n"
        f"Minecraft Username: {message.text}"
    )
    await bot.send_message(STAFF_GROUP_ID, staff_msg, reply_markup=staff_action_kb(ticket_id))
    
    await message.answer("Your request has been submitted to staff for review.", reply_markup=back_kb())
    await state.clear()

# --- SUPPORT SECTION ---
@dp.callback_query(F.data == "btn_support")
async def start_support(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        "Support Ticket\n\n"
        "Please describe your issue or question in detail.",
        reply_markup=back_kb()
    )
    await state.set_state(SupportFlow.message)

@dp.message(SupportFlow.message)
async def process_support(message: types.Message, state: FSMContext):
    ticket_id = str(uuid.uuid4())[:8]
    TICKETS[ticket_id] = message.from_user.id
    
    staff_msg = (
        "New Support Ticket\n\n"
        f"User: {message.from_user.full_name}\n"
        f"ID: {message.from_user.id}\n\n"
        f"Message:\n{message.text}"
    )
    await bot.send_message(STAFF_GROUP_ID, staff_msg, reply_markup=staff_action_kb(ticket_id))
    
    await message.answer("Your ticket has been sent. Staff will reply shortly.", reply_markup=back_kb())
    await state.clear()

# --- PUNISHMENT SECTION ---
@dp.callback_query(F.data == "btn_punishment")
async def start_punishment(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        "Punishment Appeal\n\n"
        "Step 1: Enter your Minecraft Username.",
        reply_markup=back_kb()
    )
    await state.set_state(PunishmentFlow.username)

@dp.message(PunishmentFlow.username)
async def pun_step1(message: types.Message, state: FSMContext):
    await state.update_data(username=message.text)
    await message.answer("Step 2: Enter your Punishment ID.")
    await state.set_state(PunishmentFlow.punish_id)

@dp.message(PunishmentFlow.punish_id)
async def pun_step2(message: types.Message, state: FSMContext):
    await state.update_data(punish_id=message.text)
    await message.answer("Step 3: Enter the Reason for punishment.")
    await state.set_state(PunishmentFlow.reason)

@dp.message(PunishmentFlow.reason)
async def pun_step3(message: types.Message, state: FSMContext):
    await state.update_data(reason=message.text)
    await message.answer("Step 4: Enter your Appeal Message (Explain why we should unban you).")
    await state.set_state(PunishmentFlow.message)

@dp.message(PunishmentFlow.message)
async def pun_final(message: types.Message, state: FSMContext):
    data = await state.get_data()
    ticket_id = str(uuid.uuid4())[:8]
    TICKETS[ticket_id] = message.from_user.id
    
    staff_msg = (
        "New Punishment Appeal\n\n"
        f"User: {message.from_user.full_name}\n"
        f"MC Username: {data['username']}\n"
        f"Punishment ID: {data['punish_id']}\n"
        f"Reason: {data['reason']}\n\n"
        f"Appeal:\n{message.text}"
    )
    await bot.send_message(STAFF_GROUP_ID, staff_msg, reply_markup=staff_action_kb(ticket_id))
    
    await message.answer("Your appeal has been sent. You will be notified of the result.", reply_markup=back_kb())
    await state.clear()

# --- SHOP SECTION ---
@dp.callback_query(F.data == "btn_shop")
async def show_shop(call: types.CallbackQuery):
    await call.message.edit_text(
        "Server Shop\n\n"
        "Support the server and get cool ranks/items here:\n"
        "https://store.thefellomen.com",
        reply_markup=back_kb()
    )

# --- STAFF ACTIONS (INTERACTIVE) ---
@dp.callback_query(F.data.startswith("staff_accept_"))
async def staff_accept(call: types.CallbackQuery):
    ticket_id = call.data.split("_")[2]
    user_id = TICKETS.get(ticket_id)
    if user_id:
        await bot.send_message(user_id, "Notification: Your request has been accepted by the staff.")
        await call.answer("Accepted and user notified.")
    else:
        await call.answer("Error: Ticket session expired.")

@dp.callback_query(F.data.startswith("staff_deny_"))
async def staff_deny(call: types.CallbackQuery):
    ticket_id = call.data.split("_")[2]
    user_id = TICKETS.get(ticket_id)
    if user_id:
        await bot.send_message(user_id, "Notification: Your request has been denied.")
        await call.answer("Denied and user notified.")
    else:
        await call.answer("Error: Ticket session expired.")

@dp.callback_query(F.data.startswith("staff_reply_"))
async def staff_reply_init(call: types.CallbackQuery, state: FSMContext):
    ticket_id = call.data.split("_")[2]
    await state.update_data(current_ticket=ticket_id)
    await state.set_state(StaffReplyFlow.message)
    await call.message.reply("Type your reply message for the user:")

@dp.message(StaffReplyFlow.message)
async def staff_reply_send(message: types.Message, state: FSMContext):
    data = await state.get_data()
    ticket_id = data.get("current_ticket")
    user_id = TICKETS.get(ticket_id)
    
    if user_id:
        reply_text = f"Staff Response:\n\n{message.text}"
        await bot.send_message(user_id, reply_text)
        await message.answer("Reply sent to user.")
    else:
        await message.answer("Error: Could not find user for this ticket.")
    
    await state.clear()

# --- MAIN ---
async def main():
    # Set bot commands menu in Telegram
    await bot.set_my_commands([
        BotCommand(command="start", description="Restart the bot")
    ])
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Start Web Thread
    threading.Thread(target=run_web).start()
    # Start Bot
    asyncio.run(main())
