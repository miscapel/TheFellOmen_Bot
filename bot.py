import logging
import os
import threading
import asyncio
from typing import Literal

# --- کتابخانه‌های مورد نیاز ---
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.markdown import hbold, hcode, hlink # برای فرمت‌دهی پیام‌ها

# برای اجرای محلی (اگر از فایل .env استفاده می‌کنید)
from dotenv import load_dotenv

# Flask برای زنده نگه داشتن برنامه در Render
from flask import Flask

# --- تنظیمات اولیه و لاگ‌گیری ---
# تنظیم سطح لاگ‌گیری روی INFO برای مشاهده پیام‌های مهم
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# این پیام چاپ می‌شود تا Render نشان دهد برنامه در حال شروع است
print("--- ربات در حال شروع است ---")

# بارگذاری متغیرهای محیطی از فایل .env (فقط برای اجرای محلی، در Render این کار لازم نیست)
load_dotenv()

# --- تنظیمات ربات ---
# خواندن مقادیر از متغیرهای محیطی که در Render تنظیم می‌شوند
BOT_TOKEN = os.getenv("BOT_TOKEN")
STAFF_GROUP_ID = os.getenv("STAFF_GROUP_ID")
PORT = os.getenv("PORT", "10000") # مقدار پیش‌فرض 10000

# --- بررسی تنظیمات ضروری ---
# اگر توکن ربات تنظیم نشده باشد، برنامه با خطا خارج می‌شود
if not BOT_TOKEN:
    logging.error("خطا: BOT_TOKEN تنظیم نشده است. لطفاً در تنظیمات Render، متغیر محیطی BOT_TOKEN را با توکن ربات خود تنظیم کنید.")
    exit(1)
# اگر شناسه گروه تنظیم نشده باشد، برنامه با خطا خارج می‌شود
if not STAFF_GROUP_ID:
    logging.error("خطا: STAFF_GROUP_ID تنظیم نشده است. لطفاً در تنظیمات Render، متغیر محیطی STAFF_GROUP_ID را با شناسه گروه خود تنظیم کنید.")
    exit(1)
# تبدیل STAFF_GROUP_ID به عدد صحیح (integer)
try:
    STAFF_GROUP_ID = int(STAFF_GROUP_ID)
except ValueError:
    logging.error(f"خطا: STAFF_GROUP_ID مقدار معتبر عددی ندارد: '{STAFF_GROUP_ID}'. لطفاً یک عدد صحیح وارد کنید.")
    exit(1)
# تبدیل PORT به عدد صحیح (integer)
try:
    PORT = int(PORT)
except ValueError:
    logging.error(f"خطا: PORT مقدار معتبر عددی ندارد: '{PORT}'. لطفاً یک عدد صحیح وارد کنید.")
    exit(1)

# نمایش تنظیمات خوانده شده (توکن نمایش داده نمی‌شود تا امن بماند)
logging.info(f"تنظیمات محیطی خوانده شد: BOT_TOKEN=***, STAFF_GROUP_ID={STAFF_GROUP_ID}, PORT={PORT}")

# --- راه‌اندازی ربات و دیسپچر با MemoryStorage ---
# MemoryStorage فقط برای تست مناسب است. برای استفاده در محیط Production،
# بهتر است از پایگاه داده واقعی مانند Redis یا PostgreSQL استفاده کنید.
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# --- تعریف State ها (برای مدیریت جریان کار کاربر - FSM) ---
# این کلاس‌ها وضعیت‌های مختلفی را که کاربر در طول یک فرآیند طی می‌کند، تعریف می‌کنند.
class UserWorkflow(StatesGroup):
    selecting_reason = State()           # انتخاب دلیل برای Whitelist
    awaiting_reason_confirmation = State() # تایید نهایی Whitelist
    awaiting_shop_choice = State()       # انتخاب بین فروشگاه رنک یا کوین
    awaiting_rank_purchase = State()     # انتخاب رنک خاص برای خرید
    awaiting_coin_purchase = State()     # انتخاب بسته کوین برای خرید
    awaiting_custom_coin_amount = State()# وارد کردن مقدار دلخواه کوین

# --- داده‌های نمونه (در دنیای واقعی این اطلاعات از دیتابیس خوانده می‌شوند) ---
# دلایل برای Whitelist و هزینه هر کدام
REASONS = {
    "reason_1": {"name": "مشکل ورود", "price": 10000},
    "reason_2": {"name": "خطای پرداخت", "price": 15000},
    "reason_3": {"name": "درخواست پشتیبانی", "price": 20000},
}

