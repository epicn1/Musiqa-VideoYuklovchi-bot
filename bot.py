import asyncio
import os
import uuid
import re
import logging
from html import escape
from io import BytesIO
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import yt_dlp
from shazamio import Shazam
import logging
from dotenv import load_dotenv
import database
from aiogram import BaseMiddleware
from aiohttp import web

load_dotenv()

# Loglarni sozlash
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== SOZLAMALAR ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNELS = os.getenv("CHANNELS", "").split(",") if os.getenv("CHANNELS") else []
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]

# ========== TILLAR ==========
TEXTS = {
    'uz': {
        'welcome': "👋 Assalomu alaykum {user}!\n\nBotga hush kelibsiz!\n\n🌐 Iltimos, tilni tanlang:",
        'check_sub': "📢 Iltimos, botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:",
        'check_button': "✅ Tekshirish",
        'not_subscribed': "❌ Siz hali kanallarga obuna bo'lmadingiz!\n\nIltimos, avval kanallarga obuna bo'ling va qayta tekshiring.",
        'processing': "⏳ Qidirilmoqda...",
        'downloading': "⬇️ Yuklanmoqda...",
        'recognizing': "🎵 Qo'shiq aniqlanmoqda...",
        'song_found': "🎵 <b>Topilgan qo'shiq:</b>\n\n🎤 Ijrochi: <b>{artist}</b>\n📀 Nomi: <b>{title}</b>",
        'downloading_full': "⏳ To'liq versiyasi yuklanmoqda...",
        'song_not_found': "❌ Kechirasiz, qo'shiqni aniqlay olmadim.",
        'error': "❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.",
        'invalid_url': "❌ Noto'g'ri havola yuborildi yoki yuklab bo'lmadi.",
        'unsupported_url': "❌ Faqat Instagram, Facebook, Pinterest, Snapchat, YouTube va TikTok havolalarini yuboring.",
        'link_expired': "❌ Havola eskirgan, videoni qaytadan yuboring.",
        'search_expired': "❌ Qidiruv natijalari eskirgan, boshqadan qidiring.",
        'no_results': "❌ Hech narsa topilmadi. Boshqacha yozib ko'ring.",
        'main_menu': "👋 Assalomu alaykum {user}!\n\n🎵 Men musiqa botiman! Quyidagilarni qila olaman:\n\n🔗 <b>Havola yuboring</b> — YouTube'dan faqat qo'shiq/audio, Instagram, TikTok, Facebook, Pinterest, Snapchat'dan video yuklab beraman\n🎧 <b>Audioni yuklash</b> — videodagi ovozni to'liq uzunligida yuklab beraman\n🎶 <b>Musiqasini yuklash</b> — videodagi orqa fon musiqasini Shazam orqali topib yuklab beraman\n🔍 <b>Qo'shiq nomi yoki ijrochi</b> yozib yuboring — topib yuklab beraman\n🎤 <b>Ovozli xabar</b> yuboring — qo'shiqni tanib topaman\n📹 <b>Video</b> yuboring — ichidagi qo'shiqni aniqlayman",
        'change_lang': "🌐 Tilni o'zgartirish",
        'lang_changed': "✅ Til muvaffaqiyatli o'zgartirildi!",
        'btn_audio': "🎧 Videodagi audioni yuklash",
        'btn_music': "🎶 Videodagi musiqani yuklash",
        'no_url_found': "❌ Qo'shiqni yuklab bo'lmadi.",
        'video_too_large': "❌ Video hajmi juda katta (50 MB dan oshadi). Audio yuklashga urinib ko'ring.",
        'downloading_video': "⬇️ Video yuklanmoqda... Iltimos kuting.",
        'downloading_audio': "⬇️ Audio yuklanmoqda...",
        'search_results': "🔍 <b>{query}</b> uchun natijalar:\n\n",
        'select_number': "Yuklab olish uchun raqamni bosing 👆",
        'song_info': "🎵 <b>{artist}</b> — <b>{title}</b>\n🎼 <i>{snippet}</i>",
    },
    'ru': {
        'welcome': "👋 Здравствуйте {user}!\n\nДобро пожаловать в бот!\n\n🌐 Пожалуйста, выберите язык:",
        'check_sub': "📢 Пожалуйста, подпишитесь на следующие каналы для использования бота:",
        'check_button': "✅ Проверить",
        'not_subscribed': "❌ Вы еще не подписались!\n\nПожалуйста, сначала подпишитесь и проверьте снова.",
        'processing': "⏳ Поиск...",
        'downloading': "⬇️ Загрузка...",
        'recognizing': "🎵 Распознавание песни...",
        'song_found': "🎵 <b>Найденная песня:</b>\n\n🎤 Исполнитель: <b>{artist}</b>\n📀 Название: <b>{title}</b>",
        'downloading_full': "⏳ Загрузка полной версии...",
        'song_not_found': "❌ Извините, не удалось распознать песню.",
        'error': "❌ Произошла ошибка. Попробуйте снова.",
        'invalid_url': "❌ Неверная ссылка или не удалось скачать.",
        'unsupported_url': "❌ Отправьте ссылку только из Instagram, Facebook, Pinterest, Snapchat, YouTube или TikTok.",
        'link_expired': "❌ Ссылка устарела, отправьте видео снова.",
        'search_expired': "❌ Результаты поиска устарели, ищите снова.",
        'no_results': "❌ Ничего не найдено. Попробуйте иначе.",
        'main_menu': "👋 Здравствуйте {user}!\n\n🎵 Я музыкальный бот! Вот что я умею:\n\n🔗 <b>Отправьте ссылку</b> — с YouTube скачаю только песню/аудио, с Instagram, TikTok, Facebook, Pinterest, Snapchat скачаю видео\n🎧 <b>Скачать аудио</b> — скачаю полный звук из видео\n🎶 <b>Скачать музыку</b> — найду фоновую музыку через Shazam и скачаю\n🔍 <b>Напишите название</b> песни или исполнителя — найду и скачаю\n🎤 <b>Голосовое</b> — распознаю песню\n📹 <b>Видео</b> — определю музыку",
        'change_lang': "🌐 Изменить язык",
        'lang_changed': "✅ Язык успешно изменён!",
        'btn_audio': "🎧 Скачать аудио из видео",
        'btn_music': "🎶 Скачать музыку из видео",
        'no_url_found': "❌ Не удалось скачать песню.",
        'video_too_large': "❌ Видео слишком большое (>50 МБ). Попробуйте скачать аудио.",
        'downloading_video': "⬇️ Загрузка видео... Пожалуйста подождите.",
        'downloading_audio': "⬇️ Загрузка аудио...",
        'search_results': "🔍 <b>{query}</b> — результаты:\n\n",
        'select_number': "Нажмите цифру для скачивания 👆",
        'song_info': "🎵 <b>{artist}</b> — <b>{title}</b>\n🎼 <i>{snippet}</i>",
    },
    'en': {
        'welcome': "👋 Hello {user}!\n\nWelcome to the bot!\n\n🌐 Please select a language:",
        'check_sub': "📢 Please subscribe to the following channels to use the bot:",
        'check_button': "✅ Check",
        'not_subscribed': "❌ You haven't subscribed yet!\n\nPlease subscribe first and check again.",
        'processing': "⏳ Searching...",
        'downloading': "⬇️ Downloading...",
        'recognizing': "🎵 Recognizing song...",
        'song_found': "🎵 <b>Found song:</b>\n\n🎤 Artist: <b>{artist}</b>\n📀 Title: <b>{title}</b>",
        'downloading_full': "⏳ Downloading full version...",
        'song_not_found': "❌ Sorry, couldn't identify the song.",
        'error': "❌ An error occurred. Try again.",
        'invalid_url': "❌ Invalid link or couldn't download.",
        'unsupported_url': "❌ Send only Instagram, Facebook, Pinterest, Snapchat, YouTube, or TikTok links.",
        'link_expired': "❌ Link expired, please send the video again.",
        'search_expired': "❌ Search results expired, search again.",
        'no_results': "❌ Nothing found. Try a different search.",
        'main_menu': "👋 Hello {user}!\n\n🎵 I am a music bot! Here's what I can do:\n\n🔗 <b>Send a link</b> — from YouTube I download only song/audio, from Instagram, TikTok, Facebook, Pinterest, Snapchat I download video\n🎧 <b>Download audio</b> — full-length sound from video\n🎶 <b>Download music</b> — find background music via Shazam\n🔍 <b>Type a song name or artist</b> — I'll find and download it\n🎤 <b>Voice message</b> — I'll recognize the song\n📹 <b>Video</b> — I'll identify the music",
        'change_lang': "🌐 Change language",
        'lang_changed': "✅ Language changed successfully!",
        'btn_audio': "🎧 Download video audio",
        'btn_music': "🎶 Download music from video",
        'no_url_found': "❌ Couldn't download song.",
        'video_too_large': "❌ Video is too large (>50 MB). Try downloading audio instead.",
        'downloading_video': "⬇️ Downloading video... Please wait.",
        'downloading_audio': "⬇️ Downloading audio...",
        'search_results': "🔍 <b>{query}</b> results:\n\n",
        'select_number': "Tap a number to download 👆",
        'song_info': "🎵 <b>{artist}</b> — <b>{title}</b>\n🎼 <i>{snippet}</i>",
    }
}

