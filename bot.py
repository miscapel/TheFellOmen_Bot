import logging
import os
import threading
import asyncio
from typing import Literal

# --- کتابخانه‌های مورد نیاز ---
from aiogram import Bot, Dispatcher, types # F برای فیلتر کردن حذف شده است
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
from flask import Flask, request

# --- تنظیمات اولیه و لاگ‌گیری ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
print("--- ربات در حال شروع است ---")

load_dotenv()

# --- تنظیمات ربات ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
STAFF_GROUP_ID = os.getenv("STAFF_GROUP_ID")
PORT = os.getenv("PORT", "10000") # مقدار پیش‌فرض 10000

if not BOT_TOKEN:
    logging.error("خطا: BOT_TOKEN تنظیم نشده است. لطفاً در تنظیمات Render، متغیر محیطی BOT_TOKEN را با توکن ربات خود تنظیم کنید.")
    exit(1)
if not STAFF_GROUP_ID:
    logging.error("خطا: STAFF_GROUP_ID تنظیم نشده است. لطفاً در تنظیمات Render، متغیر محیطی STAFF_GROUP_ID را با شناسه گروه خود تنظیم کنید.")
    exit(1)
try:
    STAFF_GROUP_ID = int(STAFF_GROUP_ID)
except ValueError:
    logging.error(f"خطا: STAFF_GROUP_ID مقدار معتبر عددی ندارد: '{STAFF_GROUP_ID}'. لطفاً یک عدد صحیح وارد کنید.")
    exit(1)
try:
    PORT = int(PORT)
except ValueError:
    logging.error(f"خطا: PORT مقدار معتبر عددی ندارد: '{PORT}'. لطفاً یک عدد صحیح وارد کنید.")
    exit(1)

logging.info(f"تنظیمات محیطی خوانده شد: BOT_TOKEN=***, STAFF_GROUP_ID={STAFF_GROUP_ID}, PORT={PORT}")

# --- راه‌اندازی ربات و دیسپچر با MemoryStorage ---
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# --- تعریف State ها ---
class UserWorkflow(StatesGroup):
    selecting_reason = State()
    awaiting_reason_confirmation = State()
    awaiting_shop_choice = State()
    awaiting_rank_purchase = State()
    awaiting_coin_purchase = State()
    awaiting_custom_coin_amount = State()

# --- داده‌های نمونه ---
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
PRICE_PER_COIN = 300

# --- Callback Data Factories ---
class WhitelistCallback(CallbackData, prefix="whitelist"):
    action: Literal["select_reason", "confirm_reason", "cancel_reason"]
    reason_id: str | None = None

class ShopCallback(CallbackData, prefix="shop"):
    action: Literal["open_rank_shop", "open_coin_shop", "buy_rank", "buy_coin", "custom_coin", "open_shop"]
    item_id: str | None = None
    amount: int | None = None

# --- تصاویر نمونه ---
# توجه: این مسیرها باید در واقعیت وجود داشته باشند. اگر این فایل‌ها را ندارید، از ارسال عکس صرف نظر کنید.
PHOTO_PATHS = {
    "whitelist_success": "photos/whitelist_success.jpg",
    "rank_purchase_success": "photos/rank_purchase_success.jpg",
    "coin_purchase_success": "photos/coin_purchase_success.jpg",
}

def get_photo_path(key: str) -> str | None:
    path = PHOTO_PATHS.get(key)
    # در محیط Render، مسیر نسبی ممکن است متفاوت باشد.
    # برای تست محلی، مطمئن شوید مسیر درست است.
    # اگر فایل‌ها در پوشه 'photos' در کنار bot.py هستند، مسیر بالا درست است.
    if path and os.path.exists(path):
        return path
    # logging.warning(f"فایل عکس برای '{key}' در مسیر '{path}' یافت نشد.")
    return None