# آیتم‌های فروشگاه رنک و قیمت آن‌ها
RANK_SHOP_ITEMS = {
    "vip": {"name": "Vip", "price": 49000},
    "elite": {"name": "Elite", "price": 100000},
    "thefellomen": {"name": "TheFellOmen", "price": 190000},
    "sponsor": {"name": "Sponsor", "price": 250000},
    "lover": {"name": "Lover", "price": 400000},
}

# آیتم‌های فروشگاه کوین و قیمت آن‌ها
COIN_SHOP_ITEMS = {
    "50_coin": {"name": "50 Coin", "price": 15000},
    "100_coin": {"name": "100 Coins", "price": 30000},
    "150_coin": {"name": "150 Coins", "price": 55000},
    "200_coin": {"name": "200 Coins", "price": 80000},
    "250_coin": {"name": "250 Coins", "price": 150000},
}
# قیمت تقریبی هر کوین برای محاسبه مقادیر دلخواه
PRICE_PER_COIN = 300

# --- Callback Data Factories ---
# این کلاس‌ها برای ساخت و تجزیه داده‌های callback دکمه‌های Inline Keyboard استفاده می‌شوند.
class WhitelistCallback(CallbackData, prefix="whitelist"):
    action: Literal["select_reason", "confirm_reason", "cancel_reason"] # نوع اکشن دکمه
    reason_id: str | None = None # شناسه دلیل انتخابی

class ShopCallback(CallbackData, prefix="shop"):
    action: Literal["open_rank_shop", "open_coin_shop", "buy_rank", "buy_coin", "custom_coin", "open_shop"] # نوع اکشن دکمه
    item_id: str | None = None # شناسه آیتم انتخابی
    amount: int | None = None # مقدار (برای کوین‌های دلخواه)

# --- تصاویر نمونه (مسیرها را با فایل‌های خودتان جایگزین کنید) ---
# این دیکشنری مسیر فایل‌های عکس را ذخیره می‌کند.
# اطمینان حاصل کنید که پوشه 'photos' در کنار فایل bot.py وجود دارد و فایل‌های عکس داخل آن قرار دارند.
PHOTO_PATHS = {
    "whitelist_success": "photos/whitelist_success.jpg",
    "rank_purchase_success": "photos/rank_purchase_success.jpg",
    "coin_purchase_success": "photos/coin_purchase_success.jpg",
}

def get_photo_path(key: str) -> str | None:
    """
    تابع کمکی برای گرفتن مسیر عکس از دیکشنری PHOTO_PATHS.
    اگر عکس وجود نداشته باشد یا مسیر اشتباه باشد، None برمی‌گرداند.
    """
    path = PHOTO_PATHS.get(key)
    # بررسی می‌کند که آیا مسیر وجود دارد و فایل در آن مسیر موجود است
    if path and os.path.exists(path):
        return path
    logging.warning(f"فایل عکس برای '{key}' در مسیر '{path}' یافت نشد.")
    return None

