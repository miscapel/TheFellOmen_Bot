import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder

TOKEN = "8975820451:AAEBZjhBGdFNCjnCcvld09oItdJYnkGCsGU"
ADMIN_ID = 123456789  # آیدی عددی خودت

bot = Bot(token=TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

# ذخیره وضعیت کاربران
user_state = {}

# ---------- Main Menu ----------
def main_menu():
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="📜 Whitelist", callback_data="whitelist"))
    kb.row(types.InlineKeyboardButton(text="🛒 Shop", callback_data="shop"))
    kb.row(types.InlineKeyboardButton(text="📞 Contact Staff", callback_data="contact"))
    kb.row(types.InlineKeyboardButton(text="🛠 Support", callback_data="support"))
    return kb.as_markup()

# ---------- Start ----------
@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "سلام! به ربات رسمی سرور **TheFellOmen** خوش آمدید 🎮\n\n"
        "لطفاً یکی از بخش‌های زیر را انتخاب کنید:",
        reply_markup=main_menu()
    )

# ---------- Buttons ----------
@dp.callback_query()
async def buttons(callback: types.CallbackQuery):

    if callback.data == "whitelist":
        user_state[callback.from_user.id] = "whitelist"
        await callback.message.edit_text(
            "📜 **Whitelist Request**\n\n"
            "برای ثبت درخواست، لطفاً فقط **IGN (نام کاربری ماینکرفت)** خود را ارسال کنید.",
            reply_markup=main_menu()
        )

    elif callback.data == "shop":
        user_state[callback.from_user.id] = "shop"
        await callback.message.edit_text(
            "🛒 **Server Shop**\n\n"
            "در فروشگاه سرور می‌توانید آیتم‌ها و رنک‌های ویژه خریداری کنید.\n"
            "برای مثال:\n"
            "• Rank ها\n"
            "• آیتم‌های خاص\n"
            "• امکانات ویژه سرور\n\n"
            "اگر سوالی درباره خرید دارید پیام ارسال کنید.",
            reply_markup=main_menu()
        )

    elif callback.data == "contact":
        user_state[callback.from_user.id] = "contact"
        await callback.message.edit_text(
            "📞 **Contact Staff**\n\n"
            "اگر نیاز دارید با تیم مدیریت صحبت کنید، پیام خود را ارسال کنید.",
            reply_markup=main_menu()
        )

    elif callback.data == "support":
        user_state[callback.from_user.id] = "support"
        await callback.message.edit_text(
            "🛠 **Support**\n\n"
            "مشکل خود را بنویسید و ارسال کنید.\n"
            "تیم پشتیبانی به زودی پاسخ می‌دهد.",
            reply_markup=main_menu()
        )

    await callback.answer()

# ---------- Ticket System ----------
@dp.message()
async def tickets(message: types.Message):

    # پیام کاربر → ارسال برای ادمین
    if message.from_user.id != ADMIN_ID:

        section = user_state.get(message.from_user.id, "unknown")

        await bot.send_message(
            ADMIN_ID,
            f"📩 New Ticket\n\n"
            f"Section: {section}\n"
            f"User: {message.from_user.full_name}\n"
            f"ID: {message.from_user.id}\n\n"
            f"Message:\n{message.text}"
        )

        await message.answer("✅ پیام شما ارسال شد. لطفاً منتظر پاسخ بمانید.")

    # پاسخ ادمین
    else:
        if message.reply_to_message:
            try:
                text = message.reply_to_message.text
                user_id = int(text.split("ID: ")[1].split("\n")[0])

                await bot.send_message(
                    user_id,
                    f"👨‍💻 پاسخ تیم سرور:\n\n{message.text}"
                )

                await message.answer("✅ پاسخ ارسال شد.")

            except:
                await message.answer("❌ خطا در ارسال پاسخ")

# ---------- Run Bot ----------
async def main():
    print("TheFellOmen_Bot running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
