import asyncio
import os
import uuid
import tempfile
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
        'song_found': "🎵 Topilgan qo'shiq:\n\n🎤 Ijrochi: {artist}\n📀 Nomi: {title}",
        'downloading_full': "⏳ To'liq versiyasi yuklanmoqda...",
        'song_not_found': "❌ Kechirasiz, qo'shiqni aniqlay olmadim.",
        'error': "❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.",
        'invalid_url': "❌ Noto'g'ri havola yuborildi.",
        'link_expired': "❌ Havola eskirgan, videoni qaytadan yuboring.",
        'search_expired': "❌ Qidiruv natijalari eskirgan, boshqadan qidiring.",
        'no_results': "❌ Hech narsa topilmadi.",
        'main_menu': "👋 Assalomu alaykum {user}!\n\n🎵 Men musiqa botiman! Quyidagilarni qila olaman:\n\n🔗 TikTok, Instagram, YouTube havolasini yuboring — videoni yuklab beraman\n🎧 Audioni yuklash — videodagi ovozni yuklab beraman\n🎶 Musiqasini yuklash — videodagi orqa fon musiqasini Shazam orqali topib yuklab beraman\n🔍 Qo'shiq nomi yoki ijrochi yozib yuboring — topib yuklab beraman\n🎤 Ovozli xabar yuboring — qo'shiqni tanib topaman\n📹 Video yuboring — ichidagi qo'shiqni aniqlayman\n🎧 Audio/video fayl yuboring — qo'shiqni topaman",
        'change_lang': "🌐 Tilni o'zgartirish",
        'lang_changed': "✅ Til muvaffaqiyatli o'zgartirildi!",
        'btn_audio': "🎧 Audioni yuklash",
        'btn_music': "🎶 Musiqasini yuklash",
        'no_url_found': "❌ Qo'shiqni yuklab bo'lmadi (havola yo'q).",
    },
    'ru': {
        'welcome': "👋 Здравствуйте {user}!\n\nДобро пожаловать в бот!\n\n🌐 Пожалуйста, выберите язык:",
        'check_sub': "📢 Пожалуйста, подпишитесь на следующие каналы для использования бота:",
        'check_button': "✅ Проверить",
        'not_subscribed': "❌ Вы еще не подписались!\n\nПожалуйста, сначала подпишитесь и проверьте снова.",
        'processing': "⏳ Поиск...",
        'downloading': "⬇️ Загрузка...",
        'recognizing': "🎵 Распознавание песни...",
        'song_found': "🎵 Найденная песня:\n\n🎤 Исполнитель: {artist}\n📀 Название: {title}",
        'downloading_full': "⏳ Загрузка полной версии...",
        'song_not_found': "❌ Извините, не удалось распознать песню.",
        'error': "❌ Произошла ошибка. Попробуйте снова.",
        'invalid_url': "❌ Неверная ссылка.",
        'link_expired': "❌ Ссылка устарела, отправьте видео снова.",
        'search_expired': "❌ Результаты поиска устарели, ищите снова.",
        'no_results': "❌ Ничего не найдено.",
        'main_menu': "👋 Здравствуйте {user}!\n\n🎵 Я музыкальный бот! Вот что я умею:\n\n🔗 Отправьте ссылку TikTok, Instagram, YouTube — скачаю видео\n🎧 Скачать аудио — скачаю звук из видео\n🎶 Скачать музыку — найду фоновую музыку через Shazam и скачаю\n🔍 Напишите название песни или исполнителя — найду и скачаю\n🎤 Отправьте голосовое сообщение — распознаю песню\n📹 Отправьте видео — определю музыку внутри\n🎧 Отправьте аудио/видео файл — найду песню",
        'change_lang': "🌐 Изменить язык",
        'lang_changed': "✅ Язык успешно изменён!",
        'btn_audio': "🎧 Скачать аудио",
        'btn_music': "🎶 Скачать музыку",
        'no_url_found': "❌ Не удалось скачать песню (нет ссылки).",
    },
    'en': {
        'welcome': "👋 Hello {user}!\n\nWelcome to the bot!\n\n🌐 Please select a language:",
        'check_sub': "📢 Please subscribe to the following channels to use the bot:",
        'check_button': "✅ Check",
        'not_subscribed': "❌ You haven't subscribed yet!\n\nPlease subscribe first and check again.",
        'processing': "⏳ Searching...",
        'downloading': "⬇️ Downloading...",
        'recognizing': "🎵 Recognizing song...",
        'song_found': "🎵 Found song:\n\n🎤 Artist: {artist}\n📀 Title: {title}",
        'downloading_full': "⏳ Downloading full version...",
        'song_not_found': "❌ Sorry, couldn't identify the song.",
        'error': "❌ An error occurred. Try again.",
        'invalid_url': "❌ Invalid link.",
        'link_expired': "❌ Link expired, please send the video again.",
        'search_expired': "❌ Search results expired, search again.",
        'no_results': "❌ Nothing found.",
        'main_menu': "👋 Hello {user}!\n\n🎵 I am a music bot! Here's what I can do:\n\n🔗 Send a TikTok, Instagram, YouTube link — I'll download the video\n🎧 Download audio — download the raw sound from video\n🎶 Download music — find background music via Shazam and download it\n🔍 Type a song name or artist — I'll find and download it\n🎤 Send a voice message — I'll recognize the song\n📹 Send a video — I'll identify the music inside\n🎧 Send an audio/video file — I'll find the song",
        'change_lang': "🌐 Change language",
        'lang_changed': "✅ Language changed successfully!",
        'btn_audio': "🎧 Download audio",
        'btn_music': "🎶 Download music",
        'no_url_found': "❌ Couldn't download song (no URL).",
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

def video_action_keyboard(user_id, video_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=get_text(user_id, 'btn_audio'), callback_data=f"getaudio_{video_id}"),
        InlineKeyboardButton(text=get_text(user_id, 'btn_music'), callback_data=f"getmusic_{video_id}"),
    ]])

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

