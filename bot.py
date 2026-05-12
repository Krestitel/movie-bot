import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from flask import Flask, request
import requests
import json
import random
import os
from datetime import datetime

# ============================================
# КОНФИГУРАЦИЯ
# ============================================

BOT_TOKEN = "8767537651:AAGmhRwLcDpkijAHj_b6frhCynZrD09Qwic"
TMDB_API_KEY = "c93a533c091791e717d708cc88983e19"

# Создаём папку для логов
LOG_DIR = "/var/data/logs"  # На Render будет доступна эта папка
os.makedirs(LOG_DIR, exist_ok=True)

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN)

# ============================================
# ДАННЫЕ ДЛЯ КЛАВИАТУР
# ============================================

GENRES = {
    "comedy": {"name": "🎭 Комедия", "id": 35},
    "horror": {"name": "😱 Хоррор", "id": 27},
    "action": {"name": "🔫 Боевик", "id": 28},
    "drama": {"name": "🎭 Драма", "id": 18},
    "crime": {"name": "🕵️ Детектив", "id": 9648},
    "sci_fi": {"name": "🚀 Фантастика", "id": 878},
    "thriller": {"name": "🗡️ Триллер", "id": 53},
    "romance": {"name": "💕 Мелодрама", "id": 10749},
    "history": {"name": "📜 История", "id": 36}
}

COUNTRIES = {
    "russia": {"name": "🇷🇺 Россия", "code": "RU"},
    "usa": {"name": "🇺🇸 США", "code": "US"},
    "uk": {"name": "🇬🇧 Великобритания", "code": "GB"},
    "france": {"name": "🇫🇷 Франция", "code": "FR"},
    "germany": {"name": "🇩🇪 Германия", "code": "DE"},
    "japan": {"name": "🇯🇵 Япония", "code": "JP"},
    "korea": {"name": "🇰🇷 Корея", "code": "KR"},
    "any": {"name": "🌍 Любая страна", "code": None}
}

RATINGS = [
    {"name": "⭐ Любой", "id": 0},
    {"name": "⭐ 5+", "id": 5},
    {"name": "⭐ 6+", "id": 6},
    {"name": "⭐ 7+", "id": 7},
    {"name": "⭐ 8+", "id": 8},
    {"name": "⭐ 9+", "id": 9}
]

YEARS = ["Любой"] + [str(y) for y in range(2025, 2014, -1)]

# ============================================
# КЛАВИАТУРЫ
# ============================================

def get_main_keyboard():
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        KeyboardButton("🔍 Поиск"),
        KeyboardButton("🎲 Случайный фильм"),
        KeyboardButton("🏆 Топ фильмов"),
        KeyboardButton("⭐ Избранное"),
        KeyboardButton("📜 История"),
        KeyboardButton("❓ Помощь")
    )
    return markup

def get_genre_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    for key, genre in GENRES.items():
        markup.add(InlineKeyboardButton(genre["name"], callback_data=f"genre_{key}"))
    return markup

def get_country_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    for key, country in COUNTRIES.items():
        markup.add(InlineKeyboardButton(country["name"], callback_data=f"country_{key}"))
    return markup

def get_rating_keyboard():
    markup = InlineKeyboardMarkup(row_width=3)
    for rating in RATINGS:
        markup.add(InlineKeyboardButton(rating["name"], callback_data=f"rating_{rating['id']}"))
    return markup

def get_year_keyboard():
    markup = InlineKeyboardMarkup(row_width=4)
    for year in YEARS:
        markup.add(InlineKeyboardButton(year, callback_data=f"year_{year}"))
    return markup

def get_media_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🎬 Фильмы", callback_data="media_movie"),
        InlineKeyboardButton("📺 Сериалы", callback_data="media_tv"),
        InlineKeyboardButton("🎬🎬 И то и другое", callback_data="media_both")
    )
    return markup

def get_movie_action_keyboard(movie_id, media_type):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("❤️ В избранное", callback_data=f"fav_{media_type}_{movie_id}"),
        InlineKeyboardButton("🎲 Похожие", callback_data=f"similar_{media_type}_{movie_id}")
    )
    return markup

# ============================================
# ЛОГИРОВАНИЕ
# ============================================

