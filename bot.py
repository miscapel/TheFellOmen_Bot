import os
import asyncio
import threading
from flask import Flask
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# --------------------- CONFIG ---------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
STAFF_GROUP_ID = int(os.getenv("STAFF_GROUP_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --------------------- KEEP ALIVE ---------------------
app = Flask(__name__)
@app.route("/")
def home(): return "Bot is Online"
def run_web(): app.run(host="0.0.0.0", port=10000)

# --------------------- STATES ---------------------
class UserFlow(StatesGroup):
    waiting_for_input = State()

class StaffReplyFlow(StatesGroup):
    waiting_for_reply = State()

# --------------------- KEYBOARDS ---------------------
def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📜 Whitelist Request")],
            [KeyboardButton(text="💎 Server Shop")],
            [KeyboardButton(text="🆘 Support Ticket")],
            [KeyboardButton(text="⚖️ Punishment Appeal")]
        ],
        resize_keyboard=True,
        input_field_placeholder="لطفاً یک گزینه انتخاب کنید..."
    )

def staff_reply_button(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Reply to User", callback_data=f"reply_{user_id}")]
    ])

# --------------------- HANDLERS ---------------------

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "✨ **به پنل اختصاصی TheFellOmen خوش اومدی!**\n\n"
        "از منوی پایین، بخش مورد نظرت رو انتخاب کن:",
        reply_markup=main_menu()
    )

# مدیریت انتخاب‌ها
@dp.message(F.text.in_(["📜 Whitelist Request", "💎 Server Shop", "🆘 Support Ticket", "⚖️ Punishment Appeal"]))
async def menu_select(message: types.Message, state: FSMContext):
    await state.update_data(section=message.text)
    await state.set_state(UserFlow.waiting_for_input)
    
    await message.answer(
        f"✅ **{message.text}** انتخاب شد.\n"
        "حالا پیام، اسکرین‌شات یا ویدیوی خودت رو بفرست:",
        reply_markup=ReplyKeyboardRemove() # کیبورد رو موقتا برمی‌داریم تا تمرکز کنن
    )

# دریافت محتوا (متن/عکس/ویدیو)
@dp.message(UserFlow.waiting_for_input)
async def handle_input(message: types.Message, state: FSMContext):
    data = await state.get_data()
    section = data.get("section")
    
    # ساخت متن کپشن برای گروه استاف
    caption = f"📩 **New Request: {section}**\n👤 User: {message.from_user.full_name}\n🆔 ID: `{message.from_user.id}`\n\n"
    if message.text: caption += f"💬: {message.text}"
    
    # ارسال به گروه استاف
    if message.photo:
        await bot.send_photo(STAFF_GROUP_ID, message.photo[-1].file_id, caption=caption, reply_markup=staff_reply_button(message.from_user.id))
    elif message.video:
        await bot.send_video(STAFF_GROUP_ID, message.video.file_id, caption=caption, reply_markup=staff_reply_button(message.from_user.id))
    else:
        await bot.send_message(STAFF_GROUP_ID, caption, reply_markup=staff_reply_button(message.from_user.id))

    await message.answer("✅ پیام شما ارسال شد. ممنون از صبر شما!", reply_markup=main_menu())
    await state.clear()

# --------------------- STAFF REPLY ---------------------
@dp.callback_query(F.data.startswith("reply_"))
async def prepare_reply(call: types.CallbackQuery, state: FSMContext):
    user_id = call.data.split("_")[1]
    await state.update_data(target_user=user_id)
    await state.set_state(StaffReplyFlow.waiting_for_reply)
    await call.message.answer(f"✍️ پیام پاسخ برای کاربر `{user_id}` رو بفرست:")

@dp.message(StaffReplyFlow.waiting_for_reply)
async def send_reply(message: types.Message, state: FSMContext):
    data = await state.get_data()
    target_user = data.get("target_user")
    
    header = "📩 **پاسخ مدیریت:**\n\n"
    
    try:
        if message.text: await bot.send_message(target_user, f"{header}{message.text}")
        elif message.photo: await bot.send_photo(target_user, message.photo[-1].file_id, caption=header + (message.caption or ""))
        elif message.video: await bot.send_video(target_user, message.video.file_id, caption=header + (message.caption or ""))
        
        await message.answer("✅ با موفقیت برای کاربر ارسال شد.")
    except Exception as e:
        await message.answer(f"❌ ارسال نشد! ممکنه کاربر ربات رو بلاک کرده باشه.\nError: {e}")
        
    await state.clear()

# --------------------- MAIN ---------------------
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    asyncio.run(main())