# ========== FSM States ==========
class UserState(StatesGroup):
    language = State()
    main_menu = State()

# ========== Bot ==========
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
shazam = Shazam()

# ========== Cache ==========
user_languages_cache = {}
url_cache = {}
search_cache = {}

# ========== Middleware ==========
class CacheMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = event.from_user if hasattr(event, "from_user") else None
        if user:
            if user.id not in user_languages_cache:
                db_user = await database.get_user(user.id)
                user_languages_cache[user.id] = db_user.language if db_user else 'uz'
        return await handler(event, data)

router.message.middleware(CacheMiddleware())
router.callback_query.middleware(CacheMiddleware())

# ========== Yordamchi funksiyalar ==========
def get_text(user_id, key):
    lang = user_languages_cache.get(user_id, 'uz')
    return TEXTS[lang].get(key, TEXTS['uz'].get(key, ''))

def format_duration(seconds):
    if not seconds:
        return ""
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes}:{secs:02d}"

def html_escape(value):
    return escape(str(value or ""), quote=False)

def is_social_url(url):
    """Ijtimoiy tarmoq havolasini tekshirish"""
    patterns = [
        r'(youtube\.com|youtu\.be)',
        r'(instagram\.com)',
        r'(tiktok\.com)',
        r'(facebook\.com|fb\.com|fb\.watch)',
        r'(pinterest\.com|pin\.it)',
        r'(snapchat\.com|snap\.com)',
    ]
    for p in patterns:
        if re.search(p, url, re.IGNORECASE):
            return True
    return False

def music_search_query(query):
    """YouTube qidiruvini qo'shiq/audio natijalarga yo'naltirish."""
    query = (query or "").strip()
    music_words = r'\b(song|music|audio|official audio|lyrics|lyric|qo.?shiq|musiqa|песня|музыка)\b'
    if re.search(music_words, query, re.IGNORECASE):
        return query
    return f"{query} song audio"

