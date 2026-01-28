import telebot
from google import genai
from dotenv import load_dotenv
import os
import time
import threading
import logging
import sqlite3



load_dotenv()

GEMINI_KEY = os.getenv('MINI_KEY')
TELEGRAM_TOKEN = os.getenv('GRAM_TOKEN')


MODEL_NAME = "gemini-3-flash-preview"
MAX_CHARS = 8000
FLOOD_DELAY = 2

DB_PATH = "memory.db"



logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)



client = genai.Client(api_key=GEMINI_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

last_message_time = {}

SYSTEM_PROMPT_TEXT = (
    "Ты дружелюбный и умный Telegram-бот. "
    "Отвечай понятно, кратко и по делу."
)



conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.execute("PRAGMA journal_mode=WAL")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS memory (
    user_id INTEGER,
    role TEXT,
    content TEXT,
    ts INTEGER
)
""")
conn.commit()

db_lock = threading.Lock()

def save_message(user_id, role, content):
    with db_lock:
        cursor.execute(
            "INSERT INTO memory VALUES (?, ?, ?, ?)",
            (user_id, role, content, int(time.time()))
        )
        conn.commit()



def load_context(user_id):
    cursor.execute("""
        SELECT role, content FROM memory
        WHERE user_id = ?
        ORDER BY ts ASC
    """, (user_id,))

    rows = cursor.fetchall()
    context = []

    for role, content in rows:
        context.append({
            "role": role,
            "parts": [{"text": content}]
        })

    if not context:
        context.append({
            "role": "user",
            "parts": [{"text": SYSTEM_PROMPT_TEXT}]
        })

    return trim_context(context)


def clear_context(user_id):
    cursor.execute("DELETE FROM memory WHERE user_id = ?", (user_id,))
    conn.commit()




def is_spam(user_id):
    now = time.time()
    if now - last_message_time.get(user_id, 0) < FLOOD_DELAY:
        return True
    last_message_time[user_id] = now
    return False


def trim_context(context):
    total = 0
    trimmed = []

    for msg in reversed(context):
        text = msg["parts"][0]["text"]
        total += len(text)
        if total > MAX_CHARS:
            break
        trimmed.insert(0, msg)

    return trimmed


import threading

def typing(chat_id, stop_event):
    while not stop_event.is_set():
        try:
            bot.send_chat_action(chat_id, "typing")
            stop_event.wait(2)
        except:
            break



def generate_with_context(user_id, text):
    context = load_context(user_id)

    context.append({
        "role": "user",
        "parts": [{"text": text}]
    })

    save_message(user_id, "user", text)

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=context
        )

        if not response.text:
            return " Я не смог ответить."

        save_message(user_id, "model", response.text)

        return response.text

    except Exception:
        logging.error("Gemini API error", exc_info=True)
        clear_context(user_id)
        return " Ошибка. Контекст был сброшен."




@bot.message_handler(commands=["start", "clear"])
def start_cmd(message):
    clear_context(message.chat.id)
    bot.reply_to(message, "Память очищена. Начнём заново?")



@bot.message_handler(commands=["help"])
def help_cmd(message):
    bot.reply_to(
        message,
        "/start – начать заново\n"
        "/clear – очистить память\n"
        "/help – помощь\n\n"
        "Просто пиши сообщение "
    )




@bot.message_handler(func=lambda m: True)
def main_handler(message):
    if is_spam(message.chat.id):
        return

    t = threading.Thread(
        target=typing,
        args=(message.chat.id,),
        daemon=True
    )
    t.start()

    try:
        response = generate_with_context(message.chat.id, message.text)

        if len(response) > 4000:
            for i in range(0, len(response), 4000):
                bot.send_message(message.chat.id, response[i:i + 4000])
        else:
            bot.send_message(message.chat.id, response)


    except Exception:
        logging.error("Telegram error", exc_info=True)
        bot.send_message(message.chat.id, " Техническая ошибка")




logging.info(" Bot started (SQLite + scalable)")
bot.infinity_polling()