# ========== Yuklab olish ==========
async def download_video_from_url(url, user_id):
    try:
        temp_id = str(uuid.uuid4())[:8]
        output_template = f'downloads/{user_id}_{temp_id}_%(title)s.%(ext)s'
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if 'requested_downloads' in info:
                filename = info['requested_downloads'][0]['filepath']
            elif not os.path.exists(filename):
                base, _ = os.path.splitext(filename)
                for ext in ['.mp4', '.mkv', '.webm']:
                    if os.path.exists(base + ext):
                        filename = base + ext
                        break
            return filename, info.get('title', 'Video')
    except Exception as e:
        logger.error(f"yt-dlp video error: {e}")
        return None, None

async def download_audio_from_url(url, user_id):
    try:
        temp_id = str(uuid.uuid4())[:8]
        output_template = f'downloads/{user_id}_{temp_id}_%(title)s.%(ext)s'
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_template,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp3'
            return filename, info.get('title', 'Audio'), info.get('uploader', 'Unknown')
    except Exception as e:
        logger.error(f"yt-dlp audio error: {e}")
        return None, None, None

async def download_full_song(query, user_id):
    try:
        temp_id = str(uuid.uuid4())[:8]
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'downloads/{user_id}_{temp_id}_%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=True)
            if 'entries' in info and info['entries']:
                info = info['entries'][0]
            filename = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp3'
            title = info.get('title', 'Unknown')
            artist = info.get('artist', info.get('uploader', 'Unknown'))
            return filename, title, artist
    except Exception as e:
        logger.error(f"Search download error: {e}")
        return None, None, None

async def recognize_with_shazam(file_data: bytes):
    try:
        out = await shazam.recognize(file_data)
        if out and 'track' in out:
            track = out['track']
            return {
                'title': track.get('title', 'Unknown'),
                'artist': track.get('subtitle', 'Unknown')
            }
        return None
    except Exception as e:
        logger.error(f"Shazam error: {e}")
        return None

