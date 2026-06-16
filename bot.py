import asyncio
import os
import uuid
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
        'subscribed': "✅ Kanallarga muvaffaqiyatli obuna bo'ldingiz!\n\n📥 Quyidagilardan birini yuboring:\n\n▫️ Video, TikTok, Instagram, YouTube havolasi\n▫️ Qo'shiq nomi, ijrochi yoki matni\n▫️ Ovozli xabar yoki Video xabar\n▫️ Audio yoki Video fayl",
        'not_subscribed': "❌ Siz hali kanallarga obuna bo'lmadingiz!\n\nIltimos, avval kanallarga obuna bo'ling va qayta tekshiring.",
        'processing': "⏳ Qidirilmoqda...",
        'song_found': "🎵 Topilgan qo'shiq:\n\n🎤 Ijrochi: {artist}\n📀 Nomi: {title}",
        'song_not_found': "❌ Kechirasiz, qo'shiqni aniqlay olmadim.",
        'error': "❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.",
        'invalid_url': "❌ Noto'g'ri havola yuborildi."
    },
    'ru': {
        'welcome': "👋 Здравствуйте {user}!\n\nДобро пожаловать в бот!\n\n🌐 Пожалуйста, выберите язык:",
        'check_sub': "📢 Пожалуйста, подпишитесь на следующие каналы для использования бота:",
        'check_button': "✅ Проверить",
        'subscribed': "✅ Вы успешно подписались!\n\n📥 Отправьте одно из следующего:\n\n▫️ Ссылка (TikTok, Instagram, YouTube)\n▫️ Название песни, исполнитель или текст\n▫️ Голосовое или Видео сообщение\n▫️ Аудио или Видео файл",
        'not_subscribed': "❌ Вы еще не подписались!\n\nПожалуйста, сначала подпишитесь и проверьте снова.",
        'processing': "⏳ Поиск...",
        'song_found': "🎵 Найденная песня:\n\n🎤 Исполнитель: {artist}\n📀 Название: {title}",
        'song_not_found': "❌ Извините, не удалось распознать песню.",
        'error': "❌ Произошла ошибка. Попробуйте снова.",
        'invalid_url': "❌ Неверная ссылка."
    },
    'en': {
        'welcome': "👋 Hello {user}!\n\nWelcome to the bot!\n\n🌐 Please select a language:",
        'check_sub': "📢 Please subscribe to the following channels to use the bot:",
        'check_button': "✅ Check",
        'subscribed': "✅ Successfully subscribed!\n\n📥 Send one of the following:\n\n▫️ Link (TikTok, Instagram, YouTube)\n▫️ Song name, artist or lyrics\n▫️ Voice or Video message\n▫️ Audio or Video file",
        'not_subscribed': "❌ You haven't subscribed yet!\n\nPlease subscribe first and check again.",
        'processing': "⏳ Searching...",
        'song_found': "🎵 Found song:\n\n🎤 Artist: {artist}\n📀 Title: {title}",
        'song_not_found': "❌ Sorry, couldn't identify the song.",
        'error': "❌ An error occurred. Try again.",
        'invalid_url': "❌ Invalid link."
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

# ========== Yordamchi funksiyalar ==========
user_languages_cache = {}

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

def get_text(user_id, key):
    lang = user_languages_cache.get(user_id, 'uz')
    return TEXTS[lang].get(key, TEXTS['uz'][key])

def language_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")
        ]
    ])

