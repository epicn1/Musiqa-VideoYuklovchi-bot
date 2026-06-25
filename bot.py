import asyncio
import json
import os
import time
import uuid
import re
import logging
import shutil
from dataclasses import dataclass
from html import escape, unescape
from io import BytesIO
from urllib.parse import quote, urlparse
import aiohttp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, URLInputFile
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
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "20989956f0msh6800512a62e08eap18416ejsnae06767c25e8")

REQUEST_LIMIT = 50
RAPIDAPI_TIMEOUT = aiohttp.ClientTimeout(total=40, connect=12, sock_read=30)
MEDIA_EXTENSIONS = ('.mp4', '.mov', '.mkv', '.webm', '.m3u8', '.mp3', '.m4a', '.aac', '.ogg', '.opus', '.wav')
AUDIO_EXTENSIONS = ('.mp3', '.m4a', '.aac', '.ogg', '.opus', '.wav')
VIDEO_EXTENSIONS = ('.mp4', '.mov', '.mkv', '.webm', '.m3u8')
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp')
SOCIAL_PAGE_DOMAINS = ('instagram.com', 'tiktok.com', 'youtube.com', 'youtu.be', 'facebook.com', 'fb.watch', 'twitter.com', 'x.com', 'soundcloud.com')
CDN_HINTS = ('cdn', 'fbcdn', 'googlevideo', 'tiktokcdn', 'sndcdn', 'scdn', 'cloudfront', 'akamai', 'twimg', 'rapidapi')

UNIVERSAL_APIS = [
    {"name": "API_1 Auto Download All In One", "method": "POST", "url": "https://auto-download-all-in-one.p.rapidapi.com/v1/social/autolink", "host": "auto-download-all-in-one.p.rapidapi.com", "json": {"url": "{link}"}},
    {"name": "API_2 Social Download All In One", "method": "POST", "url": "https://social-download-all-in-one.p.rapidapi.com/v1/social/autolink", "host": "social-download-all-in-one.p.rapidapi.com", "json": {"url": "{link}"}},
    {"name": "API_3 ZM API", "method": "GET", "url": "https://zm-api.p.rapidapi.com/v1/social/autolink?url={encoded_link}", "host": "zm-api.p.rapidapi.com"},
    {"name": "API_4 All-In-One Media Downloader API", "method": "GET", "url": "https://all-in-one-media-downloader-api.p.rapidapi.com/download?url={encoded_link}", "host": "all-in-one-media-downloader-api.p.rapidapi.com"},
    {"name": "API_5 All Media Downloader", "method": "GET", "url": "https://all-media-downloader4.p.rapidapi.com/api/youtube/download?id={id_or_link}", "host": "all-media-downloader4.p.rapidapi.com"},
    {"name": "API_6 Full Downloader Social Media", "method": "GET", "url": "https://full-downloader-social-media.p.rapidapi.com/?url={encoded_link}", "host": "full-downloader-social-media.p.rapidapi.com"},
    {"name": "API_7 Download All In One - Ultimate", "method": "GET", "url": "https://download-all-in-one-ultimate.p.rapidapi.com/autolink?url={encoded_link}", "host": "download-all-in-one-ultimate.p.rapidapi.com"},
]

INSTAGRAM_APIS = [
    {"name": "API_INSTA_1 Reels Downloader", "method": "GET", "url": "https://instagram-downloader-download-instagram-videos-stories.p.rapidapi.com/unified/url?url={encoded_link}", "host": "instagram-downloader-download-instagram-videos-stories.p.rapidapi.com"},
    {"name": "API_INSTA_2 Instagram Downloader Scraper", "method": "GET", "url": "https://instagram-downloader-scraper-reels-igtv-posts-stories.p.rapidapi.com/instagram/get_media?url={encoded_link}", "host": "instagram-downloader-scraper-reels-igtv-posts-stories.p.rapidapi.com"},
]