# ========== Klaviaturalar ==========
def language_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz"),
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")
    ]])

def change_language_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="change_lang_uz"),
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="change_lang_ru"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="change_lang_en")
    ]])

def main_menu_keyboard(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=get_text(user_id, 'change_lang'), callback_data="open_change_lang")
    ]])

def subscription_keyboard(user_id):
    buttons = []
    for channel in CHANNELS:
        buttons.append([InlineKeyboardButton(text=f"📢 {channel}", url=f"https://t.me/{channel[1:]}")])
    buttons.append([InlineKeyboardButton(text=get_text(user_id, 'check_button'), callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def extract_platform(url):
    """URL dan platformani aniqlash"""
    if re.search(r'(youtube\.com|youtu\.be)', url, re.IGNORECASE):
        return 'youtube'
    if re.search(r'(instagram\.com)', url, re.IGNORECASE):
        return 'instagram'
    if re.search(r'(tiktok\.com)', url, re.IGNORECASE):
        return 'tiktok'
    if re.search(r'(facebook\.com|fb\.com|fb\.watch)', url, re.IGNORECASE):
        return 'facebook'
    if re.search(r'(pinterest\.com|pin\.it)', url, re.IGNORECASE):
        return 'pinterest'
    if re.search(r'(snapchat\.com|snap\.com)', url, re.IGNORECASE):
        return 'snapchat'
    return None

# ========== Klaviaturalar ==========
def video_action_keyboard(user_id, video_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(user_id, 'btn_music'), callback_data=f"getmusic_{video_id}")],
        [InlineKeyboardButton(text=get_text(user_id, 'btn_audio'), callback_data=f"getaudio_{video_id}")],
    ])

def audio_only_keyboard(user_id, video_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(user_id, 'btn_audio'), callback_data=f"getaudio_{video_id}")],
    ])

# ========== Obuna tekshirish ==========
async def check_subscription(user_id):
    if user_id in ADMIN_IDS:
        return True
    for channel in CHANNELS:
        try:
            channel_username = channel if channel.startswith('@') else f"@{channel}"
            member = await bot.get_chat_member(chat_id=channel_username, user_id=user_id)
            if member.status in ['left', 'kicked']:
                return False
        except Exception as e:
            logger.error(f"Subscription check error {channel}: {e}")
            continue
    return True

# ========== yt-dlp uchun umumiy sozlamalar ==========
def get_ydl_cookies_opts():
    """Cookie fayllari mavjud bo'lsa qo'shish"""
    opts = {}
    # Browser cookies — har bir platforma uchun
    # Agar cookies.txt fayli mavjud bo'lsa ishlatish
    if os.path.exists('cookies.txt'):
        opts['cookiefile'] = 'cookies.txt'
    return opts

# ========== Video yuklab olish ==========
async def download_video_from_url(url, user_id, audio_only=False):
    """Ijtimoiy tarmoqdan video/audio yuklab olish"""
    try:
        os.makedirs('downloads', exist_ok=True)
        temp_id = str(uuid.uuid4())[:8]
        is_youtube = extract_platform(url) == 'youtube'
        
        # YouTube uchun faqat audio
        if is_youtube:
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': f'downloads/{user_id}_{temp_id}.%(ext)s',
                'noplaylist': True,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'quiet': True,
                'no_warnings': True,
                'socket_timeout': 30,
                'retries': 3,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept-Language': 'en-US,en;q=0.9',
                },
            }
        else:
            # Boshqa platformalar uchun video
            ydl_opts = {
                'format': 'bestvideo[ext=mp4][filesize<45M]+bestaudio[ext=m4a]/best[ext=mp4][filesize<45M]/best[filesize<45M]/best',
                'outtmpl': f'downloads/{user_id}_{temp_id}.%(ext)s',
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
                'merge_output_format': 'mp4',
                'socket_timeout': 30,
                'retries': 3,
                'fragment_retries': 3,
                'extractor_args': {
                    'instagram': {'app_id': ''}
                },
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                },
            }
        
        if os.path.exists('cookies.txt'):
            ydl_opts['cookiefile'] = 'cookies.txt'

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info is None:
                    return None, None, None
                if is_youtube:
                    base = os.path.splitext(ydl.prepare_filename(info))[0]
                    filename = base + '.mp3'
                    if not os.path.exists(filename):
                        for f in os.listdir('downloads'):
                            if f.startswith(f'{user_id}_{temp_id}') and f.endswith('.mp3'):
                                filename = os.path.join('downloads', f)
                                break
                    title = info.get('title') or info.get('fulltitle') or 'Audio'
                    return filename, title, 'youtube'
                else:
                    if 'requested_downloads' in info and info['requested_downloads']:
                        filename = info['requested_downloads'][0].get('filepath', '')
                    else:
                        filename = ydl.prepare_filename(info)
                        if not os.path.exists(filename):
                            base = os.path.splitext(filename)[0]
                            for ext in ['.mp4', '.mkv', '.webm', '.mov']:
                                if os.path.exists(base + ext):
                                    filename = base + ext
                                    break
                    title = info.get('title') or info.get('fulltitle') or 'Video'
                    duration = info.get('duration', 0)
                    return filename, title, duration

        result = await asyncio.to_thread(_download)
        filename, title, extra = result
        
        if is_youtube and filename and os.path.exists(filename):
            return filename, title, None
            
        if filename and os.path.exists(filename):
            size = os.path.getsize(filename)
            if size > 49 * 1024 * 1024:
                os.remove(filename)
                return 'TOO_LARGE', title, None
            return filename, title, extra
        return None, None, None
    except Exception as e:
        logger.error(f"yt-dlp video error: {e}")
        return None, None, None

