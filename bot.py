import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from config import TOKEN, GROQ_API_KEY, ADMIN_ID
from openai import AsyncOpenAI
from db import init_db, add_message, get_history, clear_history, get_stats, add_chunks, get_chunks, clear_chunks
from rag import find_best_chunks, split_into_chunks

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

@dp.message(F.document)
async def handle_document(message: types.Message):
    user_id = message.from_user.id
    doc = message.document

    if not doc.file_name.endswith('.txt'):
        await message.answer('Можно загружать только текстовые файлы .txt')
        return
    if doc.file_size > 1_000_000:
        await message.answer('Файл слишком большой, максимум 1 МБ')
        return

    file = await bot.download(doc)
    try:
        text = file.read().decode('utf-8')
    except UnicodeDecodeError:
        await message.answer('Не удалось прочитать файл, сохрани его в кодировке UTF-8')
        return
    
    if not text.strip():
        await message.answer('Файл пустой')
        return
        

    doc_chunks = split_into_chunks(text)
    clear_chunks(user_id)
    add_chunks(user_id, doc.file_name, doc_chunks)
    await message.answer(f'Файл загружен. Получилось {len(doc_chunks)} фрагментов.')
   
    
@dp.message(F.text)
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    user_chunks = get_chunks(user_id)
    found_chunks = find_best_chunks(message.text, user_chunks)
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
    