YOUTUBE_APIS = [
    {"name": "API_YT_1 YouTube MP3 Audio Video Downloader", "method": "GET", "url": "https://youtube-mp3-audio-video-downloader.p.rapidapi.com/language_list/{video_id}?response_mode=default", "host": "youtube-mp3-audio-video-downloader.p.rapidapi.com", "requires_video_id": True},
    {"name": "API_YT_2 YouTube Info & Download API", "method": "GET", "url": "https://youtube-info-download-api.p.rapidapi.com/ajax/download.php?format=mp3&url={encoded_link}", "host": "youtube-info-download-api.p.rapidapi.com"},
    {"name": "API_YT_3 Social Media Video Downloader", "method": "GET", "url": "https://social-media-video-downloader.p.rapidapi.com/youtube/v3/video/details?videoId={video_id}", "host": "social-media-video-downloader.p.rapidapi.com", "requires_video_id": True},
]

SOUNDCLOUD_APIS = [
    {"name": "API_SOUNDCLOUD SoundCloud Scraper", "method": "GET", "url": "https://soundcloud-scraper.p.rapidapi.com/v1/track/metadata?track={encoded_link}", "host": "soundcloud-scraper.p.rapidapi.com"},
]

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
        'sub_limit_reached': "📢 Siz 50 ta so'rovdan keyin botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:",
        'btn_broadcast': "📢 Hammaga xabar yuborish",
        'btn_confirm': "✅ Tasdiqlash",
        'btn_cancel': "❌ Bekor qilish",
        'admin_broadcast_prompt': "📢 Iltimos, yubormoqchi bo'lgan xabaringizni yuboring (matn, rasm, video va h.k.):",
        'admin_broadcast_confirm': "📢 Xabarni barcha foydalanuvchilarga yuborishni tasdiqlaysizmi?",
        'admin_broadcast_sent': "✅ Xabar {count} ta foydalanuvchiga yuborildi!",
        'admin_broadcast_cancelled': "❌ Xabar yuborish bekor qilindi.",
        'admin_broadcast_error': "❌ Xabar yuborishda xatolik yuz berdi.",
        'sub_limit_reached': "📢 Siz 50 ta so'rovdan keyin botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:",
        'btn_broadcast': "📢 Hammaga xabar yuborish",
        'btn_confirm': "✅ Tasdiqlash",
        'btn_cancel': "❌ Bekor qilish",
        'admin_broadcast_prompt': "📢 Iltimos, yubormoqchi bo'lgan xabaringizni yuboring (matn, rasm, video va h.k.):",
        'admin_broadcast_confirm': "📢 Xabarni barcha foydalanuvchilarga yuborishni tasdiqlaysizmi?",
        'admin_broadcast_sent': "✅ Xabar {count} ta foydalanuvchiga yuborildi!",
        'admin_broadcast_cancelled': "❌ Xabar yuborish bekor qilindi.",
        'admin_broadcast_error': "❌ Xabar yuborishda xatolik yuz berdi.",
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
        'sub_limit_reached': "📢 После 50 запросов вам нужно подписаться на каналы для использования бота:",
        'btn_broadcast': "📢 Рассылка всем",
        'btn_confirm': "✅ Подтвердить",
        'btn_cancel': "❌ Отмена",
        'admin_broadcast_prompt': "📢 Отправьте сообщение, которое хотите разослать (текст, фото, видео и т.д.):",
        'admin_broadcast_confirm': "📢 Подтвердите отправку сообщения всем пользователям?",
        'admin_broadcast_sent': "✅ Сообщение отправлено {count} пользователям!",
        'admin_broadcast_cancelled': "❌ Рассылка отменена.",
        'admin_broadcast_error': "❌ Ошибка при рассылке.",
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
        'sub_limit_reached': "📢 After 50 requests, you need to subscribe to the channels to use the bot:",
        'btn_broadcast': "📢 Broadcast to all",
        'btn_confirm': "✅ Confirm",
        'btn_cancel': "❌ Cancel",
        'admin_broadcast_prompt': "📢 Send the message you want to broadcast (text, photo, video, etc.):",
        'admin_broadcast_confirm': "📢 Confirm sending this message to all users?",
        'admin_broadcast_sent': "✅ Message sent to {count} users!",
        'admin_broadcast_cancelled': "❌ Broadcast cancelled.",
        'admin_broadcast_error': "❌ Error sending broadcast.",
    }
}

# ========== FSM States ==========
class UserState(StatesGroup):
    language = State()
    main_menu = State()