# ========== Duration bo'yicha audio yuklab olish ==========
async def download_audio_by_duration(url, duration_seconds, user_id):
    """Videoning audio qismini duration bo'yicha yuklab olish (FFmpeg bilan kesish)"""
    try:
        os.makedirs('downloads', exist_ok=True)
        temp_id = str(uuid.uuid4())[:8]
        
        # Avval video/audio yuklab olish
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'downloads/temp_{user_id}_{temp_id}.%(ext)s',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
            'retries': 3,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
            },
        }
        if os.path.exists('cookies.txt'):
            ydl_opts['cookiefile'] = 'cookies.txt'

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info is None:
                    return None, None
                base = os.path.splitext(ydl.prepare_filename(info))[0]
                filename = base
                for f in os.listdir('downloads'):
                    if f.startswith(f'temp_{user_id}_{temp_id}'):
                        filename = os.path.join('downloads', f)
                        ext = f.split('.')[-1] if '.' in f else 'mp3'
                        break
                title = info.get('title') or 'Audio'
                return filename, title

        temp_audio_path, title = await asyncio.to_thread(_download)
        
        if temp_audio_path and os.path.exists(temp_audio_path):
            # FFmpeg bilan duration bo'yicha kesish
            output_path = f'downloads/{user_id}_{temp_id}.mp3'
            import subprocess
            try:
                subprocess.run([
                    'ffmpeg', '-y', '-i', temp_audio_path,
                    '-t', str(duration_seconds),
                    '-vn', '-acodec', 'libmp3lame', '-b:a', '192k',
                    output_path
                ], check=True, capture_output=True)
                os.remove(temp_audio_path)
                return output_path, title
            except Exception as e:
                logger.error(f"FFmpeg cut error: {e}")
                # Kesish xatosa, asl audio ni qaytarish
                return temp_audio_path, title
        return None, None
    except Exception as e:
        logger.error(f"Duration audio download error: {e}")
        return None, None

# ========== Audio yuklab olish ==========
async def download_audio_from_url(url, user_id):
    """URL dan audio yuklab olish (MP3)"""
    try:
        os.makedirs('downloads', exist_ok=True)
        temp_id = str(uuid.uuid4())[:8]
        output_template = f'downloads/{user_id}_{temp_id}.%(ext)s'

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_template,
            'noplaylist': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
            'retries': 3,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
            },
        }
        if os.path.exists('cookies.txt'):
            ydl_opts['cookiefile'] = 'cookies.txt'

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info is None:
                    return None, None, None
                # .mp3 fayl nomi
                base = os.path.splitext(ydl.prepare_filename(info))[0]
                filename = base + '.mp3'
                if not os.path.exists(filename):
                    # downloads papkasidan qidirish
                    for f in os.listdir('downloads'):
                        if f.startswith(f'{user_id}_{temp_id}') and f.endswith('.mp3'):
                            filename = os.path.join('downloads', f)
                            break
                title = info.get('title') or 'Audio'
                uploader = info.get('artist') or info.get('uploader') or info.get('channel') or 'Unknown'
                return filename, title, uploader

        return await asyncio.to_thread(_download)
    except Exception as e:
        logger.error(f"yt-dlp audio error: {e}")
        return None, None, None

# ========== YouTube dan qo'shiq yuklab olish ==========
async def download_song_from_youtube(query, user_id):
    """YouTube qidiruvi orqali qo'shiq yuklab olish"""
    try:
        query = music_search_query(query)
        os.makedirs('downloads', exist_ok=True)
        temp_id = str(uuid.uuid4())[:8]

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'downloads/{user_id}_{temp_id}.%(ext)s',
            'noplaylist': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
            'retries': 3,
        }

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{query}", download=True)
                if not info:
                    return None, None, None
                if 'entries' in info and info['entries']:
                    info = info['entries'][0]
                base = os.path.splitext(ydl.prepare_filename(info))[0]
                filename = base + '.mp3'
                if not os.path.exists(filename):
                    for f in os.listdir('downloads'):
                        if f.startswith(f'{user_id}_{temp_id}') and f.endswith('.mp3'):
                            filename = os.path.join('downloads', f)
                            break
                title = info.get('title', 'Unknown')
                artist = info.get('artist') or info.get('uploader') or info.get('channel') or 'Unknown'
                return filename, title, artist

        return await asyncio.to_thread(_download)
    except Exception as e:
        logger.error(f"YouTube download error: {e}")
        return None, None, None

# ========== Shazam bilan aniqlash ==========
async def recognize_with_shazam(file_data: bytes):
    try:
        out = await shazam.recognize(file_data)
        if out and 'track' in out:
            track = out['track']
            # Lyrics snippet
            snippet = ""
            sections = track.get('sections', [])
            for sec in sections:
                if sec.get('type') == 'LYRICS' and sec.get('text'):
                    lines = [l for l in sec['text'] if l and l.strip()]
                    snippet = " / ".join(lines[:2])
                    break
            if not snippet:
                # urlparams dan snippet
                for sec in sections:
                    if sec.get('type') == 'SONG' and sec.get('metapages'):
                        pass
            return {
                'title': track.get('title', 'Unknown'),
                'artist': track.get('subtitle', 'Unknown'),
                'snippet': snippet,
            }
        return None
    except Exception as e:
        logger.error(f"Shazam error: {e}")
        return None

