"""Background footage: long-form gameplay/POV video downloaded once via yt-dlp,
cached locally, randomly sliced per run.

Classic 'brain rot' background strategy — Minecraft parkour / construction POV /
satisfying footage fits any narration since viewers watch it for stimulation,
not relevance. Each style maps to one long source video; every run picks a
random start offset so output never repeats the same segment.
"""
import os
import random
import subprocess
import urllib.request
from datetime import datetime

_CACHE_DIR = os.path.join('assets', 'footage_cache')

# Long-form source videos, explicitly labeled free-to-use/no-copyright by uploader.
# Verify license terms yourself before commercial use.
_SOURCE_URL = {
    'minecraft-parkour': 'https://www.youtube.com/watch?v=85z7jqGAGcc',
    'construction-pov':  'https://www.youtube.com/watch?v=kJaN003uNK4',
}

# Pre-trimmed (<2GB) re-encodes hosted as GitHub Release assets — the fast,
# reliable path for ephemeral CI runners. yt-dlp from YouTube is the fallback
# (slower, and cloud datacenter IPs get rate-limited/blocked by YouTube).
_RELEASE_URL = {
    'minecraft-parkour': 'https://github.com/REPLACE_OWNER/REPLACE_REPO/releases/download/footage-v1/minecraft_parkour_clip.mp4',
}


def fetch(config: dict, log) -> str:
    style    = config.get('background', 'minecraft-parkour')
    duration = config.get('duration', 60) + 8

    cache_dir = os.path.join(_CACHE_DIR, style)
    os.makedirs(cache_dir, exist_ok=True)

    src = _cached_source(cache_dir)
    if not src:
        src = _fetch_release_asset(style, cache_dir, log)
    if not src:
        url = _SOURCE_URL.get(style)
        if not url:
            raise RuntimeError(f'No source configured for background style "{style}"')
        log(f'  -> Downloading source footage for "{style}" via yt-dlp (one-time)...', 'footage')
        src = _download_source(url, cache_dir, log)

    log(f'  -> Using cached footage: {os.path.basename(src)}', 'footage')

    ts  = datetime.now().strftime('%Y%m%d_%H%M%S')
    out = os.path.join('output', f'background_{ts}.mp4')
    _extract_segment(src, out, duration, log)
    return out


def _cached_source(cache_dir: str) -> str | None:
    files = [f for f in os.listdir(cache_dir) if f.endswith('.mp4')]
    if not files:
        return None
    return os.path.join(cache_dir, files[0])


def _fetch_release_asset(style: str, cache_dir: str, log) -> str | None:
    url = _RELEASE_URL.get(style)
    if not url:
        return None

    path = os.path.join(cache_dir, 'source.mp4')
    log(f'  -> Fetching pre-trimmed footage for "{style}" from release asset...', 'footage')
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=120) as resp:
            with open(path, 'wb') as f:
                while True:
                    chunk = resp.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
    except Exception as exc:
        log(f'  -> Release asset fetch failed ({exc}), falling back to yt-dlp', 'footage')
        if os.path.exists(path):
            os.remove(path)
        return None

    size_mb = os.path.getsize(path) / 1024 / 1024
    log(f'  -> Cached: {path} ({size_mb:.1f} MB)', 'footage')
    return path


def _download_source(url: str, cache_dir: str, log) -> str:
    out_tmpl = os.path.join(cache_dir, 'source.%(ext)s')
    cmd = [
        'yt-dlp',
        '-f', 'bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080][ext=mp4]/best',
        '--merge-output-format', 'mp4',
        '-o', out_tmpl,
        url,
    ]
    proc = subprocess.run(cmd, capture_output=True, encoding='utf-8', errors='replace')
    if proc.returncode != 0:
        raise RuntimeError(f'yt-dlp download failed:\n{proc.stderr[-600:]}')

    files = [f for f in os.listdir(cache_dir) if f.endswith('.mp4')]
    if not files:
        raise RuntimeError('yt-dlp reported success but no mp4 found in cache dir')

    path = os.path.join(cache_dir, files[0])
    size_mb = os.path.getsize(path) / 1024 / 1024
    log(f'  -> Cached: {path} ({size_mb:.1f} MB)', 'footage')
    return path


def _extract_segment(src: str, out: str, duration: float, log) -> None:
    probe = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', src],
        capture_output=True, text=True,
    )
    try:
        src_dur = float(probe.stdout.strip())
    except ValueError:
        src_dur = duration

    max_start = max(0, src_dur - duration - 1)
    start     = random.uniform(0, max_start) if max_start > 0 else 0

    cmd = [
        'ffmpeg', '-y',
        '-ss', f'{start:.2f}', '-i', src,
        '-t', str(duration),
        '-an',
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
        out,
    ]
    proc = subprocess.run(cmd, capture_output=True, encoding='utf-8', errors='replace')
    if proc.returncode != 0:
        raise RuntimeError(f'Segment extraction failed:\n{proc.stderr[-400:]}')

    size_mb = os.path.getsize(out) / 1024 / 1024
    log(f'  -> Background: {out} ({size_mb:.1f} MB, start={start:.0f}s of {src_dur:.0f}s)', 'footage')