# --- تابع کمکی برای ارسال پیام همراه با عکس ---
async def send_message_with_photo(
    message: types.Message | types.CallbackQuery, # پیام اصلی (یا از کاربر یا از callback query)
    text: str, # متن پیام
    photo_key: str, # کلید مربوط به عکس در دیکشنری PHOTO_PATHS
    reply_markup: types.InlineKeyboardMarkup | None = None, # دکمه‌های Inline Keyboard
    parse_mode: str = "Markdown" # حالت پارس کردن متن (Markdown یا HTML)
):
    """
    این تابع پیام را همراه با عکس مربوطه ارسال می‌کند.
    اگر عکس پیدا نشود، فقط متن پیام را ارسال می‌کند.
    """
    photo_path = get_photo_path(photo_key) # گرفتن مسیر عکس

    # اگر پیام از نوع CallbackQuery باشد، به شیء Message اصلی آن دسترسی پیدا می‌کنیم
    if isinstance(message, types.CallbackQuery):
        message_obj = message.message
    else:
        message_obj = message

    # اگر مسیر عکس معتبر بود
    if photo_path:
        try:
            # فایل عکس را به صورت باینری باز می‌کنیم
            with open(photo_path, 'rb') as photo_file:
                # ارسال عکس به همراه متن (caption)
                await message_obj.answer_photo(photo=photo_file, caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
            return True # موفقیت‌آمیز بود
        except Exception as e:
            # در صورت بروز خطا هنگام ارسال عکس (مثلاً حجم زیاد یا مشکل در فایل)
            logging.error(f"خطا در ارسال عکس {photo_key}: {e}")
            # پیام متنی را به جای عکس ارسال می‌کنیم
            await message_obj.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
            return False # ناموفق بود
    else:
        # اگر عکسی وجود نداشت، فقط متن را ارسال می‌کنیم
        await message_obj.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
        return False

# --- پردازش دستور /start ---
@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    """
    این تابع به دستور /start پاسخ می‌دهد و پیام خوش‌آمدگویی را نمایش می‌دهد.
    """
    user_name = message.from_user.full_name # نام کامل کاربر
    user_id = message.from_user.id # شناسه کاربری
    logging.info(f"دستور /start از کاربر {user_name} (ID: {user_id}) دریافت شد.")

    # ارسال پیام خوش‌آمدگویی با فرمت Markdown
    await message.reply(f"سلام {hbold(user_name)}!\nبه ربات TheFellOmen خوش آمدید! برای مشاهده امکانات، از دستور /help استفاده کنید.")

# --- پردازش دستور /help ---
@dp.message(Command("help"))
async def send_help(message: types.Message):
    """
    این تابع به دستور /help پاسخ می‌دهد و راهنمای ربات را نمایش می‌دهد.
    """
    user_id = message.from_user.id
    logging.info(f"دستور /help از کاربر {user_id} دریافت شد.")

    # متن راهنما با فرمت Markdown
    help_text = (
        "🤖 *راهنمای ربات TheFellOmen*\n\n"
        f"{hbold('`/whitelist`')}: برای خرید دسترسی Whitelist یا رفع مشکلات خاص.\n"
        f"{hbold('`/shop`')}: برای مشاهده فروشگاه رنک و کوین.\n"
        f"{hbold('`/my_profile`')}: نمایش اطلاعات پروفایل شما (در آینده).\n\n"
        "برای هرگونه سوال یا مشکل، لطفاً با ادمین در ارتباط باشید."
    )
    await message.reply(help_text, parse_mode="Markdown")

# --- پردازش دستور /whitelist ---
@dp.message(Command("whitelist"))
async def start_whitelist_process(message: types.Message, state: FSMContext):
    """
    شروع فرآیند Whitelist با انتخاب دلیل.
    """
    user_id = message.from_user.id
    logging.info(f"دستور /whitelist از کاربر {user_id} دریافت شد.")

    # تنظیم حالت کاربر به 'selecting_reason' برای شروع فرآیند
    await state.set_state(UserWorkflow.selecting_reason)

    # ساخت دکمه‌های Inline Keyboard برای انتخاب دلیل
    builder = InlineKeyboardBuilder()
    for reason_id, reason_data in REASONS.items():
        builder.add(types.InlineKeyboardButton(
            text=f"{reason_data['name']} ({reason_data['price']:,} T)", # نمایش نام دلیل و قیمت
            callback_data=WhitelistCallback(action="select_reason", reason_id=reason_id).pack() # ساخت callback data
        ))
    builder.adjust(1) # هر دکمه در یک سطر

    # ارسال پیام به کاربر برای انتخاب دلیل
    await message.reply("لطفاً یکی از دلایل زیر را برای Whitelist انتخاب کنید:", reply_markup=builder.as_markup())

# --- پردازش کلیک روی دکمه انتخاب دلیل Whitelist ---
@dp.callback_query(WhitelistCallback.filter(F=lambda F, callback_data: callback_data.action == "select_reason"))
async def process_reason_selection(callback_query: types.CallbackQuery, callback_data: WhitelistCallback, state: FSMContext):
    """
    پردازش انتخاب دلیل توسط کاربر و رفتن به مرحله تایید.
    """
    reason_id = callback_data.reason_id # دریافت شناسه دلیل از callback data
    user_id = callback_query.from_user.id

    # بررسی معتبر بودن دلیل انتخاب شده
    if not reason_id or reason_id not in REASONS:
        await callback_query.answer("دلیل نامعتبر است.", show_alert=True) # نمایش پیام خطا به کاربر
        return

    reason_data = REASONS[reason_id]
    reason_name = reason_data["name"]
    reason_price = reason_data["price"]

    # ذخیره دلیل انتخاب شده در وضعیت کاربر (state)
    await state.update_data(selected_reason_id=reason_id)
    # تغییر حالت کاربر به 'awaiting_reason_confirmation'
    await state.set_state(UserWorkflow.awaiting_reason_confirmation)

    # ساخت دکمه‌های تایید و لغو
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="✅ تایید نهایی",
        callback_data=WhitelistCallback(action="confirm_reason", reason_id=reason_id).pack() # ارسال دلیل انتخابی
    ))
    builder.add(types.InlineKeyboardButton(
        text="❌ لغو",
        callback_data=WhitelistCallback(action="cancel_reason").pack() # دکمه لغو
    ))
    builder.adjust(2) # دو دکمه در یک سطر

    # ساخت متن پیام تایید
    text = (
        f"شما '{hbold(reason_name)}' را انتخاب کردید.\n"
        f"هزینه: {hbold(f'{reason_price:,} تومان')}.\n\n"
        "آیا برای تایید نهایی و انتقال به درگاه پرداخت آماده‌اید؟"
    )
    # ویرایش پیام قبلی برای نمایش متن تایید و دکمه‌ها
    await callback_query.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback_query.answer("دلیل انتخاب شد.") # بستن نشانگر "Loading" روی دکمه

