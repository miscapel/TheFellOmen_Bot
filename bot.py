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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
print("--- ربات در حال شروع است ---")

# بارگذاری متغیرهای محیطی (فقط برای اجرای محلی)
load_dotenv()

# --- تنظیمات ربات ---
BOT_TOKEN = os.getenv("8975820451:AAEBZjhBGdFNCjnCcvld09oItdJYnkGCsGU")
STAFF_GROUP_ID = os.getenv("-1004332150226")
PORT = os.getenv("PORT", "10000") # مقدار پیش‌فرض 10000

# بررسی تنظیمات ضروری
if not BOT_TOKEN:
    logging.error("خطا: BOT_TOKEN تنظیم نشده است. لطفاً در تنظیمات Render آن را وارد کنید.")
    exit(1)
if not STAFF_GROUP_ID:
    logging.error("خطا: STAFF_GROUP_ID تنظیم نشده است. لطفاً در تنظیمات Render آن را وارد کنید.")
    exit(1)
try:
    STAFF_GROUP_ID = int(STAFF_GROUP_ID)
except ValueError:
    logging.error(f"خطا: STAFF_GROUP_ID مقدار معتبر عددی ندارد: {STAFF_GROUP_ID}")
    exit(1)
try:
    PORT = int(PORT)
except ValueError:
    logging.error(f"خطا: PORT مقدار معتبر عددی ندارد: {PORT}")
    exit(1)

logging.info(f"تنظیمات محیطی خوانده شد: BOT_TOKEN={BOT_TOKEN[:5]}..., STAFF_GROUP_ID={STAFF_GROUP_ID}, PORT={PORT}")

# --- راه‌اندازی ربات و دیسپچر با MemoryStorage ---
# MemoryStorage فقط برای تست مناسب است، برای پروداکشن از Redis یا پایگاه داده استفاده کنید.
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# --- تعریف State ها (برای مدیریت جریان کار کاربر - FSM) ---
class UserWorkflow(StatesGroup):
    selecting_reason = State()           # انتخاب دلیل برای Whitelist
    awaiting_reason_confirmation = State() # تایید نهایی Whitelist
    awaiting_shop_choice = State()       # انتخاب بین فروشگاه رنک یا کوین
    awaiting_rank_purchase = State()     # انتخاب رنک خاص
    awaiting_coin_purchase = State()     # انتخاب بسته کوین
    awaiting_custom_coin_amount = State()# وارد کردن مقدار دلخواه کوین

# --- داده‌های نمونه (در دنیای واقعی از دیتابیس خوانده می‌شوند) ---
REASONS = {
    "reason_1": {"name": "مشکل ورود", "price": 10000},
    "reason_2": {"name": "خطای پرداخت", "price": 15000},
    "reason_3": {"name": "درخواست پشتیبانی", "price": 20000},
}

RANK_SHOP_ITEMS = {
    "vip": {"name": "Vip", "price": 49000},
    "elite": {"name": "Elite", "price": 100000},
    "thefellomen": {"name": "TheFellOmen", "price": 190000},
    "sponsor": {"name": "Sponsor", "price": 250000},
    "lover": {"name": "Lover", "price": 400000},
}

COIN_SHOP_ITEMS = {
    "50_coin": {"name": "50 Coin", "price": 15000},
    "100_coin": {"name": "100 Coins", "price": 30000},
    "150_coin": {"name": "150 Coins", "price": 55000},
    "200_coin": {"name": "200 Coins", "price": 80000},
    "250_coin": {"name": "250 Coins", "price": 150000},
}
# قیمت تقریبی هر کوین برای مقادیر دلخواه
PRICE_PER_COIN = 300

# --- Callback Data Factories ---
class WhitelistCallback(CallbackData, prefix="whitelist"):
    action: Literal["select_reason", "confirm_reason", "cancel_reason"]
    reason_id: str | None = None

class ShopCallback(CallbackData, prefix="shop"):
    action: Literal["open_rank_shop", "open_coin_shop", "buy_rank", "buy_coin", "custom_coin", "open_shop"]
    item_id: str | None = None
    amount: int | None = None # برای کوین‌های دلخواه

