import logging
import os
import threading
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from dotenv import load_dotenv # فقط برای اجرای لوکال، در Render استفاده نمی‌شود

# --- بخش تنظیمات اولیه و متغیرهای محیطی ---

print("--- ربات در حال شروع است ---") # لاگ برای Render

# بارگذاری متغیرهای محیطی (فقط برای اجرای محلی)
# در Render، این متغیرها مستقیماً از پنل تنظیمات خوانده می‌شوند.
load_dotenv()

# خواندن تنظیمات از متغیرهای محیطی
BOT_TOKEN = os.getenv("BOT_TOKEN")
STAFF_GROUP_ID = os.getenv("STAFF_GROUP_ID")
PORT = os.getenv("PORT", "10000") # مقدار پیش‌فرض 10000 اگر PORT تعریف نشده باشد

# اطمینان از تنظیم بودن متغیرهای ضروری
if not BOT_TOKEN:
    print("خطا: BOT_TOKEN تنظیم نشده است. لطفاً در تنظیمات Render آن را وارد کنید.")
    exit(1)
if not STAFF_GROUP_ID:
    print("خطا: STAFF_GROUP_ID تنظیم نشده است. لطفاً در تنظیمات Render آن را وارد کنید.")
    exit(1)
try:
    STAFF_GROUP_ID = int(STAFF_GROUP_ID) # تبدیل به عدد صحیح
except ValueError:
    print(f"خطا: STAFF_GROUP_ID مقدار معتبر عددی ندارد: {STAFF_GROUP_ID}")
    exit(1)
try:
    PORT = int(PORT) # تبدیل به عدد صحیح
except ValueError:
    print(f"خطا: PORT مقدار معتبر عددی ندارد: {PORT}")
    exit(1)

print(f"تنظیمات محیطی خوانده شد: BOT_TOKEN={BOT_TOKEN[:5]}..., STAFF_GROUP_ID={STAFF_GROUP_ID}, PORT={PORT}")

# --- بخش راه‌اندازی ربات Aiogram ---

# فعال کردن لاگ‌گیری
logging.basicConfig(level=logging.INFO)
print("لاگ‌گیری Aiogram فعال شد.")

# راه‌اندازی ربات و دیسپچر
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- بخش تعریف دستورات و پردازش پیام‌ها ---

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    """
    این تابع وقتی کاربر دستور /start را ارسال کند، اجرا می‌شود.
    """
    user_name = message.from_user.full_name
    user_id = message.from_user.id
    print(f"دستور /start از کاربر {user_name} (ID: {user_id}) دریافت شد.")
    await message.reply(f"سلام {user_name}!\nمن ربات TheFellOmen هستم. خوش آمدید!")

@dp.message(Command("help"))
async def send_help(message: types.Message):
    """
    این تابع وقتی کاربر دستور /help را ارسال کند، اجرا می‌شود.
    """
    print(f"دستور /help از کاربر {message.from_user.full_name} (ID: {message.from_user.id}) دریافت شد.")
    await message.reply("برای راهنمایی، لطفاً با ادمین تماس بگیرید.")

# پردازش پیام‌های متنی معمولی (اگر لازم باشد)
# @dp.message()
# async def handle_all_messages(message: types.Message):
#     print(f"پیام دریافت شد از {message.from_user.full_name}: {message.text}")
#     await message.answer("پیام شما دریافت شد.")

# --- بخش اجرای وب‌سرور Flask برای زنده نگه داشتن برنامه در Render ---

from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    """
    یک مسیر ساده برای پاسخ دادن به درخواست‌های HTTP.
    این تابع باعث می‌شود Render برنامه را فعال نگه دارد.
    """
    print("درخواست به مسیر روت دریافت شد.")
    return "ربات TheFellOmen در حال اجرا است!"

def run_flask_server():
    """
    این تابع وب‌سرور Flask را در یک ترد جداگانه اجرا می‌کند.
    """
    print(f"راه‌اندازی وب‌سرور Flask روی پورت: {PORT}")
    try:
        app.run(host="0.0.0.0", port=PORT, debug=False) # debug=False برای محیط پروداکشن
    except Exception as e:
        print(f"خطا در اجرای وب‌سرور Flask: {e}")

# --- تابع اصلی برای اجرای ربات ---

async def main():
    """
    تابع اصلی که ربات Aiogram را راه‌اندازی و اجرا می‌کند.
    """
    print("شروع اجرای تابع main...")

    # راه‌اندازی وب‌سرور Flask در یک ترد جداگانه
    flask_thread = threading.Thread(target=run_flask_server)
    flask_thread.daemon = True # اجازه می‌دهد برنامه اصلی با بسته شدن ربات، برنامه Flask را هم ببندد
    flask_thread.start()
    print("ترد وب‌سرور Flask راه‌اندازی شد.")

    # شروع به کار دیسپچر Aiogram برای دریافت آپدیت‌ها (پولینگ)
    print("شروع پولینگ Aiogram...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"خطا در هنگام اجرای پولینگ Aiogram: {e}")
    finally:
        print("پولینگ Aiogram متوقف شد.")
        # در صورت نیاز، اینجا می‌توانید کارهای پایانی را انجام دهید.

if __name__ == "__main__":
    # این بلوک فقط زمانی اجرا می‌شود که فایل bot.py مستقیماً اجرا شود.
    print("اجرای اسکریپت اصلی...")
    try:
        # اجرای تابع main با استفاده از asyncio
        import asyncio
        asyncio.run(main())
    except KeyboardInterrupt:
        print("ربات با Ctrl+C متوقف شد.")
    except Exception as e:
        print(f"خطای ناشناخته در اجرای اصلی: {e}")
    finally:
        print("--- ربات متوقف شد ---")