# ========== YouTube qidiruvi (matn uchun) ==========
async def search_youtube_tracks(query, limit=10):
    """YouTube dan qidiruv natijalari (yuklab olmaydi)"""
    try:
        query = music_search_query(query)
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'socket_timeout': 20,
        }

        def _search():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
                if not info or 'entries' not in info:
                    return []
                results = []
                for entry in info['entries']:
                    if entry:
                        title = entry.get('title', 'Unknown')
                        uploader = entry.get('uploader') or entry.get('channel') or ''
                        duration = entry.get('duration') or 0
                        video_id = entry.get('id', '')
                        results.append({
                            'title': title,
                            'uploader': uploader,
                            'duration': duration,
                            'video_id': video_id,
                            'url': f"https://www.youtube.com/watch?v={video_id}" if video_id else '',
                        })
                return results

        return await asyncio.to_thread(_search)
    except Exception as e:
        logger.error(f"YouTube search error: {e}")
        return []

# ========== Qo'shiq yuborish (Shazam topgandan keyin) ==========
async def send_recognized_song(message, song_info, user_id, processing_msg):
    """Shazam topgan qo'shiqni YouTube'dan yuklab yuborish"""
    artist = song_info['artist']
    title = song_info['title']
    snippet = song_info.get('snippet', '')

    # Xabarni yangilash
    found_text = get_text(user_id, 'song_found').format(artist=html_escape(artist), title=html_escape(title))
    if snippet:
        found_text += f"\n\n🎼 <i>{html_escape(snippet)}</i>"
    found_text += f"\n\n{get_text(user_id, 'downloading_full')}"

    try:
        await processing_msg.edit_text(found_text, parse_mode="HTML")
    except Exception:
        pass

    query = f"{artist} - {title}"
    audio_path, dl_title, dl_artist = await download_song_from_youtube(query, user_id)

    if audio_path and os.path.exists(audio_path):
        try:
            audio_file = FSInputFile(audio_path)
            caption = f"🎵 <b>{html_escape(artist)}</b> — <b>{html_escape(title)}</b>"
            if snippet:
                caption += f"\n🎼 <i>{html_escape(snippet)}</i>"
            await message.answer_audio(
                audio_file,
                title=title,
                performer=artist,
                caption=caption,
                parse_mode="HTML"
            )
            try:
                await processing_msg.delete()
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Send audio error: {e}")
            try:
                await processing_msg.edit_text(get_text(user_id, 'error'))
            except Exception:
                pass
        finally:
            try:
                os.remove(audio_path)
            except Exception:
                pass
    else:
        try:
            await processing_msg.edit_text(get_text(user_id, 'song_not_found'))
        except Exception:
            pass

# ========== Search UI ==========
def get_search_text(query, results, page, lang='uz'):
    limit = 10
    start = (page - 1) * limit
    end = start + limit
    page_results = results[start:end]
    text = f"<b>{html_escape(query)}</b>\n\n"
    for i, res in enumerate(page_results):
        duration = format_duration(res.get('duration'))
        title = html_escape(res.get('title', 'Unknown'))
        dur_text = f" <b>{html_escape(duration)}</b>" if duration else ""
        num = start + i + 1
        text += f"<b>{num}.</b> <i>{title}</i>{dur_text}\n"
    return text

def get_search_keyboard(page, total_results, search_id):
    limit = 10
    total_pages = (total_results + limit - 1) // limit
    buttons = []
    start_index = (page - 1) * limit
    row = []
    for i in range(min(limit, total_results - start_index)):
        absolute_index = start_index + i
        row.append(InlineKeyboardButton(text=str(absolute_index + 1), callback_data=f"dl_{search_id}_{absolute_index}"))
        if len(row) == 5:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="\u2b05\ufe0f", callback_data=f"page_{search_id}_{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="\u27a1\ufe0f", callback_data=f"page_{search_id}_{page+1}"))
    if nav_buttons:
        buttons.append(nav_buttons)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ========== START ==========
@router.message(CommandStart())
async def cmd_start(message, state: FSMContext):
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    if not await check_subscription(user_id):
        await message.answer(get_text(user_id, 'check_sub'), reply_markup=subscription_keyboard(user_id))
        return

    db_user = await database.get_user(user_id)
    if db_user and db_user.language:
        user_languages_cache[user_id] = db_user.language
        await message.answer(
            get_text(user_id, 'main_menu').format(user=user_name),
            reply_markup=main_menu_keyboard(user_id),
            parse_mode="HTML"
        )
        await state.set_state(UserState.main_menu)
    else:
        await message.answer(TEXTS['uz']['welcome'].format(user=user_name), reply_markup=language_keyboard())
        await state.set_state(UserState.language)