# --- تصاویر نمونه (مسیرها را با فایل‌های خودتان جایگزین کنید) ---
# اطمینان حاصل کنید که پوشه 'photos' وجود دارد و فایل‌های عکس در آن قرار دارند.
PHOTO_PATHS = {
    "whitelist_success": "photos/whitelist_success.jpg",
    "rank_purchase_success": "photos/rank_purchase_success.jpg",
    "coin_purchase_success": "photos/coin_purchase_success.jpg",
}

def get_photo_path(key: str) -> str | None:
    """تابع کمکی برای گرفتن مسیر عکس یا None اگر وجود نداشته باشد."""
    path = PHOTO_PATHS.get(key)
    if path and os.path.exists(path):
        return path
    logging.warning(f"فایل عکس برای '{key}' در مسیر '{path}' یافت نشد.")
    return None

# --- توابع کمکی برای ارسال پیام با عکس ---
async def send_message_with_photo(
    message: types.Message | types.CallbackQuery,
    text: str,
    photo_key: str,
    reply_markup: types.InlineKeyboardMarkup | None = None,
    parse_mode: str = "Markdown"
):
    """
    ارسال پیام همراه با عکس، در صورت وجود عکس.
    اگر message یک CallbackQuery باشد، از edit_text یا reply_photo استفاده می‌کند.
    """
    photo_path = get_photo_path(photo_key)
    if isinstance(message, types.CallbackQuery):
        message = message.message # دسترسی به Message object

    if photo_path:
        try:
            with open(photo_path, 'rb') as photo_file:
                if message.message_id: # اگر از CallbackQuery آمده باشیم
                    await message.answer_photo(photo=photo_file, caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
                else:
                    await message.answer_photo(photo=photo_file, caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
            return True
        except Exception as e:
            logging.error(f"خطا در ارسال عکس {photo_key}: {e}")
            # اگر ارسال عکس با خطا مواجه شد، پیام متنی را ارسال می‌کنیم
            if message.message_id:
                await message.message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
            else:
                await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
            return False
    else:
        # اگر عکسی وجود نداشت، فقط متن را ارسال می‌کنیم
        if message.message_id:
            await message.message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
        return False

# --- پردازش دستور /start ---
@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    """
    پیام خوش‌آمدگویی به کاربر.
    """
    user_name = message.from_user.full_name
    user_id = message.from_user.id
    logging.info(f"دستور /start از کاربر {user_name} (ID: {user_id}) دریافت شد.")
    await message.reply(f"سلام {hbold(user_name)}!\nبه ربات TheFellOmen خوش آمدید! برای مشاهده امکانات، از دستور /help استفاده کنید.")

# --- پردازش دستور /help ---
@dp.message(Command("help"))
async def send_help(message: types.Message):
    """
    نمایش راهنمای ربات.
    """
    user_id = message.from_user.id
    logging.info(f"دستور /help از کاربر {user_id} دریافت شد.")
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
    شروع فرآیند انتخاب دلیل برای Whitelist.
    """
    user_id = message.from_user.id
    logging.info(f"دستور /whitelist از کاربر {user_id} دریافت شد.")
    await state.set_state(UserWorkflow.selecting_reason)

    builder = InlineKeyboardBuilder()
    for reason_id, reason_data in REASONS.items():
        builder.add(types.InlineKeyboardButton(
            text=f"{reason_data['name']} ({reason_data['price']:,} T)",
            callback_data=WhitelistCallback(action="select_reason", reason_id=reason_id).pack()
        ))
    builder.adjust(1) # هر دکمه در یک سطر

    await message.reply("لطفاً یکی از دلایل زیر را برای Whitelist انتخاب کنید:", reply_markup=builder.as_markup())

@dp.callback_query(WhitelistCallback.filter(F=lambda F, callback_data: callback_data.action == "select_reason"))
async def process_reason_selection(callback_query: types.CallbackQuery, callback_data: WhitelistCallback, state: FSMContext):
    """
    پردازش انتخاب دلیل توسط کاربر.
    """
    reason_id = callback_data.reason_id
    user_id = callback_query.from_user.id

    if not reason_id or reason_id not in REASONS:
        await callback_query.answer("دلیل نامعتبر است.", show_alert=True)
        return

    reason_data = REASONS[reason_id]
    reason_name = reason_data["name"]
    reason_price = reason_data["price"]

    # ذخیره دلیل انتخاب شده و رفتن به مرحله تایید
    await state.update_data(selected_reason_id=reason_id)
    await state.set_state(UserWorkflow.awaiting_reason_confirmation)

    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="✅ تایید نهایی",
        callback_data=WhitelistCallback(action="confirm_reason", reason_id=reason_id).pack()
    ))
    builder.add(types.InlineKeyboardButton(
        text="❌ لغو",
        callback_data=WhitelistCallback(action="cancel_reason").pack()
    ))
    builder.adjust(2)

    text = (
        f"شما '{hbold(reason_name)}' را انتخاب کردید.\n"
        f"هزینه: {hbold(f'{reason_price:,} تومان')}.\n\n"
        "آیا برای تایید نهایی و انتقال به درگاه پرداخت آماده‌اید؟"
    )
    await callback_query.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback_query.answer("دلیل انتخاب شد.") # بستن نشانگر "Loading" روی دکمه

@dp.callback_query(WhitelistCallback.filter(F=lambda F, callback_data: callback_data.action == "confirm_reason"))
async def confirm_reason_purchase(callback_query: types.CallbackQuery, callback_data: WhitelistCallback, state: FSMContext):
    """
    تایید نهایی خرید Whitelist و هدایت به درگاه پرداخت (یا اتمام).
    """
    user_data = await state.get_data()
    reason_id = callback_data.reason_id # یا user_data.get('selected_reason_id')
    user_id = callback_query.from_user.id

    if not reason_id or reason_id not in REASONS:
        await callback_query.answer("خطایی رخ داد، لطفاً دوباره امتحان کنید.", show_alert=True)
        await state.clear()
        return

    reason_name = REASONS[reason_id]["name"]
    reason_price = REASONS[reason_id]["price"]

    logging.info(f"کاربر {user_id}، '{reason_name}' را با قیمت {reason_price} تایید کرد.")

    # --- بخش پیاده‌سازی پرداخت ---
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

    # --- شبیه‌سازی موفقیت پرداخت ---
    text = f"پرداخت شما برای '{reason_name}' با موفقیت انجام شد!\n\n"
    text += "اگر نیاز به کیت خاصی دارید، لطفاً با ادمین تماس بگیرید."
    await send_message_with_photo(callback_query, text, "whitelist_success", parse_mode="Markdown")
    await callback_query.answer("پرداخت موفق!")
    await state.clear() # ریست کردن وضعیت کاربر

@dp.callback_query(WhitelistCallback.filter(F=lambda F, callback_data: callback_data.action == "cancel_reason"))
async def cancel_reason_purchase(callback_query: types.CallbackQuery, state: FSMContext):
    """
    لغو فرآیند انتخاب دلیل.
    """
    user_id = callback_query.from_user.id
    logging.info(f"فرآیند Whitelist توسط کاربر {user_id} لغو شد.")
    await callback_query.message.edit_text("عملیات Whitelist لغو شد.")
    await callback_query.answer("عملیات لغو شد.")
    await state.clear() # پاک کردن وضعیت

# --- پردازش دستور /shop ---
@dp.message(Command("shop"))
async def open_main_shop(message: types.Message, state: FSMContext):
    """
    باز کردن منوی اصلی فروشگاه.
    """
    user_id = message.from_user.id
    logging.info(f"دستور /shop از کاربر {user_id} دریافت شد.")
    await state.set_state(UserWorkflow.awaiting_shop_choice)

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

    await message.reply("به فروشگاه خوش آمدید! کدام بخش را می‌خواهید مشاهده کنید؟", reply_markup=builder.as_markup())

@dp.callback_query(ShopCallback.filter(F=lambda F, callback_data: callback_data.action == "open_rank_shop"))
async def show_rank_shop(callback_query: types.CallbackQuery, state: FSMContext):
    """
    نمایش فروشگاه رنک.
    """
    user_id = callback_query.from_user.id
    logging.info(f"کاربر {user_id} فروشگاه رنک را باز کرد.")
    await state.set_state(UserWorkflow.awaiting_rank_purchase)

    message_text = f"🌟 {hbold('Rank Shop')} 🌟\n\n"
    message_text += "برای خرید کیت رنک، رنک مورد نظر خود را انتخاب کنید:\n\n"
    for item_id, item_data in RANK_SHOP_ITEMS.items():
        message_text += f"🔹 {hbold(item_data['name'])} » {hcode(f'{item_data['price']:,} تومان')}\n"

    message_text += "\nاگر فقط نیاز به کیت رنک دارید، رنک مورد نظر و کیت مورد نظر خود را بنویسید (مثلاً: 'Vip - کیت')."

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

    await callback_query.message.edit_text(message_text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback_query.answer("فروشگاه رنک")

@dp.callback_query(ShopCallback.filter(F=lambda F, callback_data: callback_data.action == "open_coin_shop"))
async def show_coin_shop(callback_query: types.CallbackQuery, state: FSMContext):
    """
    نمایش فروشگاه کوین.
    """
    user_id = callback_query.from_user.id
    logging.info(f"کاربر {user_id} فروشگاه کوین را باز کرد.")
    await state.set_state(UserWorkflow.awaiting_coin_purchase)

    message_text = f"💰 {hbold('Coin Shop')} 💰\n\n"
    message_text += "مقدار کوین مورد نظر خود را انتخاب کنید:\n\n"
    for item_id, item_data in COIN_SHOP_ITEMS.items():
        message_text += f"🔹 {hbold(item_data['name'])} » {hcode(f'{item_data['price']:,} تومان')}\n"

    message_text += f"\nاگر مقدار کوین مورد نظر شما بیشتر از این‌هاست، مقدار دلخواه خود را در چت بنویسید (هر کوین تقریباً {PRICE_PER_COIN:,} تومان)."

    builder = InlineKeyboardBuilder()
    for item_id, item_data in COIN_SHOP_ITEMS.items():
        builder.add(types.InlineKeyboardButton(
            text=f"{item_data['name']} ({item_data['price']:,} T)",
            callback_data=ShopCallback(action="buy_coin", item_id=item_id).pack()
        ))
    builder.adjust(1)

    # دکمه برای وارد کردن مقدار دلخواه
    builder.add(types.InlineKeyboardButton(
        text="مقدار دلخواه",
        callback_data=ShopCallback(action="custom_coin").pack()
    ))
    # دکمه بازگشت به منوی اصلی
    builder.add(types.InlineKeyboardButton(
        text="بازگشت به منوی اصلی",
        callback_data=ShopCallback(action="open_shop").pack()
    ))

    await callback_query.message.edit_text(message_text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback_query.answer("فروشگاه کوین")

@dp.callback_query(ShopCallback.filter(F=lambda F, callback_data: callback_data.action == "buy_rank"))
async def process_rank_purchase_callback(callback_query: types.CallbackQuery, callback_data: ShopCallback, state: FSMContext):
    """
    پردازش انتخاب رنک از فروشگاه.
    """
    item_id = callback_data.item_id
    user_id = callback_query.from_user.id

    if not item_id or item_id not in RANK_SHOP_ITEMS:
        await callback_query.answer("آیتم نامعتبر است.", show_alert=True)
        return

    item_data = RANK_SHOP_ITEMS[item_id]
    item_name = item_data["name"]
    item_price = item_data["price"]

    logging.info(f"کاربر {user_id} قصد خرید رنک '{item_name}' را دارد.")

    # --- بخش پیاده‌سازی پرداخت برای رنک ---
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

    # --- شبیه‌سازی موفقیت پرداخت ---
    confirmation_message = f"خرید رنک '{hbold(item_name)}' با موفقیت انجام شد!\n\n"
    confirmation_message += "اگر فقط نیاز به کیت رنک دارید، لطفاً با ادمین تماس بگیرید یا منتظر پیام باشید."

    await send_message_with_photo(callback_query, confirmation_message, "rank_purchase_success", parse_mode="Markdown")
    await callback_query.answer("خرید رنک موفق!")
    await state.clear() # ریست وضعیت

@dp.callback_query(ShopCallback.filter(F=lambda F, callback_data: callback_data.action == "buy_coin"))
async def process_coin_purchase_callback(callback_query: types.CallbackQuery, callback_data: ShopCallback, state: FSMContext):
    """
    پردازش انتخاب بسته کوین از فروشگاه.
    """
    item_id = callback_data.item_id
    user_id = callback_query.from_user.id

    if not item_id or item_id not in COIN_SHOP_ITEMS:
        await callback_query.answer("بسته کوین نامعتبر است.", show_alert=True)
        return

    item_data = COIN_SHOP_ITEMS[item_id]
    item_name = item_data["name"]
    item_price = item_data["price"]
    # استخراج تعداد کوین از item_id (مثلا '50' از '50_coin')
    try:
        coins_amount = int(item_id.split('_')[0])
    except ValueError:
        logging.error(f"فرمت item_id برای کوین نامعتبر است: {item_id}")
        await callback_query.answer("خطایی در پردازش بسته کوین رخ داد.", show_alert=True)
        await state.clear()
        return

    logging.info(f"کاربر {user_id} قصد خرید {item_name} ({coins_amount} کوین) را دارد.")

    # --- بخش پیاده‌سازی پرداخت برای کوین ---
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

    # --- شبیه‌سازی موفقیت پرداخت ---
    confirmation_message = f"خرید {hbold(item_name)} با موفقیت انجام شد!\n"
    confirmation_message += f"{hbold(f'{coins_amount} کوین')} به حساب شما اضافه خواهد شد."

    await send_message_with_photo(callback_query, confirmation_message, "coin_purchase_success", parse_mode="Markdown")
    await callback_query.answer("خرید کوین موفق!")
    await state.clear() # ریست وضعیت

@dp.callback_query(ShopCallback.filter(F=lambda F, callback_data: callback_data.action == "custom_coin"))
async def request_custom_coin_amount(callback_query: types.CallbackQuery, state: FSMContext):
    """
    درخواست مقدار دلخواه کوین از کاربر.
    """
    user_id = callback_query.from_user.id
    logging.info(f"کاربر {user_id} درخواست مقدار دلخواه کوین را داد.")
    await state.set_state(UserWorkflow.awaiting_custom_coin_amount)

    message_text = "لطفاً مقدار کوین مورد نظر خود را به عدد وارد کنید.\n"
    message_text += f"(هر کوین تقریباً {PRICE_PER_COIN:,} تومان محاسبه می‌شود.)"

    # دکمه لغو
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="❌ لغو", callback_data=ShopCallback(action="open_coin_shop").pack())) # بازگشت به فروشگاه کوین
    await callback_query.message.edit_text(message_text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback_query.answer("وارد کردن مقدار دلخواه")

@dp.message(UserWorkflow.awaiting_custom_coin_amount)
async def process_custom_coin_amount(message: types.Message, state: FSMContext):
    """
    پردازش مقدار دلخواه کوین وارد شده توسط کاربر.
    """
    user_id = message.from_user.id
    try:
        amount = int(message.text)
        if amount <= 0:
            await message.reply("مقدار کوین باید بیشتر از صفر باشد.")
            return

        total_price = amount * PRICE_PER_COIN

        logging.info(f"کاربر {user_id} درخواست {amount} کوین با قیمت تخمینی {total_price} را داد.")

        # --- بخش پیاده‌سازی پرداخت برای کوین دلخواه ---
        # اینجا باید کاربر را به درگاه پرداخت هدایت کنید.
        # مثال:
        # payment_link = await create_payment_link(user_id, total_price, f"Custom Coin Purchase - {amount} Coins")
        # if payment_link:
        #     text = f"شما درخواست {hbold(f'{amount} کوین')} را دارید.\n"
        #     text += f"هزینه تقریبی: {hcode(f'{total_price:,} تومان')}.\n\n"
        #     text += f"لطفاً روی لینک زیر کلیک کنید تا پرداخت را نهایی کنید:\n{hlink('پرداخت', payment_link)}"
        #     await send_message_with_photo(message, text, "coin_purchase_success", parse_mode="Markdown")
        # else:
        #     await message.reply("خطایی در ایجاد لینک پرداخت رخ داد. لطفاً بعداً دوباره امتحان کنید.")
        #     await state.clear()
        #     return

        # --- شبیه‌سازی نمایش پیام نهایی ---
        final_message = f"شما درخواست {hbold(f'{amount} کوین')} را دارید.\n"
        final_message += f"هزینه تقریبی: {hcode(f'{total_price:,} تومان')}.\n\n"
        final_message += "لطفاً برای نهایی کردن خرید و پرداخت، به ادمین پیام دهید تا راهنمایی لازم را دریافت کنید."

        # در این حالت، به جای هدایت به درگاه، کاربر را به ادمین ارجاع می‌دهیم.
        # می‌توانید یک پیام به ادمین هم ارسال کنید:
        await bot.send_message(STAFF_GROUP_ID,
                               f"کاربر {user_id} ({message.from_user.full_name}) درخواست خرید {amount} کوین را دارد. هزینه تقریبی: {total_price:,} تومان.")

        await message.reply(final_message, parse_mode="Markdown")

    except ValueError:
        await message.reply("مقدار وارد شده معتبر نیست. لطفاً فقط عدد وارد کنید.")
    except Exception as e:
        logging.error(f"خطا در پردازش کوین دلخواه: {e}")
        await message.reply("خطایی در پردازش درخواست شما رخ داد.")
    finally:
        await state.clear() # ریست وضعیت پس از پردازش

@dp.callback_query(ShopCallback.filter(F=lambda F, callback_data: callback_data.action == "open_shop"))
async def return_to_main_shop(callback_query: types.CallbackQuery, state: FSMContext):
    """
    بازگشت به منوی اصلی فروشگاه.
    """
    user_id = callback_query.from_user.id
    logging.info(f"کاربر {user_id} به منوی اصلی فروشگاه بازگشت.")
    await state.set_state(UserWorkflow.awaiting_shop_choice)

    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="🛒 فروشگاه رنک",
        callback_data=ShopCallback(action="open_rank_shop").pack()
    ))
    builder.add(types.InlineKeyboardButton(
        text="💰 ف",
        callback_data=ShopCallback(action="open_coin_shop").pack()
    ))
    builder.adjust(1)

    await callback_query.message.edit_text("به فروشگاه خوش آمدید! کدام بخش را می‌خواهید مشاهده کنید؟", reply_markup=builder.as_markup())
    await callback_query.answer("منوی اصلی فروشگاه")

# --- بخش اجرای وب‌سرور Flask برای زنده نگه داشتن برنامه در Render ---
app = Flask(__name__)

@app.route("/")
def index():
    """
    مسیر روت برای Render.
    """
    print("درخواست به مسیر روت Render دریافت شد.")
    return "ربات TheFellOmen فعال است!"

def run_flask_server():
    """
    اجرای وب‌سرور Flask.
    """
    try:
        app.run(host="0.0.0.0", port=PORT, debug=False)
    except Exception as e:
        logging.error(f"خطا در اجرای وب‌سرور Flask: {e}")

# --- تابع اصلی برای اجرای ربات ---
async def main():
    """
    تابع اصلی که ربات Aiogram و وب‌سرور Flask را راه‌اندازی می‌کند.
    """
    logging.info("شروع اجرای تابع main...")

    # راه‌اندازی وب‌سرور Flask در یک ترد جداگانه
    flask_thread = threading.Thread(target=run_flask_server)
    flask_thread.daemon = True #