async def send_recognized_song(message, song_info, user_id, processing_msg):
    """Shazam topgan qo'shiqni YouTube'dan yuklab yuborish"""
    try:
        await processing_msg.edit_text(
            get_text(user_id, 'song_found').format(
                artist=song_info['artist'],
                title=song_info['title']
            ) + f"\n\n{get_text(user_id, 'downloading_full')}"
        )
    except Exception:
        pass

    query = f"{song_info['artist']} - {song_info['title']}"
    full_audio_path, dl_title, dl_artist = await download_full_song(query, user_id)

    if full_audio_path and os.path.exists(full_audio_path):
        try:
            audio_file = FSInputFile(full_audio_path)
            await message.answer_audio(
                audio_file,
                title=song_info['title'],
                performer=song_info['artist'],
                caption=f"🎵 {song_info['artist']} - {song_info['title']}"
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
            if full_audio_path and os.path.exists(full_audio_path):
                os.remove(full_audio_path)
    else:
        try:
            await processing_msg.edit_text(get_text(user_id, 'error'))
        except Exception:
            pass

# ========== Search helpers ==========
def get_search_text(query, results, page):
    limit = 5
    start = (page - 1) * limit
    end = start + limit
    page_results = results[start:end]
    text = f"🔍 <b>{query}</b>\n\n"
    for i, res in enumerate(page_results):
        duration = format_duration(res.get('duration'))
        title = res.get('title', 'Unknown')
        uploader = res.get('uploader', '')
        if uploader:
            title = f"{uploader} - {title}"
        dur_text = f" <b>{duration}</b>" if duration else ""
        text += f"<b>{i+1}.</b> {title}{dur_text}\n\n"
    return text

def get_search_keyboard(page, total_results, search_id):
    limit = 5
    total_pages = (total_results + limit - 1) // limit
    buttons = []
    start_index = (page - 1) * limit
    for i in range(min(limit, total_results - start_index)):
        absolute_index = start_index + i
        buttons.append(InlineKeyboardButton(text=str(i + 1), callback_data=f"dl_{search_id}_{absolute_index}"))
    keyboard = [buttons]
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"page_{search_id}_{page-1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text="⏹", callback_data="ignore"))
    nav_buttons.append(InlineKeyboardButton(text="❌", callback_data=f"close_{search_id}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"page_{search_id}_{page+1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text="⏹", callback_data="ignore"))
    keyboard.append(nav_buttons)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def search_youtube_videos(query):
    try:
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'default_search': 'ytsearch25',
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            return info.get('entries', [])
    except Exception as e:
        logger.error(f"Search error: {e}")
        return []

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
        await message.answer(get_text(user_id, 'main_menu').format(user=user_name), reply_markup=main_menu_keyboard(user_id))
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
        await callback.message.edit_text(get_text(user_id, 'main_menu').format(user=user_name), reply_markup=main_menu_keyboard(user_id))
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
    await callback.message.edit_text(get_text(user_id, 'main_menu').format(user=user_name), reply_markup=main_menu_keyboard(user_id))
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
            await callback.message.edit_text(get_text(user_id, 'main_menu').format(user=user_name), reply_markup=main_menu_keyboard(user_id))
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
    processing_msg = await message.answer(get_text(user_id, 'downloading'))
    video_path = None
    try:
        video_path, title = await download_video_from_url(url, user_id)
        if video_path and os.path.exists(video_path):
            video_id = str(uuid.uuid4())[:8]
            url_cache[video_id] = url
            video_file = FSInputFile(video_path)
            await message.answer_video(video_file, caption=f"🎬 {title}", reply_markup=video_action_keyboard(user_id, video_id))
            await processing_msg.delete()
        else:
            await processing_msg.edit_text(get_text(user_id, 'invalid_url'))
    except Exception as e:
        logger.error(f"Video URL error: {e}")
        await processing_msg.edit_text(get_text(user_id, 'error'))
    finally:
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
            except Exception:
                pass

# ========== Audioni yuklash (videodagi oddiy ovoz) ==========
@router.callback_query(F.data.startswith("getaudio_"))
async def process_audio_button(callback: CallbackQuery):
    user_id = callback.from_user.id
    # getaudio_ prefix = 9 belgi
    video_id = callback.data[9:]
    if not await check_subscription(user_id):
        await callback.message.answer(get_text(user_id, 'check_sub'), reply_markup=subscription_keyboard(user_id))
        await callback.answer()
        return
    url = url_cache.get(video_id)
    if not url:
        await callback.answer(get_text(user_id, 'link_expired'), show_alert=True)
        return
    await callback.answer()
    processing_msg = await callback.message.answer(get_text(user_id, 'downloading'))
    audio_path = None
    try:
        audio_path, title, uploader = await download_audio_from_url(url, user_id)
        if audio_path and os.path.exists(audio_path):
            audio_file = FSInputFile(audio_path)
            await callback.message.answer_audio(
                audio_file, title=title, performer=uploader,
                caption=f"🎧 {uploader} - {title}"
            )
            try:
                await processing_msg.delete()
            except Exception:
                pass
        else:
            await processing_msg.edit_text(get_text(user_id, 'error'))
    except Exception as e:
        logger.error(f"Audio download error: {e}")
        try:
            await processing_msg.edit_text(get_text(user_id, 'error'))
        except Exception:
            pass
    finally:
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except Exception:
                pass

# ========== Musiqasini yuklash (Shazam + YouTube) ==========
@router.callback_query(F.data.startswith("getmusic_"))
async def process_music_button(callback: CallbackQuery):
    user_id = callback.from_user.id
    # getmusic_ prefix = 9 belgi, qolganini olish
    video_id = callback.data[9:]
    if not await check_subscription(user_id):
        await callback.message.answer(get_text(user_id, 'check_sub'), reply_markup=subscription_keyboard(user_id))
        await callback.answer()
        return
    url = url_cache.get(video_id)
    if not url:
        await callback.answer(get_text(user_id, 'link_expired'), show_alert=True)
        return
    await callback.answer()
    processing_msg = await callback.message.answer(get_text(user_id, 'recognizing'))
    audio_path = None
    try:
        audio_path, title, uploader = await download_audio_from_url(url, user_id)
        if audio_path and os.path.exists(audio_path):
            with open(audio_path, 'rb') as f:
                file_data = f.read()
            song_info = await recognize_with_shazam(file_data)
            if song_info:
                # Shazam topdi — eski audio o'chirib, YouTube dan yuklab yuborish
                if audio_path and os.path.exists(audio_path):
                    os.remove(audio_path)
                    audio_path = None
                await send_recognized_song(callback.message, song_info, user_id, processing_msg)
            else:
                # Shazam topa olmadi — audioni shundayicha yuborish
                try:
                    await processing_msg.edit_text(get_text(user_id, 'song_not_found'))
                except Exception:
                    pass
                audio_file = FSInputFile(audio_path)
                await callback.message.answer_audio(
                    audio_file, title=title, performer=uploader,
                    caption=f"🎧 {uploader} - {title}"
                )
        else:
            await processing_msg.edit_text(get_text(user_id, 'error'))
    except Exception as e:
        logger.error(f"Music extraction error: {e}")
        try:
            await processing_msg.edit_text(get_text(user_id, 'error'))
        except Exception:
            pass
    finally:
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
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
        await processing_msg.edit_text(get_text(user_id, 'error'))

# ========== Matn qidirish ==========
@router.message(F.text & ~F.text.startswith(("http://", "https://", "/")))
async def handle_text_search(message: Message):
    user_id = message.from_user.id
    if not await check_subscription(user_id):
        await message.answer(get_text(user_id, 'check_sub'), reply_markup=subscription_keyboard(user_id))
        return
    search_query = message.text.strip()
    processing_msg = await message.answer(get_text(user_id, 'processing'))
    results = await search_youtube_videos(search_query)
    if results:
        search_id = str(uuid.uuid4())[:8]
        search_cache[search_id] = {'query': search_query, 'results': results}
        text = get_search_text(search_query, results, 1)
        keyboard = get_search_keyboard(1, len(results), search_id)
        await processing_msg.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await processing_msg.edit_text(get_text(user_id, 'no_results'))

@router.callback_query(F.data.startswith("page_"))
async def process_page_button(callback: CallbackQuery):
    parts = callback.data.split("_")
    search_id = parts[1]
    page = int(parts[2])
    data = search_cache.get(search_id)
    if not data:
        await callback.answer(get_text(callback.from_user.id, 'search_expired'), show_alert=True)
        return
    text = get_search_text(data['query'], data['results'], page)
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
    await callback.message.delete()
    await callback.answer()

@router.callback_query(F.data == "ignore")
async def process_ignore_button(callback: CallbackQuery):
    await callback.answer()

@router.callback_query(F.data.startswith("dl_"))
async def process_download_button(callback: CallbackQuery):
    parts = callback.data.split("_")
    search_id = parts[1]
    index = int(parts[2])
    data = search_cache.get(search_id)
    if not data:
        await callback.answer(get_text(callback.from_user.id, 'search_expired'), show_alert=True)
        return
    user_id = callback.from_user.id
    if not await check_subscription(user_id):
        await callback.message.answer(get_text(user_id, 'check_sub'), reply_markup=subscription_keyboard(user_id))
        await callback.answer()
        return
    await callback.answer()
    selected_song = data['results'][index]
    video_url = selected_song.get('url')
    if not video_url:
        vid_id = selected_song.get('id')
        if vid_id:
            video_url = f"https://www.youtube.com/watch?v={vid_id}"
    if not video_url:
        await callback.message.answer(get_text(user_id, 'no_url_found'))
        return
    processing_msg = await callback.message.answer(get_text(user_id, 'downloading'))
    audio_path = None
    try:
        audio_path, title, uploader = await download_audio_from_url(video_url, user_id)
        if audio_path and os.path.exists(audio_path):
            audio_file = FSInputFile(audio_path)
            await callback.message.answer_audio(audio_file, title=title, performer=uploader, caption=f"🎵 {uploader} - {title}")
            await processing_msg.delete()
        else:
            await processing_msg.edit_text(get_text(user_id, 'error'))
    except Exception as e:
        logger.error(f"Download error: {e}")
        await processing_msg.edit_text(get_text(user_id, 'error'))
    finally:
        if audio_path and os.path.exists(audio_path):
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