class AdminState(StatesGroup):
    waiting_broadcast = State()

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
subscription_cache = {}
SUBSCRIPTION_CACHE_TTL = 300

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

@dataclass(slots=True)
class MediaCandidate:
    url: str
    media_type: str = "document"
    quality: str = ""
    title: str = "Media"
    source_api: str = ""
    score: int = 0

def first_url_from_text(text: str) -> str | None:
    match = re.search(r'https?://[^\s<>"\']+', text or "", re.IGNORECASE)
    return match.group(0).rstrip(').,;"\'') if match else None

def extract_youtube_id(url: str) -> str | None:
    patterns = [
        r'(?:v=|/shorts/|/embed/|youtu\.be/)([A-Za-z0-9_-]{6,})',
        r'youtube\.com/watch/([A-Za-z0-9_-]{6,})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return match.group(1).split('&')[0].split('?')[0]
    return None

def rapidapi_headers(host: str) -> dict:
    return {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": host,
        "Accept": "application/json,text/plain,*/*",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 RapidAPI-TelegramBot/1.0",
    }

def build_api_url(template: str, link: str) -> str:
    video_id = extract_youtube_id(link) or link
    return template.format(
        link=link,
        encoded_link=quote(link, safe=""),
        id_or_link=quote(video_id if video_id else link, safe=""),
        video_id=quote(video_id, safe=""),
    )

def build_api_json(payload: dict | None, link: str) -> dict | None:
    if not payload:
        return None
    return {key: (value.format(link=link) if isinstance(value, str) else value) for key, value in payload.items()}

def looks_like_direct_media_url(url: str, key_path: str = "") -> bool:
    if not url or not url.lower().startswith(("http://", "https://")):
        return False
    lowered = unescape(url).lower()
    parsed = urlparse(lowered)
    path = parsed.path.split('?')[0]
    host = parsed.netloc
    if any(domain in host for domain in SOCIAL_PAGE_DOMAINS) and not any(ext in path for ext in MEDIA_EXTENSIONS):
        return False
    if any(ext in path for ext in MEDIA_EXTENSIONS):
        return True
    media_key_words = (
        'download', 'downloadurl', 'download_url', 'video', 'videourl', 'video_url',
        'audio', 'audiourl', 'audio_url', 'music', 'mp3', 'mp4', 'hd', 'sd', 'source',
        'src', 'play', 'stream', 'media', 'nowatermark', 'no_watermark', 'url'
    )
    return any(word in key_path.lower() for word in media_key_words) and any(hint in lowered for hint in CDN_HINTS + MEDIA_EXTENSIONS)

def detect_media_type(url: str, key_path: str = "", fallback_platform: str = "") -> str:
    lowered = unescape(url).lower()
    key = key_path.lower()
    parsed_path = urlparse(lowered).path
    if any(ext in parsed_path for ext in AUDIO_EXTENSIONS) or any(word in key for word in ('audio', 'music', 'mp3', 'sound')):
        return "audio"
    if any(ext in parsed_path for ext in VIDEO_EXTENSIONS) or any(word in key for word in ('video', 'mp4', 'hd', 'sd', 'play')):
        return "video"
    if any(ext in parsed_path for ext in IMAGE_EXTENSIONS) or any(word in key for word in ('image', 'thumb', 'photo', 'cover')):
        return "photo"
    if fallback_platform in ('youtube', 'soundcloud'):
        return "audio"
    return "video"

def media_score(url: str, key_path: str, media_type: str, platform: str) -> int:
    lowered = unescape(f"{url} {key_path}").lower()
    score = 10
    if media_type == "video":
        score += 30
    if media_type == "audio":
        score += 35 if platform in ('youtube', 'soundcloud') else 15
    if '.mp4' in lowered or '.mp3' in lowered:
        score += 25
    if any(word in lowered for word in ('hd', '1080', '720', 'high', 'best')):
        score += 20
    if any(word in lowered for word in ('no_watermark', 'nowatermark', 'without_watermark')):
        score += 15
    if any(word in lowered for word in ('watermark', 'thumb', 'thumbnail', 'cover', 'avatar')):
        score -= 20
    return score

def extract_title_from_json(data) -> str:
    title_keys = {'title', 'caption', 'description', 'name', 'fulltitle', 'track', 'song'}
    stack = [data]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            for key, value in item.items():
                if key.lower() in title_keys and isinstance(value, (str, int, float)) and str(value).strip():
                    return str(value).strip()[:120]
                if isinstance(value, (dict, list)):
                    stack.append(value)
        elif isinstance(item, list):
            stack.extend(item)
    return "Media"

def extract_media_candidates(data, *, source_api: str, platform: str, original_url: str) -> list[MediaCandidate]:
    candidates: list[MediaCandidate] = []
    title = extract_title_from_json(data)

    def walk(value, path="root"):
        if isinstance(value, dict):
            for key, nested in value.items():
                walk(nested, f"{path}.{key}")
        elif isinstance(value, list):
            for index, nested in enumerate(value):
                walk(nested, f"{path}[{index}]")
        elif isinstance(value, str):
            raw = unescape(value.strip())
            found_url = raw if raw.lower().startswith(("http://", "https://")) else first_url_from_text(raw)
            if not found_url or found_url.rstrip('/') == original_url.rstrip('/'):
                return
            if not looks_like_direct_media_url(found_url, path):
                return
            media_type = detect_media_type(found_url, path, platform)
            candidates.append(MediaCandidate(
                url=found_url,
                media_type=media_type,
                title=title,
                source_api=source_api,
                quality=path,
                score=media_score(found_url, path, media_type, platform),
            ))

    walk(data)
    unique = {}
    for candidate in candidates:
        old = unique.get(candidate.url)
        if old is None or candidate.score > old.score:
            unique[candidate.url] = candidate
    return sorted(unique.values(), key=lambda item: item.score, reverse=True)

async def fetch_rapidapi_json(session: aiohttp.ClientSession, api: dict, link: str) -> dict | list | None:
    if api.get("requires_video_id") and not extract_youtube_id(link):
        return None
    url = build_api_url(api["url"], link)
    headers = rapidapi_headers(api["host"])
    payload = build_api_json(api.get("json"), link)
    try:
        async with session.request(api["method"], url, headers=headers, json=payload, timeout=RAPIDAPI_TIMEOUT) as response:
            text = await response.text(errors="ignore")
            if response.status in (401, 403, 404, 408, 409, 425, 429) or response.status >= 500:
                raise RuntimeError(f"HTTP {response.status}: {text[:180]}")
            if response.status >= 400:
                raise RuntimeError(f"HTTP {response.status}: {text[:180]}")
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                direct = first_url_from_text(text)
                return {"url": direct} if direct else None
    except Exception as exc:
        logger.warning(f"RapidAPI fallback skipped [{api['name']}]: {exc}")
        return None

def route_apis_for_platform(platform: str) -> list[dict]:
    if platform == 'instagram':
        return INSTAGRAM_APIS + UNIVERSAL_APIS
    if platform == 'youtube':
        return YOUTUBE_APIS + UNIVERSAL_APIS
    if platform == 'soundcloud':
        return SOUNDCLOUD_APIS + UNIVERSAL_APIS
    return UNIVERSAL_APIS

async def resolve_media_via_rapidapi(link: str, platform: str) -> MediaCandidate | None:
    async with aiohttp.ClientSession(timeout=RAPIDAPI_TIMEOUT) as session:
        for api in route_apis_for_platform(platform):
            try:
                data = await fetch_rapidapi_json(session, api, link)
                if not data:
                    continue
                candidates = extract_media_candidates(data, source_api=api['name'], platform=platform, original_url=link)
                if candidates:
                    best = candidates[0]
                    logger.info(f"RapidAPI success: {api['name']} -> {best.media_type} score={best.score}")
                    return best
                logger.warning(f"RapidAPI no direct media URL: {api['name']}")
            except Exception as exc:
                logger.warning(f"RapidAPI parser error [{api['name']}]: {exc}")
                continue
    return None

async def keep_upload_action(chat_id: int, action: ChatAction = ChatAction.UPLOAD_VIDEO):
    while True:
        try:
            await bot.send_chat_action(chat_id=chat_id, action=action)
            await asyncio.sleep(4)
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(4)

async def send_media_candidate(message: Message, candidate: MediaCandidate, user_id: int, platform: str):
    media_id = str(uuid.uuid4())[:8]
    url_cache[media_id] = {'url': candidate.url, 'duration': 0, 'platform': platform, 'source_url': candidate.url}
    safe_title = (candidate.title or platform.title() or 'Media')[:64]
    filename_ext = '.mp3' if candidate.media_type == 'audio' else '.mp4'
    parsed_ext = os.path.splitext(urlparse(candidate.url).path)[1]
    if parsed_ext and len(parsed_ext) <= 6:
        filename_ext = parsed_ext
    input_file = URLInputFile(candidate.url, filename=f"{safe_title}{filename_ext}")
    caption = f"✅ <b>{html_escape(safe_title)}</b>"

    if candidate.media_type == 'audio':
        try:
            await message.answer_audio(input_file, title=safe_title, performer=platform.title(), caption=caption, reply_markup=audio_only_keyboard(user_id, media_id), parse_mode="HTML")
            return
        except Exception as exc:
            logger.error(f"RapidAPI send audio failed: {exc}")
            await message.answer_document(URLInputFile(candidate.url, filename=f"{safe_title}{filename_ext}"), caption=caption, parse_mode="HTML")
            return

    try:
        await message.answer_video(input_file, caption=caption, reply_markup=video_action_keyboard(user_id, media_id), parse_mode="HTML")
    except Exception as exc:
        logger.error(f"RapidAPI send video failed, sending document/link: {exc}")
        try:
            await message.answer_document(URLInputFile(candidate.url, filename=f"{safe_title}{filename_ext}"), caption=caption, reply_markup=video_action_keyboard(user_id, media_id), parse_mode="HTML")
        except Exception:
            await message.answer(f"✅ Yuklab olish havolasi:\n{candidate.url}", disable_web_page_preview=True)

def ffmpeg_available():
    """FFmpeg bor-yo'qligini tekshiradi. MP3 konvertatsiya uchun kerak."""
    return shutil.which('ffmpeg') is not None

def find_downloaded_file(prefix, preferred_exts=None):
    """downloads papkasidan yt-dlp yaratgan faylni topadi."""
    preferred_exts = preferred_exts or ['.mp3', '.m4a', '.mp4', '.webm', '.mkv', '.mov', '.aac', '.opus']
    if not os.path.isdir('downloads'):
        return None

    candidates = []
    for filename in os.listdir('downloads'):
        if not filename.startswith(prefix) or filename.endswith(('.part', '.ytdl', '.tmp')):
            continue
        path = os.path.join('downloads', filename)
        if os.path.isfile(path):
            candidates.append(path)

    if not candidates:
        return None

    for ext in preferred_exts:
        for path in candidates:
            if path.lower().endswith(ext):
                return path
    return max(candidates, key=os.path.getmtime)

def audio_download_opts(output_template):
    """Audio yuklash sozlamasi: ffmpeg bo'lsa MP3, bo'lmasa m4a/original audio."""
    opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'outtmpl': output_template,
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
    if ffmpeg_available():
        opts['format'] = 'bestaudio/best'
        opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    if os.path.exists('cookies.txt'):
        opts['cookiefile'] = 'cookies.txt'
    return opts

async def send_audio_result(message, audio_path, title='Audio', performer='Unknown', caption=None, reply_markup=None):
    """Audio faylni Telegramga yuboradi; audio sifatida ketmasa document qilib yuboradi."""
    safe_title = str(title or 'Audio')[:64]
    safe_performer = str(performer or 'Unknown')[:64]
    caption = caption or f"🎵 <b>{html_escape(safe_performer)}</b> — {html_escape(safe_title)}"

    try:
        await message.answer_audio(
            FSInputFile(audio_path),
            title=safe_title,
            performer=safe_performer,
            caption=caption,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Send as audio failed, sending as document: {e}")
        await message.answer_document(
            FSInputFile(audio_path),
            caption=caption,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )

def is_social_url(url):
    """Ijtimoiy tarmoq havolasini tekshirish"""
    patterns = [
        r'(youtube\.com|youtu\.be)',
        r'(instagram\.com)',
        r'(tiktok\.com)',
        r'(facebook\.com|fb\.com|fb\.watch)',
        r'(twitter\.com|x\.com)',
        r'(soundcloud\.com)',
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
    buttons = []
    if user_id in ADMIN_IDS:
        buttons.append([
            InlineKeyboardButton(text=get_text(user_id, 'btn_broadcast'), callback_data="admin_broadcast"),
            InlineKeyboardButton(text=get_text(user_id, 'change_lang'), callback_data="open_change_lang"),
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text=get_text(user_id, 'change_lang'), callback_data="open_change_lang"),
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

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
    if re.search(r'(twitter\.com|x\.com)', url, re.IGNORECASE):
        return 'twitter'
    if re.search(r'(soundcloud\.com)', url, re.IGNORECASE):
        return 'soundcloud'
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
    now = time.time()
    cached = subscription_cache.get(user_id)
    if cached and cached[0] and (now - cached[1]) < SUBSCRIPTION_CACHE_TTL:
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
    subscription_cache[user_id] = (True, now)
    return True

async def check_request_limit(user_id):
    if user_id in ADMIN_IDS:
        return True
    if await check_subscription(user_id):
        return True
    user = await database.get_user(user_id)
    if user and user.request_count >= REQUEST_LIMIT:
        return False
    await database.increment_user_requests(user_id)
    return True

# ========== Obuna tekshirish ==========
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
            ydl_opts = audio_download_opts(f'downloads/{user_id}_{temp_id}.%(ext)s')
        else:
            # Boshqa platformalar uchun video
            ydl_opts = {
                # Instagram/TikTok/Facebook kabi servislar ko'pincha bitta tayyor mp4 beradi.
                # Qattiq filesize yoki bestvideo+bestaudio shartlari ayrim linklarda format topilmasligiga olib keladi.
                'format': 'best[ext=mp4]/best',
                'outtmpl': f'downloads/{user_id}_{temp_id}.%(ext)s',
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
                'socket_timeout': 30,
                'retries': 3,
                'fragment_retries': 3,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Referer': 'https://www.instagram.com/',
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
                    filename = base + '.mp3' if ffmpeg_available() else ydl.prepare_filename(info)
                    if not os.path.exists(filename):
                        filename = find_downloaded_file(f'{user_id}_{temp_id}', ['.mp3', '.m4a', '.webm', '.opus', '.aac'])
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
                        if not os.path.exists(filename):
                            filename = find_downloaded_file(f'{user_id}_{temp_id}', ['.mp4', '.mov', '.webm', '.mkv'])
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

        ydl_opts = audio_download_opts(output_template)

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info is None:
                    return None, None, None
                base = os.path.splitext(ydl.prepare_filename(info))[0]
                filename = base + '.mp3' if ffmpeg_available() else ydl.prepare_filename(info)
                if not os.path.exists(filename):
                    filename = find_downloaded_file(f'{user_id}_{temp_id}', ['.mp3', '.m4a', '.webm', '.opus', '.aac'])
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

        ydl_opts = audio_download_opts(f'downloads/{user_id}_{temp_id}.%(ext)s')

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{query}", download=True)
                if not info:
                    return None, None, None
                if 'entries' in info and info['entries']:
                    info = info['entries'][0]
                base = os.path.splitext(ydl.prepare_filename(info))[0]
                filename = base + '.mp3' if ffmpeg_available() else ydl.prepare_filename(info)
                if not os.path.exists(filename):
                    filename = find_downloaded_file(f'{user_id}_{temp_id}', ['.mp3', '.m4a', '.webm', '.opus', '.aac'])
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
            caption = f"🎵 <b>{html_escape(artist)}</b> — <b>{html_escape(title)}</b>"
            if snippet:
                caption += f"\n🎼 <i>{html_escape(snippet)}</i>"
            await send_audio_result(message, audio_path, title=title, performer=artist, caption=caption)
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
    await callback.message.edit_text(
        get_text(user_id, 'main_menu').format(user=user_name),
        reply_markup=main_menu_keyboard(user_id),
        parse_mode="HTML"
    )
    await state.set_state(UserState.main_menu)
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
    if not await check_request_limit(user_id):
        await message.answer(get_text(user_id, 'check_sub'), reply_markup=subscription_keyboard(user_id))
        return

    url = message.text.strip()
    if not is_social_url(url):
        await message.answer(get_text(user_id, 'unsupported_url'))
        return

    platform = extract_platform(url) or 'universal'
    processing_msg = await message.answer(get_text(user_id, 'downloading'))
    action = ChatAction.UPLOAD_DOCUMENT if platform in ('youtube', 'soundcloud') else ChatAction.UPLOAD_VIDEO
    action_task = asyncio.create_task(keep_upload_action(message.chat.id, action))

    try:
        candidate = await resolve_media_via_rapidapi(url, platform)
        if not candidate:
            await processing_msg.edit_text("Hozircha yuklash imkoni bo'lmadi. Keyinroq qayta urining")
            return

        await send_media_candidate(message, candidate, user_id, platform)
        try:
            await processing_msg.delete()
        except Exception:
            pass
    except Exception as e:
        logger.error(f"URL handler error: {e}")
        try:
            await processing_msg.edit_text("Hozircha yuklash imkoni bo'lmadi. Keyinroq qayta urining")
        except Exception:
            pass
    finally:
        action_task.cancel()
        try:
            await action_task
        except asyncio.CancelledError:
            pass

# ========== Audioni yuklash ==========
@router.callback_query(F.data.startswith("getaudio_"))
async def process_audio_button(callback: CallbackQuery):
    user_id = callback.from_user.id
    video_id = callback.data[9:]
    if not await check_request_limit(user_id):
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
                await send_audio_result(
                    callback.message,
                    audio_path,
                    title=title,
                    performer=uploader,
                    caption=f"🎧 <b>{html_escape(uploader)}</b> — {html_escape(title)}"
                )
        else:
            # Boshqa platformalar uchun duration bo'yicha audio yuklash
            audio_path, title = await download_audio_by_duration(url, duration, user_id)
            if audio_path and os.path.exists(audio_path):
                mins = int(duration) // 60
                secs = int(duration) % 60
                dur_str = f"{mins}:{secs:02d}"
                uploader = platform.title() if platform else 'Video'
                
                await send_audio_result(
                    callback.message,
                    audio_path,
                    title=title,
                    performer=uploader,
                    caption=f"🎵 <b>{html_escape(title)}</b> <i>({html_escape(dur_str)})</i>"
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
    if not await check_request_limit(user_id):
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
                
                await send_audio_result(
                    callback.message,
                    audio_path,
                    title=title,
                    performer=uploader,
                    caption=f"🎵 <b>{html_escape(title)}</b> <i>({html_escape(dur_str)})</i>"
                )
                try:
                    os.remove(audio_path)
                except:
                    pass
                return
        
        # Duration bo'lmasa oddiy audio yuklash
        audio_path, title, uploader = await download_audio_from_url(url, user_id)
        if audio_path and os.path.exists(audio_path):
            await send_audio_result(
                callback.message,
                audio_path,
                title=title,
                performer=uploader,
                caption=f"🎧 <b>{html_escape(uploader)}</b> — {html_escape(title)}"
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
    if not await check_request_limit(user_id):
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
    if not await check_request_limit(user_id):
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
    if not await check_request_limit(user_id):
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
            display_title = dl_title or title
            display_artist = dl_artist or uploader
            await send_audio_result(
                callback.message,
                audio_path,
                title=display_title,
                performer=display_artist,
                caption=f"🎵 <b>{html_escape(display_artist)}</b> — {html_escape(display_title)}"
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

# ========== Broadcast funksiyalari ==========
async def send_broadcast_message(user_id: int, content_type: str, content, text: str = None):
    try:
        if content_type == 'text':
            await bot.send_message(user_id, text, parse_mode="HTML", disable_web_page_preview=True)
        elif content_type == 'photo':
            await bot.send_photo(user_id, content, caption=text, parse_mode="HTML")
        elif content_type == 'video':
            await bot.send_video(user_id, content, caption=text, parse_mode="HTML")
        elif content_type == 'document':
            await bot.send_document(user_id, content, caption=text, parse_mode="HTML")
        elif content_type == 'animation':
            await bot.send_animation(user_id, content, caption=text, parse_mode="HTML")
        elif content_type == 'audio':
            await bot.send_audio(user_id, content, caption=text, parse_mode="HTML")
        elif content_type == 'voice':
            await bot.send_voice(user_id, content, caption=text, parse_mode="HTML")
        else:
            return False
        return True
    except Exception as e:
        logger.error(f"Broadcast error to {user_id}: {e}")
        return False

def broadcast_confirm_keyboard(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(user_id, 'btn_confirm'), callback_data="broadcast_confirm")],
        [InlineKeyboardButton(text=get_text(user_id, 'btn_cancel'), callback_data="broadcast_cancel")]
    ])

@router.callback_query(F.data == "admin_broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if user_id not in ADMIN_IDS:
        await callback.answer("❌ Sizda bu amalni bajarish uchun ruxsat yo'q.", show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text(get_text(user_id, 'admin_broadcast_prompt'))
    await state.set_state(AdminState.waiting_broadcast)
    await callback.answer()

@router.message(AdminState.waiting_broadcast)
async def receive_broadcast_content(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        await state.clear()
        return

    content_type = None
    content = None
    text = None

    if message.text:
        content_type = 'text'
        text = message.text
    elif message.photo:
        content_type = 'photo'
        content = message.photo[-1].file_id
        text = message.caption
    elif message.video:
        content_type = 'video'
        content = message.video.file_id
        text = message.caption
    elif message.document:
        content_type = 'document'
        content = message.document.file_id
        text = message.caption
    elif message.animation:
        content_type = 'animation'
        content = message.animation.file_id
        text = message.caption
    elif message.audio:
        content_type = 'audio'
        content = message.audio.file_id
        text = message.caption
    elif message.voice:
        content_type = 'voice'
        content = message.voice.file_id
        text = message.caption
    else:
        await message.answer(get_text(user_id, 'error'))
        return

    await state.update_data(content_type=content_type, content=content, text=text)

    preview_text = get_text(user_id, 'admin_broadcast_confirm')
    keyboard = broadcast_confirm_keyboard(user_id)

    if content_type == 'text':
        await message.answer(f"📢 <b>Oldindan ko'rinish:</b>\n\n{text}", reply_markup=keyboard, parse_mode="HTML")
    elif content_type == 'photo':
        await message.answer_photo(content, caption=preview_text, reply_markup=keyboard, parse_mode="HTML")
    elif content_type == 'video':
        await message.answer_video(content, caption=preview_text, reply_markup=keyboard, parse_mode="HTML")
    elif content_type == 'document':
        await message.answer_document(content, caption=preview_text, reply_markup=keyboard, parse_mode="HTML")
    elif content_type == 'animation':
        await message.answer_animation(content, caption=preview_text, reply_markup=keyboard, parse_mode="HTML")
    elif content_type == 'audio':
        await message.answer_audio(content, caption=preview_text, reply_markup=keyboard, parse_mode="HTML")
    elif content_type == 'voice':
        await message.answer_voice(content, caption=preview_text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data == "broadcast_confirm")
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if user_id not in ADMIN_IDS:
        await callback.answer("❌ Ruxsat yo'q.", show_alert=True)
        return

    data = await state.get_data()
    content_type = data.get('content_type')
    content = data.get('content')
    text = data.get('text')

    await callback.message.edit_text("📢 Xabar yuborilmoqda... Iltimos kuting.")
    await callback.answer()
    await state.clear()

    user_ids = await database.get_all_user_ids()
    sent_count = 0
    failed_count = 0

    for uid in user_ids:
        success = await send_broadcast_message(uid, content_type, content, text)
        if success:
            sent_count += 1
        else:
            failed_count += 1
        await asyncio.sleep(0.05)

    result_text = get_text(user_id, 'admin_broadcast_sent').format(count=sent_count)
    if failed_count > 0:
        result_text += f"\n⚠️ {failed_count} ta foydalanuvchiga yuborib bo'lmadi."
    await callback.message.answer(result_text)

@router.callback_query(F.data == "broadcast_cancel")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await state.clear()
    await callback.message.edit_text(get_text(user_id, 'admin_broadcast_cancelled'))
    await callback.answer()
    await callback.message.answer(
        get_text(user_id, 'main_menu').format(user=callback.from_user.first_name),
        reply_markup=main_menu_keyboard(user_id),
        parse_mode="HTML"
    )

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
