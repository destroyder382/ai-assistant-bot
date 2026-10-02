import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from config import TOKEN, GROQ_API_KEY, ADMIN_ID
from openai import AsyncOpenAI
from db import init_db, add_message, get_history, clear_history, get_stats
from rag import load_chunks, find_best_chunks

SYSTEM_PROMPT = {
    "role": "system",
    "content": "Ты дружелюбный ассистент. Отвечай по-русски, кратко и простым текстом, без Markdown.",
}

client = AsyncOpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)

bot = Bot(token=TOKEN)
dp = Dispatcher()

init_db()
chunks = load_chunks()


@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    await message.answer('Привет! Я твой бот. Команда /reset очищает нашу историю диалога.')


@dp.message(Command('reset'))
async def cmd_reset(message: types.Message):
    clear_history(message.from_user.id)
    await message.answer('История диалога очищена.')


@dp.message(Command('myid'))
async def cmd_myid(message: types.Message):
    await message.answer(str(message.from_user.id))


@dp.message(Command('stats'))
async def cmd_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    users, questions, by_day, top_users, avg_length = get_stats()

    lines = [
        f'Пользователей: {users}',
        f'Вопросов всего: {questions}',
        f'Средняя длина ответа: {round(avg_length or 0)} символов',
        '',
        'По дням:',
    ]
    lines += [f'{day}: {cnt}' for day, cnt in by_day]
    lines += ['', 'Самые активные:']
    lines += [f'{uid}: {cnt}' for uid, cnt in top_users]

    await message.answer('\n'.join(lines))


@dp.message(F.text)
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    found_chunks = find_best_chunks(message.text, chunks)
    print(len(found_chunks), "фрагментов найдено")
    user_text = message.text
    if found_chunks:
        context = "\n---\n".join(found_chunks)
        user_text = (
            "Фрагменты из документа:\n"
            f"{context}\n\n"
            "Если эти фрагменты относятся к вопросу, ответь по ним. "
            "Если нет, ответь как обычно.\n\n"
            f"Вопрос: {message.text}"
        )
    messages = [SYSTEM_PROMPT] + get_history(user_id) + [
        {'role': 'user', 'content': user_text}
    ]

    try:
        response = await client.chat.completions.create(
            model='openai/gpt-oss-120b',
            messages=messages,
        )
        answer_text = response.choices[0].message.content
    except Exception:
        logging.exception('Ошибка запроса к LLM')
        await message.answer('Сейчас не получается ответить, попробуй чуть позже.')
        return

    add_message(user_id, 'user', message.text)
    add_message(user_id, 'assistant', answer_text)
    await message.answer(answer_text)


async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
    
