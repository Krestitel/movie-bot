import telebot
from flask import Flask, request
import requests
import os
from datetime import datetime

# ============================================
# КОНФИГУРАЦИЯ
# ============================================

BOT_TOKEN = "8767537651:AAGdYZ3_CtyMjUJwy_vF4aT_5UH1HMEqyO4"
TMDB_API_KEY = "c93a533c091791e717d708cc88983e19"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ============================================
# ФУНКЦИИ TMDB API
# ============================================

def get_movie_details(movie_id, media_type="movie"):
    """Получение информации о фильме/сериале"""
    if media_type == "movie":
        url = f"https://api.themoviedb.org/3/movie/{movie_id}"
    else:
        url = f"https://api.themoviedb.org/3/tv/{movie_id}"
    
    params = {"api_key": TMDB_API_KEY, "language": "ru-RU"}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "title": data.get('title', data.get('name', 'Неизвестно')),
                "year": data.get('release_date', data.get('first_air_date', ''))[:4],
                "rating": round(data.get('vote_average', 0), 1),
                "overview": data.get('overview', 'Нет описания')[:500],
                "genres": [g['name'] for g in data.get('genres', [])]
            }
    except Exception as e:
        print(f"Ошибка: {e}")
    return None

def search_movie(query):
    """Поиск фильма по названию"""
    url = "https://api.themoviedb.org/3/search/multi"
    params = {"api_key": TMDB_API_KEY, "query": query, "language": "ru-RU"}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data['results']:
                for item in data['results'][:5]:
                    if item['media_type'] in ['movie', 'tv']:
                        return item
    except Exception as e:
        print(f"Ошибка: {e}")
    return None

# ============================================
# ОБРАБОТЧИКИ КОМАНД
# ============================================

@bot.message_handler(commands=['start'])
def start_command(message):
    text = (
        "🎬 *Movie Finder Bot*\n\n"
        "Я ищу фильмы и сериалы через TMDB API.\n\n"
        "📝 *Как пользоваться:*\n"
        "   • Просто введи название фильма\n"
        "   • Или используй команду /info <название>\n\n"
        "🐍 Бот работает 24/7 на Render.com"
    )
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(commands=['help'])
def help_command(message):
    text = "❓ Введи название фильма или сериала, и я покажу информацию о нём!"
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['info'])
def info_command(message):
    query = message.text.replace('/info', '').strip()
    if not query:
        bot.send_message(message.chat.id, "❓ Используй: /info <название>\nПример: /info Дэдпул")
        return
    
    bot.send_message(message.chat.id, f"🔍 Ищу '{query}'...")
    
    movie = search_movie(query)
    if movie:
        details = get_movie_details(movie['id'], movie['media_type'])
        if details:
            text = f"🎬 *{details['title']}* ({details['year']})\n"
            text += f"⭐ *Рейтинг:* {details['rating']}/10\n"
            if details.get('genres'):
                text += f"🎭 *Жанры:* {', '.join(details['genres'][:3])}\n"
            text += f"\n📝 {details['overview']}..."
            bot.send_message(message.chat.id, text, parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, "😔 Не удалось получить информацию о фильме")
    else:
        bot.send_message(message.chat.id, f"😔 Не найден фильм '{query}'")

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    text = message.text.strip()
    if text.startswith('/') or len(text) < 3 or len(text) > 100:
        return
    
    bot.send_message(message.chat.id, f"🔍 Ищу '{text}'...")
    
    movie = search_movie(text)
    if movie:
        details = get_movie_details(movie['id'], movie['media_type'])
        if details:
            response = f"🎬 *{details['title']}* ({details['year']})\n"
            response += f"⭐ *Рейтинг:* {details['rating']}/10\n"
            if details.get('genres'):
                response += f"🎭 *Жанры:* {', '.join(details['genres'][:3])}\n"
            response += f"\n📝 {details['overview']}..."
            bot.send_message(message.chat.id, response, parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, "😔 Ошибка получения данных")
    else:
        bot.send_message(message.chat.id, f"😔 Фильм '{text}' не найден")

# ============================================
# WEBHOOK ДЛЯ RENDER
# ============================================

@app.route(f"/{BOT_TOKEN}", methods=['POST'])
def webhook():
    try:
        update = telebot.types.Update.de_json(request.get_data().decode('UTF-8'))
        bot.process_new_updates([update])
        return "ok", 200
    except Exception as e:
        print(f"Webhook error: {e}")
        return "error", 500

@app.route("/", methods=['GET'])
def index():
    return "🤖 Movie Finder Bot is running on Render!"

def setup_webhook():
    """Установка вебхука при запуске"""
    try:
        bot.remove_webhook()
        webhook_url = f"https://movie-bot.onrender.com/{BOT_TOKEN}"
        bot.set_webhook(url=webhook_url)
        print(f"✅ Webhook установлен: {webhook_url}")
    except Exception as e:
        print(f"Webhook error: {e}")

if __name__ == "__main__":
    setup_webhook()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