# --- پردازش تایید نهایی خرید Whitelist ---
@dp.callback_query(WhitelistCallback.filter(F=lambda F, callback_data: callback_data.action == "confirm_reason"))
async def confirm_reason_purchase(callback_query: types.CallbackQuery, callback_data: WhitelistCallback, state: FSMContext):
    """
    تایید نهایی خرید Whitelist و شبیه‌سازی انتقال به درگاه پرداخت.
    """
    reason_id = callback_data.reason_id
    user_id = callback_query.from_user.id

    # بررسی مجدد معتبر بودن دلیل
    if not reason_id or reason_id not in REASONS:
        await callback_query.answer("خطایی رخ داد، لطفاً دوباره امتحان کنید.", show_alert=True)
        await state.clear() # پاک کردن وضعیت کاربر
        return

    reason_name = REASONS[reason_id]["name"]
    reason_price = REASONS[reason_id]["price"]

    logging.info(f"کاربر {user_id}، '{reason_name}' را با قیمت {reason_price} تایید کرد.")

    # =====================================================
    # === بخش پیاده‌سازی پرداخت ===
    # در این قسمت باید کاربر را به درگاه پرداخت هدایت کنید.
    # مثال:
    # payment_link = await create_payment_link(user_id, reason_price, f"Whitelist - {reason_name}")
    # if payment_link:
    #     text = f"پرداخت شما برای '{reason_name}' با موفقیت انجام شد! لطفاً روی لینک زیر کلیک کنید:\n{hlink('پرداخت', payment_link)}"
    #     await send_message_with_photo(callback_query, text, "whitelist_success", parse_mode="Markdown")
    # else:
    #     text = "خطایی در ایجاد لینک پرداخت رخ داد. لطفاً بعداً دوباره امتحان کنید."
    #     await callback_query.answer(text, show_alert=True)
    #     await state.clear()
    #     return
    # =====================================================

    # --- شبیه‌سازی موفقیت پرداخت (برای تست) ---
    text = f"پرداخت شما برای '{reason_name}' با موفقیت انجام شد!\n\n"
    text += "اگر نیاز به کیت خاصی دارید، لطفاً با ادمین تماس بگیرید."
    # ارسال پیام موفقیت‌آمیز همراه با عکس
    await send_message_with_photo(callback_query, text, "whitelist_success", parse_mode="Markdown")
    await callback_query.answer("پرداخت موفق!") # نمایش پیام کوتاه برای کاربر
    await state.clear() # پاک کردن وضعیت کاربر پس از اتمام فرآیند

# --- پردازش دکمه لغو Whitelist ---
@dp.callback_query(WhitelistCallback.filter(F=lambda F, callback_data: callback_data.action == "cancel_reason"))
async def cancel_reason_purchase(callback_query: types.CallbackQuery, state: FSMContext):
    """
    لغو فرآیند Whitelist توسط کاربر.
    """
    user_id = callback_query.from_user.id
    logging.info(f"فرآیند Whitelist توسط کاربر {user_id} لغو شد.")
    # ویرایش پیام برای نمایش پیام لغو
    await callback_query.message.edit_text("عملیات Whitelist لغو شد.")
    await callback_query.answer("عملیات لغو شد.")
    await state.clear() # پاک کردن وضعیت کاربر