def subscription_keyboard(user_id):
    buttons = []
    for channel in CHANNELS:
        buttons.append([InlineKeyboardButton(text=f"📢 {channel}", url=f"https://t.me/{channel[1:]}")])
    buttons.append([InlineKeyboardButton(text=get_text(user_id, 'check_button'), callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

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

async def download_audio_from_url(url, user_id):
    """Linkdan faqat audioni yuklab olish"""
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
        logger.error(f"yt-dlp error: {e}")
        return None, None, None

async def download_full_song(query, user_id):
    """Qo'shiq nomi bo'yicha to'liq versiyasini YouTube'dan yuklab olish"""
    try:
        temp_id = str(uuid.uuid4())[:8]
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'downloads/{user_id}_{temp_id}_%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'quiet': True,
            'no_warnings': True,
            'default_search': 'ytsearch1',
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

async def recognize_with_shazam(file_data):
    """Shazam orqali qo'shiqni aniqlash"""
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

# ========== Handlers ==========
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    if not await check_subscription(user_id):
        await message.answer(
            get_text(user_id, 'check_sub'),
            reply_markup=subscription_keyboard(user_id)
        )
        return

    await message.answer(
        TEXTS['uz']['welcome'].format(user=user_name),
        reply_markup=language_keyboard()
    )
    await state.set_state(UserState.language)

@router.callback_query(F.data.startswith("lang_"))
async def choose_language(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[1]
    
    await database.update_user_language(callback.from_user.id, lang)
    user_languages_cache[callback.from_user.id] = lang
    
    is_subscribed = await check_subscription(callback.from_user.id)
    
    if is_subscribed:
        await callback.message.edit_text(get_text(callback.from_user.id, 'subscribed'))
        await state.set_state(UserState.main_menu)
    else:
        await callback.message.edit_text(
            get_text(callback.from_user.id, 'check_sub'),
            reply_markup=subscription_keyboard(callback.from_user.id)
        )
    await callback.answer()

@router.callback_query(F.data == "check_sub")
async def check_sub(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    is_subscribed = await check_subscription(user_id)
    
    if is_subscribed:
        user_name = callback.from_user.first_name
        current_state = await state.get_state()
        
        if current_state == UserState.main_menu.state:
            await callback.message.edit_text(get_text(user_id, 'subscribed'))
        else:
            await callback.message.edit_text(
                TEXTS['uz']['welcome'].format(user=user_name),
                reply_markup=language_keyboard()
            )
            await state.set_state(UserState.language)
    else:
        await callback.answer(get_text(user_id, 'not_subscribed'), show_alert=True)

async def process_found_song(message: Message, song_info: dict, user_id: int, processing_msg: Message):
    """Topilgan qo'shiqni to'liq yuklab olib yuborish"""
    await processing_msg.edit_text(
        get_text(user_id, 'song_found').format(
            artist=song_info['artist'],
            title=song_info['title']
        ) + "\n\n⏳ To'liq audioni yuklayapman..."
    )
    
    query = f"{song_info['artist']} - {song_info['title']} audio"
    full_audio_path, title, artist = await download_full_song(query, user_id)
    
    if full_audio_path and os.path.exists(full_audio_path):
        try:
            audio_file = FSInputFile(full_audio_path)
            await message.answer_audio(
                audio_file,
                title=song_info['title'],
                performer=song_info['artist'],
                caption=f"🎵 {song_info['artist']} - {song_info['title']}"
            )
            await processing_msg.delete()
        except Exception as e:
            logger.error(f"Send audio error: {e}")
            await processing_msg.edit_text(get_text(user_id, 'error'))
        finally:
            if os.path.exists(full_audio_path):
                os.remove(full_audio_path)
    else:
        await processing_msg.edit_text(get_text(user_id, 'error'))

@router.message(F.text & F.text.startswith(("http://", "https://")))
async def handle_url(message: Message):
    user_id = message.from_user.id
    
    if not await check_subscription(user_id):
        await message.answer(get_text(user_id, 'check_sub'), reply_markup=subscription_keyboard(user_id))
        return
    
    url = message.text
    processing_msg = await message.answer(get_text(user_id, 'processing'))
    
    audio_path = None
    try:
        audio_path, title, uploader = await download_audio_from_url(url, user_id)
        
        if audio_path and os.path.exists(audio_path):
            song_info = await recognize_with_shazam(audio_path)
            
            if song_info:
                # Agar topsa to'liq qo'shiqni topib yuboradi
                await process_found_song(message, song_info, user_id, processing_msg)
            else:
                # Topolmasa o'zidan olingan audioni yuboradi
                await processing_msg.edit_text(get_text(user_id, 'song_not_found'))
                audio_file = FSInputFile(audio_path)
                await message.answer_audio(audio_file, title=title, performer=uploader)
        else:
            await processing_msg.edit_text(get_text(user_id, 'invalid_url'))
    finally:
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except:
                pass

@router.message(F.voice | F.audio | F.video | F.video_note)
async def handle_media(message: Message):
    user_id = message.from_user.id
    
    if not await check_subscription(user_id):
        await message.answer(get_text(user_id, 'check_sub'), reply_markup=subscription_keyboard(user_id))
        return
    
    processing_msg = await message.answer(get_text(user_id, 'processing'))
    
    try:
        if message.voice:
            file_id = message.voice.file_id
        elif message.audio:
            file_id = message.audio.file_id
        elif message.video:
            file_id = message.video.file_id
        elif message.video_note:
            file_id = message.video_note.file_id
            
        file_io = await bot.download(file_id)
        if file_io:
            file_data = file_io.read()
            song_info = await recognize_with_shazam(file_data)
            
            if song_info:
                await process_found_song(message, song_info, user_id, processing_msg)
            else:
                await processing_msg.edit_text(get_text(user_id, 'song_not_found'))
        else:
            await processing_msg.edit_text(get_text(user_id, 'error'))
            
    except Exception as e:
        logger.error(f"Media handle error: {e}")
        await processing_msg.edit_text(get_text(user_id, 'error'))

@router.message(F.text & ~F.text.startswith(("http://", "https://", "/")))
async def handle_text_search(message: Message):
    user_id = message.from_user.id
    
    if not await check_subscription(user_id):
        await message.answer(get_text(user_id, 'check_sub'), reply_markup=subscription_keyboard(user_id))
        return
    
    search_query = message.text.strip()
    processing_msg = await message.answer(get_text(user_id, 'processing'))
    
    audio_path = None
    try:
        audio_path, title, artist = await download_full_song(search_query, user_id)
        
        if audio_path and os.path.exists(audio_path):
            audio_file = FSInputFile(audio_path)
            await message.answer_audio(
                audio_file,
                title=title,
                performer=artist,
                caption=f"🎵 {artist} - {title}"
            )
            await processing_msg.delete()
        else:
            await processing_msg.edit_text(get_text(user_id, 'song_not_found'))
    except Exception as e:
        logger.error(f"Search error: {e}")
        await processing_msg.edit_text(get_text(user_id, 'error'))
    finally:
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except:
                pass

# ========== ASOSIY ==========
async def main():
    await database.init_db()
    os.makedirs('downloads', exist_ok=True)
    dp.include_router(router)
    
    logger.info("Bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())