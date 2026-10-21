
import os
import logging

import httpx
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]
MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")

SYSTEM_PROMPT = """
Ты — WOODBASE AI, бизнес-ассистент мебельного бренда
в Ташкенте, Узбекистан.

Твои задачи:
- расчёт себестоимости и прибыли мебели;
- материалы, ЛДСП, МДФ и фурнитура;
- анализ мебельного рынка Ташкента;
- ассортимент, Instagram и продажи.

Отвечай на русском, кратко и по делу.
Не выдумывай цены, характеристики и факты.
Разделяй подтверждённые данные и предположения.
Если данных недостаточно, задай уточняющий вопрос.
При расчётах показывай формулу и допущения.
Не отправляй сообщения клиентам и не трать деньги
без разрешения владельца.

Не утверждай, что имеешь доступ к актуальным ценам
или базе WOODBASE, если они не предоставлены.
"""

bot = Bot(
    token=TELEGRAM_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "WOODBASE AI запущен.\n\n"
        "Я помогу с расчётами мебели, материалами, "
        "фурнитурой и развитием бизнеса.\n\n"
        "Напиши свой вопрос. Команда /help покажет подсказку."
    )


@dp.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "WOODBASE AI — команды:\n"
        "/start — начать работу\n"
        "/help — помощь\n\n"
        "Также можешь написать вопрос обычным текстом."
    )


@dp.message()
async def answer(message: Message):
    if not message.text:
        await message.answer("Пока я обрабатываю только текстовые сообщения.")
        return

    status = await message.answer("Анализирую запрос…")

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "X-Title": "WOODBASE AI",
                },
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": message.text},
                    ],
                },
            )
            response.raise_for_status()
            data = response.json()
            answer_text = data["choices"][0]["message"]["content"]

        if not answer_text:
            answer_text = "Модель вернула пустой ответ."

        # Telegram ограничивает длину одного сообщения.
        for i in range(0, len(answer_text), 4000):
            await message.answer(answer_text[i:i + 4000])

        await status.delete()

    except Exception:
        logging.exception("Ошибка при обработке запроса")
        await status.edit_text(
            "Не удалось получить ответ от ИИ. "
            "Возможно, модель недоступна или закончился лимит. "
            "Попробуй позже."
        )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