def log_message(user_id, user_message, bot_response):
    try:
        with open(f"{LOG_DIR}/{user_id}.log", "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] USER: {user_message}\n")
            f.write(f"[{timestamp}] BOT: {bot_response}\n")
            f.write("-" * 50 + "\n")
    except:
        pass

# ============================================
# TMDB API ФУНКЦИИ
# ============================================

def get_movie_details(movie_id, media_type="movie"):
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
                "id": data['id'],
                "title": data.get('title', data.get('name', 'Неизвестно')),
                "original_title": data.get('original_title', data.get('original_name', 'Неизвестно')),
                "year": data.get('release_date', data.get('first_air_date', ''))[:4],
                "rating": round(data.get('vote_average', 0), 1),
                "votes": data.get('vote_count', 0),
                "overview": data.get('overview', 'Нет описания')[:500],
                "poster": f"https://image.tmdb.org/t/p/w500{data['poster_path']}" if data.get('poster_path') else None,
                "genres": [g['name'] for g in data.get('genres', [])],
                "media_type": media_type
            }
    except:
        pass
    return None

def search_by_title(query, media_type=None):
    if media_type == "movie":
        url = "https://api.themoviedb.org/3/search/movie"
    elif media_type == "tv":
        url = "https://api.themoviedb.org/3/search/tv"
    else:
        url = "https://api.themoviedb.org/3/search/multi"
    
    params = {"api_key": TMDB_API_KEY, "query": query, "language": "ru-RU"}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data['results'][:5]:
                media = item.get('media_type', 'movie')
                results.append({
                    "id": item['id'],
                    "title": item.get('title', item.get('name', 'Неизвестно')),
                    "year": item.get('release_date', item.get('first_air_date', ''))[:4],
                    "rating": round(item.get('vote_average', 0), 1),
                    "media_type": media
                })
            return results
    except:
        pass
    return []

