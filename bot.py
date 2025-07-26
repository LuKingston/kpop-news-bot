from aiohttp import web
import asyncio
import aiosqlite
import re
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import CommandStart

TOKEN = '7835580826:AAEqsqA1M5RkdE2l9ybKjLFyRav5tLM4A8k'  # замени на свой токен

GROUPS = [
    "BTS", "BLACKPINK", "NewJeans", "LE SSERAFIM",
    "ENHYPEN", "SEVENTEEN", "EXO", "Stray Kids",
    "TXT", "TWICE", "IVE", "ZEROBASEONE", "ATEEZ"
]

bot = Bot(token=TOKEN)
dp = Dispatcher()

async def init_db():
    async with aiosqlite.connect("users.db") as db:
        await db.execute(
            "CREATE TABLE IF NOT EXISTS subscriptions (user_id INTEGER, group_name TEXT)"
        )
        await db.commit()

def get_group_keyboard():
    keyboard = []
    row = []
    for i, group in enumerate(GROUPS, start=1):
        row.append(InlineKeyboardButton(text=group, callback_data=f"toggle:{group}"))
        if i % 2 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer(
        "Выбери K-pop группы, о которых хочешь получать новости:",
        reply_markup=get_group_keyboard()
    )

@dp.callback_query()
async def toggle_subscription(callback: types.CallbackQuery):
    group = callback.data.split(":")[1]
    user_id = callback.from_user.id
    async with aiosqlite.connect("users.db") as db:
        cursor = await db.execute(
            "SELECT 1 FROM subscriptions WHERE user_id = ? AND group_name = ?",
            (user_id, group)
        )
        exists = await cursor.fetchone()
        if exists:
            await db.execute(
                "DELETE FROM subscriptions WHERE user_id = ? AND group_name = ?",
                (user_id, group)
            )
            await callback.answer(f"Уведомления о {group} отключены")
        else:
            await db.execute(
                "INSERT INTO subscriptions (user_id, group_name) VALUES (?, ?)",
                (user_id, group)
            )
            await callback.answer(f"Теперь ты получаешь новости о {group}")
        await db.commit()

# Словарь для сбора сообщений альбома по media_group_id
media_groups = {}

@dp.message()
async def forward_handler(message: types.Message):
    if not message.forward_from_chat:
        return

    # Если сообщение часть альбома
   if message.media_group_id:
    group_id = message.media_group_id
    if group_id not in media_groups:
        media_groups[group_id] = []
    media_groups[group_id].append(message)

    # Ждем немного, чтобы собрать все сообщения альбома
    await asyncio.sleep(1)

    # Получаем и очищаем
    messages = media_groups.pop(group_id, [])
    if not messages:
        return

    text = messages[0].caption or ""
    hashtags = re.findall(r"#(\w+)", text)
    matched_groups = [g for g in GROUPS if g.upper().replace(" ", "") in [h.upper() for h in hashtags]]

    if not matched_groups:
        await messages[0].answer("❗️ Хэштеги не совпали ни с одной группой")
        return

    async with aiosqlite.connect("users.db") as db:
        for group in matched_groups:
            cursor = await db.execute("SELECT user_id FROM subscriptions WHERE group_name = ?", (group,))
            users = await cursor.fetchall()
            for (user_id,) in users:
                try:
                    for msg in messages:
                        await bot.copy_message(
                            chat_id=user_id,
                            from_chat_id=msg.chat.id,
                            message_id=msg.message_id
                        )
                except Exception as e:
                    print(f"Ошибка при отправке пользователю {user_id}: {e}")

    await messages[0].answer(f"✅ Новость отправлена подписчикам: {', '.join(matched_groups)}")

        if not messages:
            return

        # Берем хэштеги из первого сообщения (можно расширить, если нужно)
        text = messages[0].caption or ""
        hashtags = re.findall(r"#(\w+)", text)
        matched_groups = [g for g in GROUPS if g.upper().replace(" ", "") in [h.upper() for h in hashtags]]

        if not matched_groups:
            await messages[0].answer("❗️ Хэштеги не совпали ни с одной группой")
            return

        async with aiosqlite.connect("users.db") as db:
            for group in matched_groups:
                cursor = await db.execute(
                    "SELECT user_id FROM subscriptions WHERE group_name = ?", (group,)
                )
                users = await cursor.fetchall()
                for (user_id,) in users:
                    try:
                        for msg in messages:
                            await bot.copy_message(chat_id=user_id,
                                from_chat_id=msg.chat.id,
                                message_id=msg.message_id
                            )
                    except Exception as e:
                        print(f"Ошибка при отправке пользователю {user_id}: {e}")

        await messages[0].answer(f"✅ Новость отправлена подписчикам: {', '.join(matched_groups)}")

    else:
        # Обычное одиночное сообщение
        text = message.text or message.caption or ""
        hashtags = re.findall(r"#(\w+)", text)
        matched_groups = [g for g in GROUPS if g.upper().replace(" ", "") in [h.upper() for h in hashtags]]

        if not matched_groups:
            await message.answer("❗️ Хэштеги не совпали ни с одной группой")
            return

        async with aiosqlite.connect("users.db") as db:
            for group in matched_groups:
                cursor = await db.execute(
                    "SELECT user_id FROM subscriptions WHERE group_name = ?", (group,)
                )
                users = await cursor.fetchall()
                for (user_id,) in users:
                    try:
                        await bot.copy_message(
                            chat_id=user_id,
                            from_chat_id=message.chat.id,
                            message_id=message.message_id
                        )
                    except Exception as e:
                        print(f"Ошибка при отправке пользователю {user_id}: {e}")

        await message.answer(f"✅ Новость отправлена подписчикам: {', '.join(matched_groups)}")

async def handle(request):
    return web.Response(text="Bot is running")

async def start_webserver():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)  # порт 8080 для Render
    await site.start()

async def main():
    await init_db()
    await start_webserver()
    print("Бот и веб-сервер запущены")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())