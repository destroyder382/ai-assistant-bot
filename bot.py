import asyncio
import json
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from config import TOKEN, GROQ_API_KEY
from openai import AsyncOpenAI

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_PATH = os.path.join(BASE_DIR, 'histories.json')

client = AsyncOpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)

bot = Bot(token=TOKEN)
dp = Dispatcher()

def save_histories():
    with open(HISTORY_PATH, 'w', encoding='utf-8') as f:
        json.dump(histories, f, ensure_ascii=False)

def load_histories():
    global histories
    try:
        with open(HISTORY_PATH, 'r', encoding='utf-8') as f:
            histories = json.load(f)
    except FileNotFoundError:
        histories = {}

load_histories()

@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    await message.answer('Привет! Я твой бот.')

@dp.message(F.text)
async def handle_text(message: types.Message):
    user_id = str(message.from_user.id)

    if user_id not in histories:
        histories[user_id] = [
            {"role": "system", "content": "Ты дружелюбный ассистент. Отвечай по-русски, кратко и простым текстом, без Markdown."}
        ]
    histories[user_id].append({'role': 'user', 'content': message.text})

    response = await client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=histories[user_id],
    )
    answer_text = response.choices[0].message.content
    histories[user_id].append({'role': 'assistant', 'content': answer_text})
    save_histories()
    await message.answer(answer_text)

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())