def search_by_filters(genre_id, media_type="movie", year=None, rating_min=0, country_code=None, limit=10):
    if media_type == "both":
        movie_results = search_by_filters(genre_id, "movie", year, rating_min, country_code, limit//2)
        tv_results = search_by_filters(genre_id, "tv", year, rating_min, country_code, limit//2)
        return movie_results + tv_results
    
    if media_type == "movie":
        url = "https://api.themoviedb.org/3/discover/movie"
    else:
        url = "https://api.themoviedb.org/3/discover/tv"
    
    params = {
        "api_key": TMDB_API_KEY,
        "with_genres": genre_id,
        "sort_by": "popularity.desc",
        "vote_average.gte": rating_min,
        "language": "ru-RU",
        "page": 1
    }
    
    if year and year != "Любой":
        if media_type == "movie":
            params["primary_release_year"] = year
        else:
            params["first_air_date_year"] = year
    
    if country_code:
        params["with_origin_country"] = country_code
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data['results'][:limit]:
                results.append({
                    "id": item['id'],
                    "title": item.get('title', item.get('name', 'Неизвестно')),
                    "year": item.get('release_date', item.get('first_air_date', ''))[:4],
                    "rating": round(item.get('vote_average', 0), 1),
                    "overview": item.get('overview', 'Нет описания')[:200],
                    "poster": f"https://image.tmdb.org/t/p/w500{item['poster_path']}" if item.get('poster_path') else None,
                    "media_type": media_type
                })
            return results
    except:
        pass
    return []

def get_top_movies(media_type="movie", limit=10):
    if media_type == "movie":
        url = "https://api.themoviedb.org/3/movie/top_rated"
    else:
        url = "https://api.themoviedb.org/3/tv/top_rated"
    
    params = {"api_key": TMDB_API_KEY, "language": "ru-RU"}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data['results'][:limit]:
                results.append({
                    "id": item['id'],
                    "title": item.get('title', item.get('name', 'Неизвестно')),
                    "year": item.get('release_date', item.get('first_air_date', ''))[:4],
                    "rating": round(item.get('vote_average', 0), 1),
                    "overview": item.get('overview', 'Нет описания')[:200],
                    "poster": f"https://image.tmdb.org/t/p/w500{item['poster_path']}" if item.get('poster_path') else None,
                    "media_type": media_type
                })
            return results
    except:
        pass
    return []

def get_random_movie(genre_id=None):
    url = "https://api.themoviedb.org/3/discover/movie"
    params = {"api_key": TMDB_API_KEY, "language": "ru-RU", "page": random.randint(1, 10)}
    if genre_id:
        params["with_genres"] = genre_id
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data['results']:
                item = random.choice(data['results'])
                return {
                    "id": item['id'],
                    "title": item.get('title', 'Неизвестно'),
                    "year": item.get('release_date', '')[:4],
                    "rating": round(item.get('vote_average', 0), 1),
                    "overview": item.get('overview', 'Нет описания')[:300],
                    "poster": f"https://image.tmdb.org/t/p/w500{item['poster_path']}" if item.get('poster_path') else None
                }
    except:
        pass
    return None

def get_similar_movies(movie_id, media_type="movie", limit=5):
    if media_type == "movie":
        url = f"https://api.themoviedb.org/3/movie/{movie_id}/similar"
    else:
        url = f"https://api.themoviedb.org/3/tv/{movie_id}/similar"
    
    params = {"api_key": TMDB_API_KEY, "language": "ru-RU"}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data['results'][:limit]:
                results.append({
                    "id": item['id'],
                    "title": item.get('title', item.get('name', 'Неизвестно')),
                    "year": item.get('release_date', item.get('first_air_date', ''))[:4],
                    "rating": round(item.get('vote_average', 0), 1),
                    "overview": item.get('overview', 'Нет описания')[:150],
                    "media_type": media_type
                })
            return results
    except:
        pass
    return []

# ============================================
# ХРАНЕНИЕ ДАННЫХ ПОЛЬЗОВАТЕЛЕЙ (избранное, история, контекст)
# ============================================

def load_user_data(user_id):
    try:
        with open(f"{LOG_DIR}/{user_id}_data.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"favorites": [], "history": [], "search_context": {}}

def save_user_data(user_id, data):
    with open(f"{LOG_DIR}/{user_id}_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_to_favorites(user_id, movie):
    data = load_user_data(user_id)
    for fav in data["favorites"]:
        if fav["id"] == movie["id"]:
            return False
    data["favorites"].append({
        "id": movie["id"],
        "title": movie["title"],
        "year": movie.get("year", ""),
        "rating": movie.get("rating", 0),
        "media_type": movie.get("media_type", "movie")
    })
    save_user_data(user_id, data)
    return True

def add_to_history(user_id, query, results_count):
    data = load_user_data(user_id)
    data["history"].insert(0, {"query": query, "results": results_count, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    data["history"] = data["history"][:20]
    save_user_data(user_id, data)

# ============================================
# ОБРАБОТЧИКИ КОМАНД
# ============================================

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.chat.id
    log_message(user_id, "/start", "Start")
    
    text = (
        "🎬 *Добро пожаловать в Movie Finder Bot!*\n\n"
        "🔍 *Поиск* - фильмы по жанру, стране, году, рейтингу\n"
        "🎲 *Случайный фильм* - случайный фильм\n"
        "🏆 *Топ фильмов* - лучшие фильмы\n"
        "⭐ *Избранное* - сохранённые фильмы\n"
        "📜 *История* - последние поиски\n\n"
        "📝 *Команды:* /info Название, /similar Название"
    )
    bot.send_message(user_id, text, parse_mode='Markdown', reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda m: m.text == "🔍 Поиск")
def search_start(message):
    user_id = message.chat.id
    data = load_user_data(user_id)
    data["search_context"] = {"step": "media_type"}
    save_user_data(user_id, data)
    bot.send_message(user_id, "Выбери тип контента:", reply_markup=get_media_keyboard())

@bot.message_handler(func=lambda m: m.text == "🎲 Случайный фильм")
def random_movie_start(message):
    markup = InlineKeyboardMarkup(row_width=2)
    for key, genre in GENRES.items():
        markup.add(InlineKeyboardButton(genre["name"], callback_data=f"random_{key}"))
    markup.add(InlineKeyboardButton("🎲 Любой жанр", callback_data="random_any"))
    bot.send_message(message.chat.id, "Выбери жанр:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🏆 Топ фильмов")
def top_movies_start(message):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🎬 Топ фильмов", callback_data="top_movie"),
        InlineKeyboardButton("📺 Топ сериалов", callback_data="top_tv")
    )
    bot.send_message(message.chat.id, "Что хотите посмотреть?", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "⭐ Избранное")
def show_favorites(message):
    user_id = message.chat.id
    data = load_user_data(user_id)
    if not data["favorites"]:
        bot.send_message(user_id, "⭐ Избранное пусто")
        return
    text = "⭐ *Избранное:*\n\n"
    for i, m in enumerate(data["favorites"], 1):
        text += f"{i}. *{m['title']}* ({m['year']}) — ⭐ {m['rating']}\n"
    bot.send_message(user_id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "📜 История")
def show_history(message):
    user_id = message.chat.id
    data = load_user_data(user_id)
    if not data["history"]:
        bot.send_message(user_id, "📜 История пуста")
        return
    text = "📜 *История поисков:*\n\n"
    for i, h in enumerate(data["history"][:10], 1):
        text += f"{i}. {h['query']} — {h['results']} рез.\n"
    bot.send_message(user_id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "❓ Помощь")
def help_command(message):
    text = "❓ *Помощь:*\n\n🔍 Поиск — фильтры\n🎲 Случайный — random\n🏆 Топ — топ\n⭐ Избранное\n📜 История\n/info Название\n/similar Название"
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(commands=['info'])
def info_command(message):
    user_id = message.chat.id
    query = message.text.replace('/info', '').strip()
    if not query:
        bot.send_message(user_id, "❓ /info <название>")
        return
    bot.send_message(user_id, f"🔍 Ищу '{query}'...")
    results = search_by_title(query)
    if not results:
        bot.send_message(user_id, "😔 Не найдено")
        return
    if len(results) > 1:
        text = "🔍 *Найдено:*\n\n"
        markup = InlineKeyboardMarkup(row_width=1)
        for i, item in enumerate(results[:5], 1):
            text += f"{i}. {item['title']} ({item['year']}) — ⭐ {item['rating']}\n"
            markup.add(InlineKeyboardButton(f"{i}. {item['title']}", callback_data=f"show_{item['media_type']}_{item['id']}"))
        bot.send_message(user_id, text, parse_mode='Markdown', reply_markup=markup)
    else:
        send_movie_details(user_id, results[0]['id'], results[0]['media_type'])

@bot.message_handler(commands=['similar'])
def similar_command(message):
    user_id = message.chat.id
    query = message.text.replace('/similar', '').strip()
    if not query:
        bot.send_message(user_id, "❓ /similar <название>")
        return
    bot.send_message(user_id, f"🔍 Ищу похожие для '{query}'...")
    results = search_by_title(query)
    if not results:
        bot.send_message(user_id, "😔 Не найдено")
        return
    similar = get_similar_movies(results[0]['id'], results[0]['media_type'], 8)
    if similar:
        text = f"🎲 *Похожие на {results[0]['title']}:*\n\n"
        for i, m in enumerate(similar, 1):
            text += f"{i}. *{m['title']}* ({m['year']}) — ⭐ {m['rating']}\n"
        bot.send_message(user_id, text, parse_mode='Markdown')
    else:
        bot.send_message(user_id, "😔 Нет похожих")

def send_movie_details(user_id, movie_id, media_type):
    details = get_movie_details(movie_id, media_type)
    if not details:
        bot.send_message(user_id, "😔 Ошибка")
        return
    text = f"🎬 *{details['title']}* ({details['year']})\n⭐ Рейтинг: {details['rating']}\n🎭 Жанры: {', '.join(details['genres'][:3])}\n\n📝 {details['overview']}"
    markup = get_movie_action_keyboard(movie_id, media_type)
    if details.get('poster'):
        try:
            bot.send_photo(user_id, details['poster'], caption=text, parse_mode='Markdown', reply_markup=markup)
        except:
            bot.send_message(user_id, text, parse_mode='Markdown', reply_markup=markup)
    else:
        bot.send_message(user_id, text, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    text = message.text.strip()
    if text.startswith('/') or len(text) < 3:
        return
    bot.send_message(message.chat.id, f"🔍 Ищу '{text}'...")
    results = search_by_title(text)
    if results:
        if len(results) == 1:
            send_movie_details(message.chat.id, results[0]['id'], results[0]['media_type'])
        else:
            markup = InlineKeyboardMarkup(row_width=1)
            for i, item in enumerate(results[:5], 1):
                markup.add(InlineKeyboardButton(f"{i}. {item['title']} ({item['year']})", callback_data=f"show_{item['media_type']}_{item['id']}"))
            bot.send_message(message.chat.id, "🔍 Уточни:", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "😔 Не найдено")

# ============================================
# ОБРАБОТЧИКИ CALLBACK
# ============================================

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.message.chat.id
    data = call.data
    
    if data.startswith("show_"):
        parts = data.split("_")
        media_type = parts[1]
        movie_id = int(parts[2])
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        send_movie_details(user_id, movie_id, media_type)
        bot.answer_callback_query(call.id)
    
    elif data.startswith("media_"):
        media_type = data.split("_")[1]
        user_data = load_user_data(user_id)
        user_data["search_context"] = {"step": "country", "media_type": media_type}
        save_user_data(user_id, user_data)
        bot.edit_message_text("Выбери страну:", call.message.chat.id, call.message.message_id, reply_markup=get_country_keyboard())
    
    elif data.startswith("country_"):
        country_key = data.split("_")[1]
        user_data = load_user_data(user_id)
        if user_data.get("search_context", {}).get("step") == "country":
            user_data["search_context"]["country_name"] = COUNTRIES[country_key]["name"]
            user_data["search_context"]["country_code"] = COUNTRIES[country_key]["code"]
            user_data["search_context"]["step"] = "genre"
            save_user_data(user_id, user_data)
            bot.edit_message_text(f"Страна: {COUNTRIES[country_key]['name']}\n\nВыбери жанр:", call.message.chat.id, call.message.message_id, reply_markup=get_genre_keyboard())
    
    elif data.startswith("genre_"):
        genre_key = data.split("_")[1]
        user_data = load_user_data(user_id)
        if user_data.get("search_context", {}).get("step") in ["genre", "step"]:
            user_data["search_context"]["genre_id"] = GENRES[genre_key]["id"]
            user_data["search_context"]["genre_name"] = GENRES[genre_key]["name"]
            user_data["search_context"]["step"] = "rating"
            save_user_data(user_id, user_data)
            bot.edit_message_text(f"Жанр: {GENRES[genre_key]['name']}\n\nВыбери рейтинг:", call.message.chat.id, call.message.message_id, reply_markup=get_rating_keyboard())
    
    elif data.startswith("rating_"):
        rating = int(data.split("_")[1])
        user_data = load_user_data(user_id)
        if user_data.get("search_context", {}).get("step") == "rating":
            user_data["search_context"]["rating"] = rating
            user_data["search_context"]["step"] = "year"
            save_user_data(user_id, user_data)
            rating_text = "Любой" if rating == 0 else f"{rating}+"
            bot.edit_message_text(f"Рейтинг: {rating_text}\n\nВыбери год:", call.message.chat.id, call.message.message_id, reply_markup=get_year_keyboard())
    
    elif data.startswith("year_"):
        year = data.split("_")[1]
        user_data = load_user_data(user_id)
        context = user_data.get("search_context", {})
        
        genre_id = context.get("genre_id")
        rating = context.get("rating", 0)
        media_type = context.get("media_type", "movie")
        country_code = context.get("country_code")
        
        bot.edit_message_text("🔍 Ищу...", call.message.chat.id, call.message.message_id)
        
        results = search_by_filters(genre_id, media_type, year, rating, country_code, limit=10)
        add_to_history(user_id, f"{context.get('country_name', '')} {context.get('genre_name', '')} {year} {rating}+", len(results))
        
        if not results:
            bot.send_message(user_id, "😔 Ничего не найдено")
        else:
            for movie in results:
                text = f"🎬 *{movie['title']}* ({movie['year']})\n⭐ Рейтинг: {movie['rating']}"
                markup = get_movie_action_keyboard(movie['id'], movie['media_type'])
                if movie.get('poster'):
                    try:
                        bot.send_photo(user_id, movie['poster'], caption=text, parse_mode='Markdown', reply_markup=markup)
                    except:
                        bot.send_message(user_id, text, parse_mode='Markdown', reply_markup=markup)
                else:
                    bot.send_message(user_id, text, parse_mode='Markdown', reply_markup=markup)
            bot.send_message(user_id, "✅ Поиск завершён")
        
        user_data["search_context"] = {}
        save_user_data(user_id, user_data)
    
    elif data.startswith("random_"):
        if data == "random_any":
            genre_id = None
            genre_name = "любого жанра"
        else:
            genre_key = data.split("_")[1]
            genre_id = GENRES[genre_key]["id"]
            genre_name = GENRES[genre_key]["name"]
        
        bot.edit_message_text(f"🎲 Ищу {genre_name}...", call.message.chat.id, call.message.message_id)
        movie = get_random_movie(genre_id)
        if movie:
            text = f"🎲 *Случайный фильм {genre_name}:*\n\n🎬 *{movie['title']}* ({movie['year']})\n⭐ {movie['rating']}\n\n{movie['overview']}"
            markup = get_movie_action_keyboard(movie['id'], "movie")
            if movie.get('poster'):
                try:
                    bot.send_photo(user_id, movie['poster'], caption=text, parse_mode='Markdown', reply_markup=markup)
                except:
                    bot.send_message(user_id, text, parse_mode='Markdown', reply_markup=markup)
            else:
                bot.send_message(user_id, text, parse_mode='Markdown', reply_markup=markup)
        else:
            bot.send_message(user_id, "😔 Ошибка")
    
    elif data.startswith("top_"):
        media_type = data.split("_")[1]
        type_name = "фильмов" if media_type == "movie" else "сериалов"
        bot.edit_message_text(f"🏆 Загружаю топ {type_name}...", call.message.chat.id, call.message.message_id)
        results = get_top_movies(media_type, 15)
        if results:
            text = f"🏆 *Топ {len(results)} {type_name}:*\n\n"
            for i, m in enumerate(results, 1):
                text += f"{i}. *{m['title']}* ({m['year']}) — ⭐ {m['rating']}\n"
            bot.send_message(user_id, text, parse_mode='Markdown')
        else:
            bot.send_message(user_id, "😔 Ошибка")
    
    elif data.startswith("fav_"):
        parts = data.split("_")
        media_type = parts[1]
        movie_id = int(parts[2])
        details = get_movie_details(movie_id, media_type)
        if details:
            if add_to_favorites(user_id, details):
                bot.answer_callback_query(call.id, f"✅ {details['title']} в избранном!")
            else:
                bot.answer_callback_query(call.id, f"⚠️ Уже в избранном")
        else:
            bot.answer_callback_query(call.id, "❌ Ошибка")
    
    elif data.startswith("similar_"):
        parts = data.split("_")
        media_type = parts[1]
        movie_id = int(parts[2])
        similar = get_similar_movies(movie_id, media_type, 6)
        if similar:
            text = "🎲 *Похожие:*\n\n"
            for i, m in enumerate(similar, 1):
                text += f"{i}. *{m['title']}* ({m['year']}) — ⭐ {m['rating']}\n"
            bot.send_message(user_id, text, parse_mode='Markdown')
        else:
            bot.send_message(user_id, "😔 Нет похожих")
        bot.answer_callback_query(call.id)

# ============================================
# FLASK WEBHOOK ДЛЯ RENDER
# ============================================

@app.route(f"/{BOT_TOKEN}", methods=['POST'])
def webhook():
    try:
        update = telebot.types.Update.de_json(request.get_data().decode('UTF-8'))
        bot.process_new_updates([update])
        return "ok", 200
    except:
        return "error", 500

@app.route("/", methods=['GET'])
def index():
    return "🎬 Movie Finder Bot is running!"

def setup_webhook():
    try:
        bot.remove_webhook()
        webhook_url = f"https://movie-bot.onrender.com/{BOT_TOKEN}"
        bot.set_webhook(url=webhook_url)
        print(f"✅ Webhook set: {webhook_url}")
    except Exception as e:
        print(f"Webhook error: {e}")

if __name__ == "__main__":
    setup_webhook()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
