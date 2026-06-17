async def set_bot_commands():
    commands = [
        BotCommand(command="start", description="منوی اصلی"),
        BotCommand(command="punishment", description="درخواست آن‌بن/آن‌میوت"),
        BotCommand(command="whitelist", description="درخواست وایت‌لیست"),
        BotCommand(command="shop", description="فروشگاه"),
        BotCommand(command="support", description="ارتباط با استف"),
        BotCommand(command="help", description="راهنما"),
        BotCommand(command="broadcast", description="[Admin Only] ارسال پیام همگانی"),
    ]
    await bot.set_my_commands(commands)

# اضافه کردن هندلر مستقیم برای دستورات جدید جهت راحتی کاربر
@dp.message(Command("punishment"))
async def cmd_punishment(message: types.Message, state: FSMContext):
    await open_punishment_appeal(message, state) # ارجاع به تابع قبلی

@dp.message(Command("whitelist"))
async def cmd_whitelist(message: types.Message, state: FSMContext):
    await open_whitelist(message, state)

@dp.message(Command("shop"))
async def cmd_shop(message: types.Message, state: FSMContext):
    await open_shop(message, state)

@dp.message(Command("support"))
async def cmd_support(message: types.Message, state: FSMContext):
    await open_contact_staff(message, state)

# اصلاح هندلر broadcast برای مخفی کردن رفتار از دید غیر ادمین
@dp.message(Command("broadcast"))
async def broadcast_command(message: types.Message):
    remember_user(message.from_user)
    
    # اگر ادمین نیست، کلاً وانمود می‌کنیم دستور وجود ندارد یا پیام عدم دسترسی می‌دهیم
    if not is_admin(message.from_user.id):
        await message.reply("❌ این دستور برای شما تعریف نشده است.")
        return
    
    # ... بقیه کدهای broadcast که قبلاً داشتی ...
