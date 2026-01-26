import requests
import telebot

from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv('WEATHER_TOKEN')
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')


bot = telebot.TeleBot(TOKEN)

def get_weather(city):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric&lang=ru"

    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        sea_level = data['main']['temp'] - 273.15
        grnd_level = data['main']['feels_like'] - 273.15
        temp_min = data['main']['temp_min']
        temp_max = data['main']['temp_max']
        country = data['sys']['country']
        temp = data['main']['temp']
        humidity = data['main']['humidity']
        wind_speed = data['wind']['speed']
        weather_description = data['weather'][0]['description']

        return (f'Погода в {city.capitalize()}\n'
                f'Темпратура - {temp} C\n'
                f'Влажност - {humidity} %\n'
                f'Скорость ветра - {wind_speed} km/h\n'
                f'Описание - {weather_description}\n'
                f'Страна - {country}\n'
                f'Темпратура макс и мин - {temp_min + temp_max} C\n'
                f'Уровень моря {sea_level}\n'
                f'Уровен земля - {grnd_level}\n')

    elif response.status_code == 404:
        return 'Такого города нет'

    else:
        return f'Ошибка - {response.status_code}, {response.json().get("message")}'

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.send_message(message.chat.id, f'Привет, напиши /weather <город>')

@bot.message_handler(commands=['weather'])
def weather(message):
    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        bot.send_message(message, 'Веедите город, /weather <город>')
    else:
        city = args[1]
        weather_info = get_weather(city)
        bot.send_message(message.chat.id, weather_info)

bot.infinity_polling()
