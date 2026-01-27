import telebot
from google import genai

from dotenv import load_dotenv
import os

load_dotenv()

# Загружаем переменные из файла .env
GEMINI_KEY = os.getenv('GEMINI_KEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')


client = genai.Client(api_key=GEMINI_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

user_contexts = {}

def generate_with_context(user_id, text):
    if user_id not in user_contexts:
        user_contexts[user_id] = []

    # Правильный формат для google-genai SDK
    # Вместо словарей лучше использовать объекты, но словари тоже допустимы,
    # если соблюдена структура: 'role' и 'parts' (где parts — список словарей с 'text')
    user_contexts[user_id].append({"role": "user", "parts": [{"text": text}]})

    try:
        # Пытаемся получить ответ
        response = client.models.generate_content(
            model="gemini-3-flash-preview", # Рекомендую использовать стабильную версию 2.0
            contents=user_contexts[user_id]
        )

        if not response.text:
            return "Извините, я не смог сгенерировать ответ."

        # Сохраняем ответ модели в историю
        user_contexts[user_id].append({"role": "model", "parts": [{"text": response.text}]})

        # Ограничиваем историю (важно: количество элементов должно быть четным, чтобы всегда начиналось с user)
        if len(user_contexts[user_id]) > 10:
            user_contexts[user_id] = user_contexts[user_id][-10:]

        return response.text

    except Exception as e:
        print(f"Ошибка в API: {e}")
        # Если произошла ошибка структуры, иногда помогает очистить историю для этого юзера
        # user_contexts[user_id] = []
        return f"Произошла ошибка при обращении к нейросети."

@bot.message_handler(commands=['start', 'clear'])
def send_welcome(message):
    user_contexts[message.chat.id] = []
    bot.reply_to(message, "История чата очищена. О чем хочешь поговорить?")

@bot.message_handler(func=lambda message: True)
def message_generate(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        response = generate_with_context(message.chat.id, message.text)

        # Безопасная отправка длинных сообщений
        if len(response) > 4000:
            for x in range(0, len(response), 4000):
                bot.send_message(message.chat.id, response[x:x+4000])
        else:
            bot.send_message(message.chat.id, response, parse_mode='Markdown')
    except Exception as e:
        bot.send_message(message.chat.id, "Бот столкнулся с технической проблемой.")
        print(f"Telegram Error: {e}")

bot.infinity_polling()
