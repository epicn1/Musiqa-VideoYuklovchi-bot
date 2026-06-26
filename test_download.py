import asyncio
import os
import uuid
import yt_dlp
import shutil
import subprocess

def ffmpeg_available():
    return shutil.which('ffmpeg') is not None

def audio_download_opts(output_template):
    """Audio yuklash sozlamasi: ffmpeg bo'lsa MP3, bo'lmasa m4a/original audio."""
    opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'outtmpl': output_template,
        'noplaylist': True,
        'quiet': False,
        'no_warnings': False,
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
    return opts

def find_downloaded_file(prefix, preferred_exts):
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

async def test_download_song_from_youtube(query):
    os.makedirs('downloads', exist_ok=True)
    temp_id = str(uuid.uuid4())[:8]
    ydl_opts = audio_download_opts(f'downloads/test_{temp_id}.%(ext)s')

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
                filename = find_downloaded_file(f'test_{temp_id}', ['.mp3', '.m4a', '.webm', '.opus', '.aac'])
            title = info.get('title', 'Unknown')
            artist = info.get('artist') or info.get('uploader') or info.get('channel') or 'Unknown'
            return filename, title, artist

    return await asyncio.to_thread(_download)

if __name__ == "__main__":
    import asyncio
    print(asyncio.run(test_download_song_from_youtube("Botir Qodirov Xorazmli qizlar")))