async def send_message_with_photo(
    message: types.Message | types.CallbackQuery,
    text: str,
    photo_key: str,
    reply_markup: types.InlineKeyboardMarkup | None = None,
    parse_mode: str = "Markdown"
):
    photo_path = get_photo_path(photo_key)
    if isinstance(message, types.CallbackQuery):
        message_obj = message.message
        chat_id = message.message.chat.id
        message_id = message.message.message_id
    else:
        message_obj = message
        chat_id = message.chat.id
        message_id = message.message_id

    if photo_path:
        try:
            with open(photo_path, 'rb') as photo_file:
                # اگر CallbackQuery باشد، از answer_photo استفاده کنید
                if isinstance(message, types.CallbackQuery):
                     await message.message.answer_photo(photo=photo_file, caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
                else:
                     await message.answer_photo(photo=photo_file, caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
            return True
        except FileNotFoundError:
            logging.warning(f"فایل عکس برای '{photo_key}' یافت نشد در مسیر: {photo_path}. ارسال پیام متنی.")
            if isinstance(message, types.CallbackQuery):
                await message.message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
            else:
                await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
            return False
        except Exception as e:
            logging.error(f"خطا در ارسال عکس {photo_key}: {e}")
            if isinstance(message, types.CallbackQuery):
                await message.message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
            else:
                await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
            return False
    else:
        if isinstance(message, types.CallbackQuery):
            await message.message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
        return False

# --- پردازش دستور /start ---
@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    user_name = message.from_user.full_name
    user_id = message.from_user.id
    logging.info(f"دستور /start از کاربر {user_name} (ID: {user_id}) دریافت شد.")
    await message.reply(f"سلام {hbold(user_name)}!\nبه ربات TheFellOmen خوش آمدید! برای مشاهده امکانات، از دستور /help استفاده کنید.")

# --- پردازش دستور /help ---
@dp.message(Command("help"))
async def send_help(message: types.Message):
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
    user_id = message.from_user.id
    logging.info(f"دستور /whitelist از کاربر {user_id} دریافت شد.")
    await state.set_state(UserWorkflow.selecting_reason)
    builder = InlineKeyboardBuilder()
    for reason_id, reason_data in REASONS.items():
        builder.add(types.InlineKeyboardButton(
            text=f"{reason_data['name']} ({reason_data['price']:,} T)",
            callback_data=WhitelistCallback(action="select_reason", reason_id=reason_id).pack()
        ))
    builder.adjust(1)
    await message.reply("لطفاً یکی از دلایل زیر را برای Whitelist انتخاب کنید:", reply_markup=builder.as_markup())

# --- پردازش کلیک روی دکمه انتخاب دلیل Whitelist ---
@dp.callback_query(WhitelistCallback.filter(WhitelistCallback.action == "select_reason"))
async def process_reason_selection(callback_query: types.CallbackQuery, callback_data: WhitelistCallback, state: FSMContext):
    reason_id = callback_data.reason_id
    user_id = callback_query.from_user.id
    if not reason_id or reason_id not in REASONS:
        await callback_query.answer("دلیل نامعتبر است.", show_alert=True)
        return
    reason_data = REASONS[reason_id]
    reason_name = reason_data["name"]
    reason_price = reason_data["price"]
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
    # اگر پیام اصلی حاوی دکمه‌ها بود، آن را ادیت کن، در غیر این صورت جواب بده
    if callback_query.message:
        await callback_query.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    else: # این حالت نباید رخ دهد اگر callback_query از پیام آمده باشد
        await callback_query.message.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback_query.answer("دلیل انتخاب شد.")

# --- پردازش تایید نهایی خرید Whitelist ---
@dp.callback_query(WhitelistCallback.filter(WhitelistCallback.action == "confirm_reason"))
async def confirm_reason_purchase(callback_query: types.CallbackQuery, callback_data: WhitelistCallback, state: FSMContext):
    reason_id = callback_data.reason_id
    user_id = callback_query.from_user.id
    if not reason_id or reason_id not in REASONS:
        await callback_query.answer("خطایی رخ داد، لطفاً دوباره امتحان کنید.", show_alert=True)
        await state.clear()
        return
    reason_name = REASONS[reason_id]["name"]
    reason_price = REASONS[reason_id]["price"]
    logging.info(f"کاربر {user_id}، '{reason_name}' را با قیمت {reason_price} تایید کرد.")
    # =====================================================
    # === بخش پیاده‌سازی پرداخت ===
    # (کد پرداخت شما اینجا قرار می‌گیرد)
    # =====================================================
    text = f"پرداخت شما برای '{reason_name}' با موفقیت انجام شد!\n\n"
    text += "اگر نیاز به کیت خاصی دارید، لطفاً با ادمین تماس بگیرید."
    await send_message_with_photo(callback_query, text, "whitelist_success", parse_mode="Markdown")
    await callback_query.answer("پرداخت موفق!")
    await state.clear()

# --- پردازش دکمه لغو Whitelist ---
@dp.callback_query(WhitelistCallback.filter(WhitelistCallback.action == "cancel_reason"))
async def cancel_reason_purchase(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    logging.info(f"فرآیند Whitelist توسط کاربر {user_id} لغو شد.")
    if callback_query.message:
        await callback_query.message.edit_text("عملیات Whitelist لغو شد.")
    await callback_query.answer("عملیات لغو شد.")
    await state.clear()

# --- پردازش دستور /shop ---
@dp.message(Command("shop"))
async def open_main_shop(message: types.Message, state: FSMContext):
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

# --- نمایش فروشگاه رنک ---
@dp.callback_query(ShopCallback.filter(ShopCallback.action == "open_rank_shop"))
async def show_rank_shop(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    logging.info(f"کاربر {user_id} فروشگاه رنک را باز کرد.")
    await state.set_state(UserWorkflow.awaiting_rank_purchase)
    message_text = f"🌟 {hbold('Rank Shop')} 🌟\n\n"
    message_text += "برای خرید کیت رنک، رنک مورد نظر خود را انتخاب کنید:\n\n"
    for item_id, item_data in RANK_SHOP_ITEMS.items():
        message_text += f"🔹 {hbold(item_data['name'])} » {hcode(f'{item_data['price']:,} تومان')}\n"
    message_text += "\nبرای خرید کیت رنک، پس از انتخاب رنک، لطفاً نام کیت مورد نظر (مثلاً 'کیت') را در چت بنویسید."
    builder = InlineKeyboardBuilder()
    for item_id, item_data in RANK_SHOP_ITEMS.items():
        builder.add(types.InlineKeyboardButton(
            text=f"{item_data['name']} ({item_data['price']:,} T)",
            callback_data=ShopCallback(action="buy_rank", item_id=item_id).pack()
        ))
    builder.adjust(1)
    builder.add(types.InlineKeyboardButton(
        text="بازگشت به منوی اصلی",
        callback_data=ShopCallback(action="open_shop").pack()
    ))
    if callback_query.message:
        await callback_query.message.edit_text(message_text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback_query.answer("فروشگاه رنک")

# --- نمایش فروشگاه کوین ---
@dp.callback_query(ShopCallback.filter(ShopCallback.action == "open_coin_shop"))
async def show_coin_shop(callback_query: types.CallbackQuery, state: FSMContext):
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
    builder.add(types.InlineKeyboardButton(
        text="مقدار دلخواه",
        callback_data=ShopCallback(action="custom_coin").pack()
    ))
    builder.add(types.InlineKeyboardButton(
        text="بازگشت به منوی اصلی",
        callback_data=ShopCallback(action="open_shop").pack()
    ))
    if callback_query.message:
        await callback_query.message.edit_text(message_text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback_query.answer("فروشگاه کوین")

# --- پردازش خرید رنک از فروشگاه ---
@dp.callback_query(ShopCallback.filter(ShopCallback.action == "buy_rank"))
async def process_rank_purchase_callback(callback_query: types.CallbackQuery, callback_data: ShopCallback, state: FSMContext):
    item_id = callback_data.item_id
    user_id = callback_query.from_user.id
    if not item_id or item_id not in RANK_SHOP_ITEMS:
        await callback_query.answer("آیتم نامعتبر است.", show_alert=True)
        return
    item_data = RANK_SHOP_ITEMS[item_id]
    item_name = item_data["name"]
    item_price = item_data["price"]
    logging.info(f"کاربر {user_id} قصد خرید رنک '{item_name}' را دارد.")
    # در این مرحله، کاربر باید نوع کیت را مشخص کند.
    await state.update_data(selected_rank_item_id=item_id)
    await state.set_state(UserWorkflow.awaiting_rank_purchase) # تغییر حالت برای انتظار دریافت نام کیت
    message_text = f"شما '{hbold(item_name)}' را انتخاب کردید.\n"
    message_text += f"هزینه: {hcode(f'{item_price:,} تومان')}.\n\n"
    message_text += "لطفاً نام کیت مورد نظر خود را وارد کنید (مثلاً: 'کیت' یا 'Kit')."
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="لغو", callback_data=ShopCallback(action="open_rank_shop").pack()))
    if callback_query.message:
        await callback_query.message.edit_text(message_text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback_query.answer("تایید انتخاب رنک")

# پردازش دریافت نام کیت پس از انتخاب رنک
@dp.message(UserWorkflow.awaiting_rank_purchase)
async def process_rank_kit_name(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    selected_rank_item_id = (await state.get_data()).get("selected_rank_item_id")
    kit_name = message.text # نام کیت وارد شده توسط کاربر

    if not selected_rank_item_id or selected_rank_item_id not in RANK_SHOP_ITEMS:
        await message.reply("خطایی در انتخاب رنک رخ داد. لطفاً دوباره /shop را بزنید.")
        await state.clear()
        return

    item_data = RANK_SHOP_ITEMS[selected_rank_item_id]
    item_name = item_data["name"]
    item_price = item_data["price"]
    logging.info(f"کاربر {user_id} برای رنک '{item_name}' کیت '{kit_name}' را انتخاب کرد.")

    # =====================================================
    # === بخش پیاده‌سازی پرداخت برای رنک ===
    # (کد پرداخت شما اینجا قرار می‌گیرد.
    # در اینجا، فقط یک پیام تایید ارسال می‌شود.
    # شما باید منطق پرداخت واقعی را پیاده‌سازی کنید.)
    # =====================================================
    confirmation_message = f"خرید رنک '{hbold(item_name)}' با کیت '{hbold(kit_name)}' با موفقیت انجام شد!\n"
    confirmation_message += f"هزینه: {hcode(f'{item_price:,} تومان')}.\n\n"
    confirmation_message += "شما به زودی دسترسی خود را دریافت خواهید کرد."
    await send_message_with_photo(message, confirmation_message, "rank_purchase_success", parse_mode="Markdown")
    await message.reply("خرید شما ثبت شد!")
    await state.clear()


# --- پردازش خرید کوین از فروشگاه ---
@dp.callback_query(ShopCallback.filter(ShopCallback.action == "buy_coin"))
async def process_coin_purchase_callback(callback_query: types.CallbackQuery, callback_data: ShopCallback, state: FSMContext):
    item_id = callback_data.item_id
    user_id = callback_query.from_user.id
    if not item_id or item_id not in COIN_SHOP_ITEMS:
        await callback_query.answer("بسته کوین نامعتبر است.", show_alert=True)
        return
    item_data = COIN_SHOP_ITEMS[item_id]
    item_name = item_data["name"]
    item_price = item_data["price"]
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
    # (کد پرداخت شما اینجا قرار می‌گیرد)
    # =====================================================
    confirmation_message = f"خرید {hbold(item_name)} با موفقیت انجام شد!\n"
    confirmation_message += f"{hbold(f'{coins_amount} کوین')} به حساب شما اضافه خواهد شد."
    await send_message_with_photo(callback_query, confirmation_message, "coin_purchase_success", parse_mode="Markdown")
    await callback_query.answer("خرید کوین موفق!")
    await state.clear()

# --- درخواست مقدار دلخواه کوین ---
@dp.callback_query(ShopCallback.filter(ShopCallback.action == "custom_coin"))
async def request_custom_coin_amount(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    logging.info(f"کاربر {user_id} درخواست مقدار دلخواه کوین را داد.")
    await state.set_state(UserWorkflow.awaiting_custom_coin_amount)
    message_text = "لطفاً مقدار کوین مورد نظر خود را به عدد وارد کنید.\n"
    message_text += f"(هر کوین تقریباً {PRICE_PER_COIN:,} تومان محاسبه می‌شود.)"
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="لغو", callback_data=ShopCallback(action="open_coin_shop").pack()))
    if callback_query.message:
        await callback_query.message.edit_text(message_text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback_query.answer("وارد کردن مقدار دلخواه")

# --- پردازش مقدار دلخواه کوین وارد شده توسط کاربر ---
@dp.message(UserWorkflow.awaiting_custom_coin_amount)
async def process_custom_coin_amount(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        amount = int(message.text)
        if amount <= 0:
            await message.reply("مقدار کوین باید بیشتر از صفر باشد.")
            return
        total_price = amount * PRICE_PER_COIN
        logging.info(f"کاربر {user_id} درخواست {amount} کوین با قیمت تخمینی {total_price} را داد.")
        # =====================================================
        # === بخش پیاده‌سازی پرداخت برای کوین دلخواه ===
        # (در این حالت، به جای هدایت به درگاه، کاربر را به ادمین ارجاع می‌دهیم.)
        # ارسال پیام به گروه ادمین
        admin_message_text = (
            f"کاربر {hbold(message.from_user.full_name)} (ID: {user_id}) درخواست خرید {hbold(f'{amount} کوین')} را دارد.\n"
            f"هزینه تقریبی: {hcode(f'{total_price:,} تومان')}.\n\n"
            "لطفاً برای هماهنگی و دریافت لینک پرداخت، با ایشان در ارتباط باشید."
        )
        await bot.send_message(STAFF_GROUP_ID, admin_message_text, parse_mode="Markdown")

        final_message = f"شما درخواست {hbold(f'{amount} کوین')} را دارید.\n"
        final_message += f"هزینه تقریبی: {hcode(f'{total_price:,} تومان')}.\n\n"
        final_message += "لطفاً منتظر پیام ادمین برای هماهنگی و دریافت لینک پرداخت باشید."
        await message.reply(final_message, parse_mode="Markdown")
    except ValueError:
        await message.reply("مقدار وارد شده معتبر نیست. لطفاً فقط عدد وارد کنید.")
    except Exception as e:
        logging.error(f"خطا در پردازش کوین دلخواه: {e}")
        await message.reply("خطایی در پردازش درخواست شما رخ داد.")
    finally:
        await state.clear()

# --- بازگشت به منوی اصلی فروشگاه ---
@dp.callback_query(ShopCallback.filter(ShopCallback.action == "open_shop"))
async def return_to_main_shop(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    logging.info(f"کاربر {user_id} به منوی اصلی فروشگاه بازگشت.")
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
    if callback_query.message:
        await callback_query.message.edit_text("به منوی اصلی فروشگاه خوش آمدید! کدام بخش را می‌خواهید مشاهده کنید؟", reply_markup=builder.as_markup())
    await callback_query.answer("منوی اصلی فروشگاه")

# --- وب‌سرور Flask برای Keep-Alive در Render ---
app = Flask(__name__)

@app.route('/')
async def homepage():
    return "ربات TheFellOmen در حال اجراست!"

# یک endpoint ساده برای دریافت webhook اگر لازم باشد (البته اینجا از polling استفاده می‌کنیم)
@app.route('/webhook', methods=['POST'])
async def webhook():
    update = types.Update.model_validate(request.json)
    await dp.feed_update(bot, update)
    return "OK", 200

def run_flask_server():
    try:
        # استفاده از waitress یا gunicorn برای production بهتر است، اما برای سادگی از app.run استفاده می‌کنیم
        app.run(host="0.0.0.0", port=PORT, debug=False)
    except Exception as e:
        logging.error(f"خطا در اجرای وب‌سرور Flask: {e}")

# --- تابع اصلی برای اجرای ربات و وب‌سرور ---
async def main():
    logging.info("شروع اجرای تابع main...")

    # اجرای Flask در یک ترد جداگانه
    flask_thread = threading.Thread(target=run_flask_server)
    flask_thread.daemon = True # اجازه می‌دهد برنامه اصلی بسته شود حتی اگر این ترد هنوز در حال اجرا باشد
    flask_thread.start()
    logging.info("ترد وب‌سرور Flask راه‌اندازی شد.")

    # شروع پولینگ Aiogram
    logging.info("شروع پولینگ Aiogram...")
    try:
        # skip_updates=True برای نادیده گرفتن پیام‌هایی که ربات آفلاین بوده است
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logging.error(f"خطا در هنگام اجرای پولینگ Aiogram: {e}")
    finally:
        logging.info("پولینگ Aiogram متوقف شد.")

# --- اجرای برنامه ---
if __name__ == "__main__":
    print("اجرای اسکریپت اصلی...")
    try:
        # استفاده از asyncio.run() برای اجرای تابع async main
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("ربات با KeyboardInterrupt متوقف شد.")
    except Exception as e:
        logging.critical(f"خطای بحرانی در اجرای اصلی: {e}")
    finally:
        print("--- ربات متوقف شد ---")