# --- پردازش دستور /shop ---
@dp.message(Command("shop"))
async def open_main_shop(message: types.Message, state: FSMContext):
    """
    نمایش منوی اصلی فروشگاه.
    """
    user_id = message.from_user.id
    logging.info(f"دستور /shop از کاربر {user_id} دریافت شد.")
    # تنظیم حالت کاربر به 'awaiting_shop_choice'
    await state.set_state(UserWorkflow.awaiting_shop_choice)

    # ساخت دکمه‌های منوی اصلی فروشگاه (رنک و کوین)
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="🛒 فروشگاه رنک",
        callback_data=ShopCallback(action="open_rank_shop").pack()
    ))
    builder.add(types.InlineKeyboardButton(
        text="💰 فروشگاه کوین",
        callback_data=ShopCallback(action="open_coin_shop").pack()
    ))
    builder.adjust(1)

    # ارسال پیام منوی اصلی
    await message.reply("به فروشگاه خوش آمدید! کدام بخش را می‌خواهید مشاهده کنید؟", reply_markup=builder.as_markup())

# --- نمایش فروشگاه رنک ---
@dp.callback_query(ShopCallback.filter(F=lambda F, callback_data: callback_data.action == "open_rank_shop"))
async def show_rank_shop(callback_query: types.CallbackQuery, state: FSMContext):
    """
    نمایش آیتم‌های فروشگاه رنک.
    """
    user_id = callback_query.from_user.id
    logging.info(f"کاربر {user_id} فروشگاه رنک را باز کرد.")
    # تنظیم حالت کاربر به 'awaiting_rank_purchase'
    await state.set_state(UserWorkflow.awaiting_rank_purchase)

    # ساخت متن نمایش فروشگاه رنک
    message_text = f"🌟 {hbold('Rank Shop')} 🌟\n\n"
    message_text += "برای خرید کیت رنک، رنک مورد نظر خود را انتخاب کنید:\n\n"
    # لیست کردن آیتم‌های رنک
    for item_id, item_data in RANK_SHOP_ITEMS.items():
        message_text += f"🔹 {hbold(item_data['name'])} » {hcode(f'{item_data['price']:,} تومان')}\n"

    message_text += "\nاگر فقط نیاز به کیت رنک دارید، رنک مورد نظر و کیت مورد نظر خود را بنویسید (مثلاً: 'Vip - کیت')."

    # ساخت دکمه‌های خرید برای هر رنک
    builder = InlineKeyboardBuilder()
    for item_id, item_data in RANK_SHOP_ITEMS.items():
        builder.add(types.InlineKeyboardButton(
            text=f"{item_data['name']} ({item_data['price']:,} T)",
            callback_data=ShopCallback(action="buy_rank", item_id=item_id).pack()
        ))
    builder.adjust(1)

    # دکمه بازگشت به منوی اصلی
    builder.add(types.InlineKeyboardButton(
        text="بازگشت به منوی اصلی",
        callback_data=ShopCallback(action="open_shop").pack()
    ))

    # ویرایش پیام برای نمایش فروشگاه رنک
    await callback_query.message.edit_text(message_text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback_query.answer("فروشگاه رنک")

# --- نمایش فروشگاه کوین ---
@dp.callback_query(ShopCallback.filter(F=lambda F, callback_data: callback_data.action == "open_coin_shop"))
async def show_coin_shop(callback_query: types.CallbackQuery, state: FSMContext):
    """
    نمایش آیتم‌های فروشگاه کوین.
    """
    user_id = callback_query.from_user.id
    logging.info(f"کاربر {user_id} فروشگاه کوین را باز کرد.")
    # تنظیم حالت کاربر به 'awaiting_coin_purchase'
    await state.set_state(UserWorkflow.awaiting_coin_purchase)

    # ساخت متن نمایش فروشگاه کوین
    message_text = f"💰 {hbold('Coin Shop')} 💰\n\n"
    message_text += "مقدار کوین مورد نظر خود را انتخاب کنید:\n\n"
    # لیست کردن بسته‌های کوین
    for item_id, item_data in COIN_SHOP_ITEMS.items():
        message_text += f"🔹 {hbold(item_data['name'])} » {hcode(f'{item_data['price']:,} تومان')}\n"

    message_text += f"\nاگر مقدار کوین مورد نظر شما بیشتر از این‌هاست، مقدار دلخواه خود را در چت بنویسید (هر کوین تقریباً {PRICE_PER_COIN:,} تومان)."

    # ساخت دکمه‌های خرید برای بسته‌های کوین
    builder = InlineKeyboardBuilder()
    for item_id, item_data in COIN_SHOP_ITEMS.items():
        builder.add(types.InlineKeyboardButton(
            text=f"{item_data['name']} ({item_data['price']:,} T)",
            callback_data=ShopCallback(action="buy_coin", item_id=item_id).pack()
        ))
    builder.adjust(1)

    # دکمه برای وارد کردن مقدار دلخواه کوین
    builder.add(types.InlineKeyboardButton(
        text="مقدار دلخواه",
        callback_data=ShopCallback(action="custom_coin").pack()
    ))
    # دکمه بازگشت به منوی اصلی
    builder.add(types.InlineKeyboardButton(
        text="بازگشت به منوی اصلی",
        callback_data=ShopCallback(action="open_shop").pack()
    ))

    # ویرایش پیام برای نمایش فروشگاه کوین
    await callback_query.message.edit_text(message_text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback_query.answer("فروشگاه کوین")

# --- پردازش خرید رنک از فروشگاه ---
@dp.callback_query(ShopCallback.filter(F=lambda F, callback_data: callback_data.action == "buy_rank"))
async def process_rank_purchase_callback(callback_query: types.CallbackQuery, callback_data: ShopCallback, state: FSMContext):
    """
    پردازش انتخاب رنک توسط کاربر و شبیه‌سازی خرید.
    """
    item_id = callback_data.item_id # شناسه رنک انتخابی
    user_id = callback_query.from_user.id

    # بررسی معتبر بودن آیتم
    if not item_id or item_id not in RANK_SHOP_ITEMS:
        await callback_query.answer("آیتم نامعتبر است.", show_alert=True)
        return

    item_data = RANK_SHOP_ITEMS[item_id]
    item_name = item_data["name"]
    item_price = item_data["price"]

    logging.info(f"کاربر {user_id} قصد خرید رنک '{item_name}' را دارد.")

    # =====================================================
    # === بخش پیاده‌سازی پرداخت برای رنک ===
    # مشابه بخش Whitelist، باید کاربر را به درگاه پرداخت هدایت کنید.
    # مثال:
    # payment_link = await create_payment_link(user_id, item_price, f"Rank Purchase - {item_name}")
    # if payment_link:
    #     text = f"خرید رنک '{hbold(item_name)}' با موفقیت انجام شد!\n"
    #     text += f"هزینه: {hcode(f'{item_price:,} تومان')}.\n\n"
    #     text += f"لطفاً روی لینک زیر کلیک کنید تا پرداخت را نهایی کنید:\n{hlink('پرداخت', payment_link)}"
    #     await send_message_with_photo(callback_query, text, "rank_purchase_success", parse_mode="Markdown")
    # else:
    #     await callback_query.answer("خطایی در ایجاد لینک پرداخت رخ داد.")
    #     await state.clear()
    #     return
    # =====================================================

    # --- شبیه‌سازی موفقیت پرداخت (برای تست) ---
    confirmation_message = f"خرید رنک '{hbold(item_name)}' با موفقیت انجام شد!\n\n"
    confirmation_message += "اگر فقط نیاز به کیت رنک دارید، لطفاً با ادمین تماس بگیرید یا منتظر پیام باشید."

    # ارسال پیام موفقیت‌آمیز همراه با عکس
    await send_message_with_photo(callback_query, confirmation_message, "rank_purchase_success", parse_mode="Markdown")
    await callback_query.answer("خرید رنک موفق!")
    await state.clear() # پاک کردن وضعیت کاربر

# --- پردازش خرید کوین از فروشگاه ---
@dp.callback_query(ShopCallback.filter(F=lambda F, callback_data: callback_data.action == "buy_coin"))
async def process_coin_purchase_callback(callback_query: types.CallbackQuery, callback_data: ShopCallback, state: FSMContext):
    """
    پردازش انتخاب بسته کوین توسط کاربر و شبیه‌سازی خرید.
    """
    item_id = callback_data.item_id # شناسه بسته کوین انتخابی
    user_id = callback_query.from_user.id

    # بررسی معتبر بودن آیتم
    if not item_id or item_id not in COIN_SHOP_ITEMS:
        await callback_query.answer("بسته کوین نامعتبر است.", show_alert=True)
        return

    item_data = COIN_SHOP_ITEMS[item_id]
    item_name = item_data["name"]
    item_price = item_data["price"]

    # استخراج تعداد کوین از item_id (مثلاً '50' از '50_coin')
    try:
        coins_amount = int(item_id.split('_')[0])
    except ValueError:
        logging.error(f"فرمت item_id برای کوین نامعتبر است: {item_id}")
        await callback_query.answer("خطایی در پردازش بسته کوین رخ داد.", show_alert=True)
        await state.clear()
        return

    logging.info(f"کاربر {user_id} قصد خرید {item_name} ({coins_amount} کوین) را دارد.")

    # =====================================================
    # === بخش پیاده‌سازی پرداخت برای کوین ===
    # مشابه بخش Whitelist
    # مثال:
    # payment_link = await create_payment_link(user_id, item_price, f"Coin Purchase - {coins_amount} Coins")
    # if payment_link:
    #     text = f"خرید {hbold(item_name)} با موفقیت انجام شد!\n"
    #     text += f"هزینه: {hcode(f'{item_price:,} تومان')}.\n\n"
    #     text += f"لطفاً روی لینک زیر کلیک کنید تا پرداخت را نهایی کنید:\n{hlink('پرداخت', payment_link)}"
    #     await send_message_with_photo(callback_query, text, "coin_purchase_success", parse_mode="Markdown")
    # else:
    #     await callback_query.answer("خطایی در ایجاد لینک پرداخت رخ داد.")
    #     await state.clear()
    #     return
    # =====================================================

    # --- شبیه‌سازی موفقیت پرداخت (برای تست) ---
    confirmation_message = f"خرید {hbold(item_name)} با موفقیت انجام شد!\n"
    confirmation_message += f"{hbold(f'{coins_amount} کوین')} به حساب شما اضافه خواهد شد."

    # ارسال پیام موفقیت‌آمیز همراه با عکس
    await send_message_with_photo(callback_query, confirmation_message, "coin_purchase_success", parse_mode="Markdown")
    await callback_query.answer("خرید کوین موفق!")
    await state.clear() # پاک کردن وضعیت کاربر

# --- درخواست مقدار دلخواه کوین ---
@dp.callback_query(ShopCallback.filter(F=lambda F, callback_data: callback_data.action == "custom_coin"))
async def request_custom_coin_amount(callback_query: types.CallbackQuery, state: FSMContext):
    """
    کاربر درخواست وارد کردن مقدار دلخواه کوین را دارد.
    """
    user_id = callback_query.from_user.id
    logging.info(f"کاربر {user_id} درخواست مقدار دلخواه کوین را داد.")
    # تنظیم حالت کاربر به 'awaiting_custom_coin_amount'
    await state.set_state(UserWorkflow.awaiting_custom_coin_amount)

    message_text = "لطفاً مقدار کوین مورد نظر خود را به عدد وارد کنید.\n"
    message_text += f"(هر کوین تقریباً {PRICE_PER_COIN:,} تومان محاسبه می‌شود.)"

    # ساخت دکمه لغو و بازگشت به فروشگاه کوین
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="❌ لغو", callback_data=ShopCallback(action="open_coin_shop").pack()))
    await callback_query.message.edit_text(message_text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback_query.answer("وارد کردن مقدار دلخواه")

# --- پردازش مقدار دلخواه کوین وارد شده توسط کاربر ---
@dp.message(UserWorkflow.awaiting_custom_coin_amount)
async def process_custom_coin_amount(message: types.Message, state: FSMContext):
    """
    پردازش مقدار کوین دلخواه وارد شده و ارائه راهنمایی برای پرداخت.
    """
    user_id = message.from_user.id
    try:
        amount = int(message.text) # تبدیل متن ورودی به عدد
        # بررسی اینکه مقدار کوین مثبت باشد
        if amount <= 0:
            await message.reply("مقدار کوین باید بیشتر از صفر باشد.")
            return

        total_price = amount * PRICE_PER_COIN # محاسبه هزینه کل

        logging.info(f"کاربر {user_id} درخواست {amount} کوین با قیمت تخمینی {total_price} را داد.")

        # =====================================================
        # === بخش پیاده‌سازی پرداخت برای کوین دلخواه ===
        # در این حالت، به جای هدایت به درگاه، کاربر را به ادمین ارجاع می‌دهیم.
        # می‌توانید یک پیام به ادمین هم ارسال کنید:
        await bot.send_message(STAFF_GROUP_ID,
                               f"کاربر {user_id} ({message.from_user.full_name}) درخواست خرید {amount} کوین را دارد. هزینه تقریبی: {total_price:,} تومان.")

        # نمایش پیام نهایی به کاربر
        final_message = f"شما درخواست {hbold(f'{amount} کوین')} را دارید.\n"
        final_message += f"هزینه تقریبی: {hcode(f'{total_price:,} تومان')}.\n\n"
        final_message += "لطفاً برای نهایی کردن خرید و پرداخت، به ادمین پیام دهید تا راهنمایی لازم را دریافت کنید."
        await message.reply(final_message, parse_mode="Markdown")

        # مثال برای هدایت به درگاه (در صورت نیاز):
        # payment_link = await create_payment_link(user_id, total_price, f"Custom Coin Purchase - {amount} Coins")
        # if payment_link:
        #     text = f"شما درخواست {hbold(f'{amount} کوین')} را دارید.\n"
        #     text += f"هزینه تقریبی: {hcode(f'{total_price:,} تومان')}.\n\n"
        #     text += f"لطفاً روی لینک زیر کلیک کنید تا پرداخت را نهایی کنید:\n{hlink('پرداخت', payment_link)}"
        #     await send_message_with_photo(message, text, "coin_purchase_success", parse_mode="Markdown")
        # else:
        #     await message.reply("خطایی در ایجاد لینک پرداخت رخ داد. لطفاً بعداً دوباره امتحان کنید.")
        # =====================================================

    except ValueError:
        # اگر کاربر عدد وارد نکرد
        await message.reply("مقدار وارد شده معتبر نیست. لطفاً فقط عدد وارد کنید.")
    except Exception as e:
        # خطاهای احتمالی دیگر
        logging.error(f"خطا در پردازش کوین دلخواه: {e}")
        await message.reply("خطایی در پردازش درخواست شما رخ داد.")
    finally:
        await state.clear() # پاک کردن وضعیت کاربر پس از پردازش

# --- بازگشت به منوی اصلی فروشگاه ---
@dp.callback_query(ShopCallback.filter(F=lambda F, callback_data: callback_data.action == "open_shop"))
async def return_to_main_shop(callback_query: types.CallbackQuery, state: FSMContext):
    """
    بازگشت کاربر به منوی اصلی فروشگاه از بخش‌های دیگر.
    """
    user_id = callback_query.from_user.id
    logging.info(f"کاربر {user_id} به منوی اصلی فروشگاه بازگشت.")
    # تنظیم حالت کاربر به 'awaiting_shop_choice'
    await state.set_state(UserWorkflow.awaiting_shop_choice)

    # ساخت دکمه‌های منوی اصلی فروشگاه
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="🛒 فروشگاه رنک",
        callback_data=ShopCallback(action="open_rank_shop").pack()
    ))
    builder.add(types.InlineKeyboardButton(
        text="💰 فروشگاه کوین",
        callback_data=ShopCallback(action="open_coin_shop").pack()
    ))
    builder.adjust(1)

    # ویرایش پیام برای نمایش منوی اصلی
    await callback_query.message.edit_text("به فروشگاه خوش آمدید! کدام بخش را می‌خواهید مشاهده کنید؟", reply_markup=builder.as_markup())
    await callback_query.answer("منوی اصلی فروشگاه")

# --- بخش اجرای وب‌سرور Flask برای زنده نگه داشتن برنامه در Render ---
app = Flask(__name__)

@app.route("/")
def index():
    """
    این مسیر روت برای Render است تا سرویس را زنده نگه دارد.
    """
    print("درخواست به مسیر روت Render دریافت شد.")
    return "ربات TheFellOmen فعال است!"

def run_flask_server():
    """
    اجرای وب‌سرور Flask در یک ترد جداگانه.
    """
    try:
        # اجرای سرور روی هاست 0.0.0.0 و پورتی که از متغیر محیطی خوانده شده
        app.run(host="0.0.0.0", port=PORT, debug=False)
    except Exception as e:
        logging.error(f"خطا در اجرای وب‌سرور Flask: {e}")

# --- تابع اصلی برای اجرای ربات ---
async def main():
    """
    تابع اصلی که ربات Aiogram و وب‌سرور Flask را راه‌اندازی می‌کند.
    """
    logging.info("شروع اجرای تابع main...")

    # راه‌اندازی وب‌سرور Flask در یک ترد (Thread) جداگانه
    # این کار باعث می‌شود که ربات Ai