@router.callback_query(F.data.startswith("lang_"))
async def choose_language(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[1]
    user_id = callback.from_user.id
    user_name = callback.from_user.first_name
    await database.update_user_language(user_id, lang)
    user_languages_cache[user_id] = lang
    if await check_subscription(user_id):
        await callback.message.edit_text(
            get_text(user_id, 'main_menu').format(user=user_name),
            reply_markup=main_menu_keyboard(user_id),
            parse_mode="HTML"
        )
        await state.set_state(UserState.main_menu)
    else:
        await callback.message.edit_text(get_text(user_id, 'check_sub'), reply_markup=subscription_keyboard(user_id))
    await callback.answer()

@router.callback_query(F.data == "open_change_lang")
async def open_change_lang(callback: CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=change_language_keyboard())
    await callback.answer()

@router.callback_query(F.data.startswith("change_lang_"))
async def handle_change_language(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[2]
    user_id = callback.from_user.id
    user_name = callback.from_user.first_name
    await database.update_user_language(user_id, lang)
    user_languages_cache[user_id] = lang
    await callback.message.edit_text(
        get_text(user_id, 'main_menu').format(user=user_name),
        reply_markup=main_menu_keyboard(user_id),
        parse_mode="HTML"
    )
    await callback.answer(get_text(user_id, 'lang_changed'), show_alert=False)
    await state.set_state(UserState.main_menu)

@router.callback_query(F.data == "check_sub")
async def check_sub_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_name = callback.from_user.first_name
    if await check_subscription(user_id):
        db_user = await database.get_user(user_id)
        if db_user and db_user.language:
            user_languages_cache[user_id] = db_user.language
            await callback.message.edit_text(
                get_text(user_id, 'main_menu').format(user=user_name),
                reply_markup=main_menu_keyboard(user_id),
                parse_mode="HTML"
            )
            await state.set_state(UserState.main_menu)
        else:
            await callback.message.edit_text(TEXTS['uz']['welcome'].format(user=user_name), reply_markup=language_keyboard())
            await state.set_state(UserState.language)
    else:
        await callback.answer(get_text(user_id, 'not_subscribed'), show_alert=True)

# ========== URL (ijtimoiy tarmoq havolasi) ==========
@router.message(F.text & F.text.startswith(("http://", "https://")))
async def handle_url(message: Message):
    user_id = message.from_user.id
    if not await check_subscription(user_id):
        await message.answer(get_text(user_id, 'check_sub'), reply_markup=subscription_keyboard(user_id))
        return

    url = message.text.strip()
    if not is_social_url(url):
        await message.answer(get_text(user_id, 'unsupported_url'))
        return

    platform = extract_platform(url)
    processing_msg = await message.answer(get_text(user_id, 'downloading'))
    result_path = None

    try:
        # YouTube uchun faqat audio, boshqa platformalar uchun video
        if platform == 'youtube':
            result_path, title, _ = await download_video_from_url(url, user_id, audio_only=True)
            
            if result_path and result_path != 'TOO_LARGE' and os.path.exists(result_path):
                audio_id = str(uuid.uuid4())[:8]
                url_cache[audio_id] = {'url': url, 'duration': None, 'platform': 'youtube'}
                audio_file = FSInputFile(result_path)
                await message.answer_audio(
                    audio_file,
                    title=title,
                    performer='YouTube',
                    caption=f"🎵 <b>{html_escape(title)}</b>",
                    reply_markup=audio_only_keyboard(user_id, audio_id),
                    parse_mode="HTML"
                )
                await processing_msg.delete()
                try:
                    os.remove(result_path)
                except:
                    pass
            elif result_path == 'TOO_LARGE':
                await processing_msg.edit_text(get_text(user_id, 'video_too_large'))
            else:
                await processing_msg.edit_text(get_text(user_id, 'invalid_url'))
        else:
            # Instagram, TikTok, Facebook, Pinterest, Snapchat uchun video
            result_path, title, duration = await download_video_from_url(url, user_id, audio_only=False)

            if result_path == 'TOO_LARGE':
                await processing_msg.edit_text(get_text(user_id, 'video_too_large'))
                return

            if result_path and os.path.exists(result_path):
                video_id = str(uuid.uuid4())[:8]
                url_cache[video_id] = {'url': url, 'duration': duration, 'platform': platform}
                video_file = FSInputFile(result_path)
                try:
                    await message.answer_video(
                        video_file,
                        caption=f"🎬 <b>{html_escape(title)}</b>",
                        reply_markup=video_action_keyboard(user_id, video_id),
                        parse_mode="HTML"
                    )
                    await processing_msg.delete()
                except Exception as e:
                    logger.error(f"Send video error: {e}")
                    try:
                        await processing_msg.edit_text(get_text(user_id, 'downloading_audio'))
                        audio_path, a_title, a_uploader = await download_audio_from_url(url, user_id)
                        if audio_path and os.path.exists(audio_path):
                            audio_id = str(uuid.uuid4())[:8]
                            url_cache[audio_id] = {'url': url, 'duration': duration, 'platform': platform}
                            af = FSInputFile(audio_path)
                            await message.answer_audio(
                                af,
                                title=a_title,
                                performer=a_uploader,
                                caption=f"🎵 <b>{html_escape(a_title)}</b>",
                                reply_markup=video_action_keyboard(user_id, audio_id),
                                parse_mode="HTML"
                            )
                            await processing_msg.delete()
                            if os.path.exists(audio_path):
                                os.remove(audio_path)
                        else:
                            await processing_msg.edit_text(get_text(user_id, 'invalid_url'))
                    except Exception as e2:
                        logger.error(f"Fallback audio error: {e2}")
                        await processing_msg.edit_text(get_text(user_id, 'error'))
            else:
                await processing_msg.edit_text(get_text(user_id, 'invalid_url'))
    except Exception as e:
        logger.error(f"URL handler error: {e}")
        try:
            await processing_msg.edit_text(get_text(user_id, 'error'))
        except Exception:
            pass
    finally:
        if result_path and result_path != 'TOO_LARGE' and os.path.exists(str(result_path)):
            try:
                os.remove(result_path)
            except Exception:
                pass

# ========== Audioni yuklash ==========
@router.callback_query(F.data.startswith("getaudio_"))
async def process_audio_button(callback: CallbackQuery):
    user_id = callback.from_user.id
    video_id = callback.data[9:]
    if not await check_subscription(user_id):
        await callback.message.answer(get_text(user_id, 'check_sub'), reply_markup=subscription_keyboard(user_id))
        await callback.answer()
        return
    cached_data = url_cache.get(video_id)
    if not cached_data:
        await callback.answer(get_text(user_id, 'link_expired'), show_alert=True)
        return
    url = cached_data.get('url') or cached_data
    platform = cached_data.get('platform', '') if isinstance(cached_data, dict) else ''
    duration = cached_data.get('duration', 0) if isinstance(cached_data, dict) else 0
    await callback.answer()
    processing_msg = await callback.message.answer(get_text(user_id, 'downloading_audio'))
    audio_path = None
    try:
        if platform == 'youtube' or duration == 0:
            audio_path, title, uploader = await download_audio_from_url(url, user_id)
            if audio_path and os.path.exists(audio_path):
                audio_file = FSInputFile(audio_path)
                await callback.message.answer_audio(
                    audio_file,
                    title=title,
                    performer=uploader,
                    caption=f"🎧 <b>{html_escape(uploader)}</b> — {html_escape(title)}",
                    parse_mode="HTML"
                )
        else:
            # Boshqa platformalar uchun duration bo'yicha audio yuklash
            audio_path, title = await download_audio_by_duration(url, duration, user_id)
            if audio_path and os.path.exists(audio_path):
                mins = int(duration) // 60
                secs = int(duration) % 60
                dur_str = f"{mins}:{secs:02d}"
                uploader = platform.title() if platform else 'Video'
                
                audio_file = FSInputFile(audio_path)
                await callback.message.answer_audio(
                    audio_file,
                    title=title,
                    performer=uploader,
                    caption=f"🎵 <b>{html_escape(title)}</b> <i>({html_escape(dur_str)})</i>",
                    parse_mode="HTML"
                )
        if audio_path:
            try:
                await processing_msg.delete()
            except Exception:
                pass
            try:
                if os.path.exists(str(audio_path)):
                    os.remove(audio_path)
            except:
                pass
        else:
            await processing_msg.edit_text(get_text(user_id, 'error'))
    except Exception as e:
        logger.error(f"Audio download error: {e}")
        try:
            await processing_msg.edit_text(get_text(user_id, 'error'))
        except Exception:
            pass

# ========== Musiqasini yuklash (Shazam + YouTube) ==========
@router.callback_query(F.data.startswith("getmusic_"))
async def process_music_button(callback: CallbackQuery):
    user_id = callback.from_user.id
    video_id = callback.data[9:]
    if not await check_subscription(user_id):
        await callback.message.answer(get_text(user_id, 'check_sub'), reply_markup=subscription_keyboard(user_id))
        await callback.answer()
        return
    cached_data = url_cache.get(video_id)
    if not cached_data:
        await callback.answer(get_text(user_id, 'link_expired'), show_alert=True)
        return
    url = cached_data.get('url') or cached_data
    await callback.answer()
    processing_msg = await callback.message.answer(get_text(user_id, 'recognizing'))
    audio_path = None
    try:
        audio_path, title, uploader = await download_audio_from_url(url, user_id)
        if audio_path and os.path.exists(audio_path):
            with open(audio_path, 'rb') as f:
                file_data = f.read()
            song_info = await recognize_with_shazam(file_data)
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
                audio_path = None
            if song_info:
                await send_recognized_song(callback.message, song_info, user_id, processing_msg)
            else:
                # Shazam topa olmadi — videodagi audio (duration bo'yicha) yuklash
                await process_audio_button_fallback(callback, cached_data, user_id, processing_msg)
        else:
            await processing_msg.edit_text(get_text(user_id, 'error'))
    except Exception as e:
        logger.error(f"Music extraction error: {e}")
        try:
            await processing_msg.edit_text(get_text(user_id, 'error'))
        except Exception:
            pass
    finally:
        if audio_path and os.path.exists(str(audio_path)):
            try:
                os.remove(audio_path)
            except Exception:
                pass

async def process_audio_button_fallback(callback, cached_data, user_id, processing_msg):
    """Shazam topa olmasa, videodagi audio yuklab beradi (duration bo'yicha)"""
    try:
        url = cached_data['url']
        platform = cached_data.get('platform', '')
        duration = cached_data.get('duration', 0)
        
        await processing_msg.edit_text(get_text(user_id, 'downloading_audio'))
        
        if duration and duration > 0:
            # Duration bo'yicha audio yuklash
            audio_path, title = await download_audio_by_duration(url, duration, user_id)
            if audio_path and os.path.exists(audio_path):
                # Duration ni formatlash
                mins = int(duration) // 60
                secs = int(duration) % 60
                dur_str = f"{mins}:{secs:02d}"
                uploader = platform.title() if platform else 'Video'
                
                audio_file = FSInputFile(audio_path)
                await callback.message.answer_audio(
                    audio_file,
                    title=title,
                    performer=uploader,
                    caption=f"🎵 <b>{html_escape(title)}</b> <i>({html_escape(dur_str)})</i>",
                    parse_mode="HTML"
                )
                try:
                    os.remove(audio_path)
                except:
                    pass
                return
        
        # Duration bo'lmasa oddiy audio yuklash
        audio_path, title, uploader = await download_audio_from_url(url, user_id)
        if audio_path and os.path.exists(audio_path):
            audio_file = FSInputFile(audio_path)
            await callback.message.answer_audio(
                audio_file,
                title=title,
                performer=uploader,
                caption=f"🎧 <b>{html_escape(uploader)}</b> — {html_escape(title)}",
                parse_mode="HTML"
            )
            try:
                os.remove(audio_path)
            except:
                pass
        else:
            try:
                await processing_msg.edit_text(get_text(user_id, 'error'))
            except:
                pass
    except Exception as e:
        logger.error(f"Fallback audio error: {e}")
        try:
            await processing_msg.edit_text(get_text(user_id, 'error'))
        except Exception:
            pass

# ========== Ovozli / Audio / Video fayllar ==========
@router.message(F.voice | F.audio | F.video | F.video_note)
async def handle_media(message: Message):
    user_id = message.from_user.id
    if not await check_subscription(user_id):
        await message.answer(get_text(user_id, 'check_sub'), reply_markup=subscription_keyboard(user_id))
        return
    processing_msg = await message.answer(get_text(user_id, 'recognizing'))
    try:
        if message.voice:
            file_id = message.voice.file_id
        elif message.audio:
            file_id = message.audio.file_id
        elif message.video:
            file_id = message.video.file_id
        elif message.video_note:
            file_id = message.video_note.file_id
        else:
            await processing_msg.edit_text(get_text(user_id, 'error'))
            return

        file_io = await bot.download(file_id)
        if file_io:
            file_data = file_io.read()
            song_info = await recognize_with_shazam(file_data)
            if song_info:
                await send_recognized_song(message, song_info, user_id, processing_msg)
            else:
                await processing_msg.edit_text(get_text(user_id, 'song_not_found'))
        else:
            await processing_msg.edit_text(get_text(user_id, 'error'))
    except Exception as e:
        logger.error(f"Media handle error: {e}")
        try:
            await processing_msg.edit_text(get_text(user_id, 'error'))
        except Exception:
            pass

# ========== Matn qidirish ==========
@router.message(F.text & ~F.text.startswith(("http://", "https://", "/")))
async def handle_text_search(message: Message):
    user_id = message.from_user.id
    if not await check_subscription(user_id):
        await message.answer(get_text(user_id, 'check_sub'), reply_markup=subscription_keyboard(user_id))
        return

    search_query = message.text.strip()
    processing_msg = await message.answer(get_text(user_id, 'processing'))

    # YouTube dan qidiruv
    results = await search_youtube_tracks(search_query, limit=15)

    if results:
        search_id = str(uuid.uuid4())[:8]
        search_cache[search_id] = {'query': search_query, 'results': results}
        lang = user_languages_cache.get(user_id, 'uz')
        text = get_search_text(search_query, results, 1, lang)
        keyboard = get_search_keyboard(1, len(results), search_id)
        try:
            await processing_msg.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Edit search text error: {e}")
            await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
            try:
                await processing_msg.delete()
            except Exception:
                pass
    else:
        await processing_msg.edit_text(get_text(user_id, 'no_results'))

# ========== Sahifalar ==========
@router.callback_query(F.data.startswith("page_"))
async def process_page_button(callback: CallbackQuery):
    parts = callback.data.split("_")
    search_id = parts[1]
    page = int(parts[2])
    user_id = callback.from_user.id
    data = search_cache.get(search_id)
    if not data:
        await callback.answer(get_text(user_id, 'search_expired'), show_alert=True)
        return
    lang = user_languages_cache.get(user_id, 'uz')
    text = get_search_text(data['query'], data['results'], page, lang)
    keyboard = get_search_keyboard(page, len(data['results']), search_id)
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()

@router.callback_query(F.data.startswith("close_"))
async def process_close_button(callback: CallbackQuery):
    search_id = callback.data.split("_")[1]
    if search_id in search_cache:
        del search_cache[search_id]
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer()

@router.callback_query(F.data == "ignore")
async def process_ignore_button(callback: CallbackQuery):
    await callback.answer()

# ========== Qo'shiqni yuklash (qidiruv natijasidan) ==========
@router.callback_query(F.data.startswith("dl_"))
async def process_download_button(callback: CallbackQuery):
    parts = callback.data.split("_")
    search_id = parts[1]
    index = int(parts[2])
    user_id = callback.from_user.id
    data = search_cache.get(search_id)
    if not data:
        await callback.answer(get_text(user_id, 'search_expired'), show_alert=True)
        return
    if not await check_subscription(user_id):
        await callback.message.answer(get_text(user_id, 'check_sub'), reply_markup=subscription_keyboard(user_id))
        await callback.answer()
        return
    await callback.answer()

    selected_song = data['results'][index]
    uploader = selected_song.get('uploader', '')
    title = selected_song.get('title', '')
    song_url = selected_song.get('url', '')

    processing_msg = await callback.message.answer(get_text(user_id, 'downloading'))
    audio_path = None
    try:
        # To'g'ridan-to'g'ri URL orqali yuklab olish
        if song_url:
            audio_path, dl_title, dl_artist = await download_audio_from_url(song_url, user_id)
        else:
            query = f"{uploader} - {title}" if uploader else title
            audio_path, dl_title, dl_artist = await download_song_from_youtube(query, user_id)

        if audio_path and os.path.exists(audio_path):
            audio_file = FSInputFile(audio_path)
            display_title = dl_title or title
            display_artist = dl_artist or uploader
            await callback.message.answer_audio(
                audio_file,
                title=display_title,
                performer=display_artist,
                caption=f"🎵 <b>{html_escape(display_artist)}</b> — {html_escape(display_title)}",
                parse_mode="HTML"
            )
            try:
                await processing_msg.delete()
            except Exception:
                pass
        else:
            await processing_msg.edit_text(get_text(user_id, 'error'))
    except Exception as e:
        logger.error(f"Download error: {e}")
        try:
            await processing_msg.edit_text(get_text(user_id, 'error'))
        except Exception:
            pass
    finally:
        if audio_path and os.path.exists(str(audio_path)):
            try:
                os.remove(audio_path)
            except Exception:
                pass

# ========== DUMMY WEB SERVER ==========
async def handle_ping(request):
    return web.Response(text="Bot is alive and running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Web Server started on port {port}")

# ========== ASOSIY ==========
async def main():
    await database.init_db()
    os.makedirs('downloads', exist_ok=True)
    dp.include_router(router)
    await start_web_server()
    logger.info("Bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
