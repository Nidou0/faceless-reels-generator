"""Real posting: YouTube Data API v3, TikTok via browser automation.

TikTok posting drives the web upload UI directly (no official API) — violates
TikTok ToS, ban risk accepted by user. See pipeline/tiktok_poster.py.
Instagram is not implemented yet.
"""
import json
import os
import re

from . import llm

_CLIENT_SECRET_FILE = os.path.join('data', 'youtube_client_secret.json')
_TOKEN_FILE          = os.path.join('data', 'youtube_token.json')
_SCOPES              = ['https://www.googleapis.com/auth/youtube.upload']

_PRIVACY_STATUS = 'public'


def _safe_for_console(text: str) -> str:
    """Strips characters the Windows console can't encode (e.g. emoji) for log lines only —
    the real title/hashtags sent to the API keep emoji intact, that's fine over HTTP."""
    enc = __import__('sys').stdout.encoding or 'utf-8'
    return text.encode(enc, errors='replace').decode(enc)


def post(video_path: str, config: dict, log) -> None:
    platforms     = config.get('platforms', [])
    auto_title    = config.get('autoTitle', True)
    auto_hashtags = config.get('autoHashtags', True)

    title, hashtags = ('', [])
    if auto_title or auto_hashtags:
        title, hashtags = _generate_metadata(config, log)

    for platform in platforms:
        if platform == 'youtube':
            _post_youtube(video_path, title, hashtags, log)
        elif platform == 'tiktok':
            _post_tiktok(video_path, title, hashtags, log)
        elif platform == 'instagram':
            log(f'  -> {platform} posting not yet implemented — skipping', 'post')
        else:
            log(f'  -> Unknown platform: {platform}', 'post')


_BROAD_TAGS = ['#shorts', '#fyp', '#viral']


def _generate_metadata(config: dict, log) -> tuple:
    niche = config.get('niche', '')
    log('  -> Generating title + hashtags...', 'post')

    prompt = (
        f"Write a viral, curiosity-driven YouTube Shorts/TikTok title (under 60 chars so it "
        f"never truncates on mobile) and 6 relevant niche-specific hashtags for a "
        f"{niche.replace('-', ' ')} short video. "
        f"Title rules: create genuine curiosity or shock, match what the video actually "
        f"delivers (no misleading clickbait that hurts retention), no emoji, no quotation marks. "
        f"Hashtag rules: specific to the content and niche (not generic filler) — broad reach "
        f"tags like #shorts/#fyp/#viral are added separately, don't include them here.\n"
        f'Output strict JSON only: {{"title": "...", "hashtags": ["...", ...]}}'
    )
    try:
        text  = llm.complete(
            'You write viral short-form video titles and hashtags optimized for the '
            'YouTube Shorts and TikTok algorithms. Output only JSON.',
            prompt, max_tokens=300, temperature=0.9, log=log,
        )
        match = re.search(r'\{.*\}', text, re.DOTALL)
        data  = json.loads(match.group()) if match else {}
        title = data.get('title') or niche.replace('-', ' ').title()
        niche_tags = data.get('hashtags') or [f'#{niche.replace("-", "")}']
    except Exception as exc:
        log(f'  -> Metadata generation failed, using fallback: {exc}', 'post')
        title, niche_tags = niche.replace('-', ' ').title(), [f'#{niche.replace("-", "")}']

    # Broad discovery tags are forced in regardless of what the LLM returned —
    # don't rely on it remembering the Shorts-classification signal.
    tags = _BROAD_TAGS + [t for t in niche_tags if t.lower() not in _BROAD_TAGS]
    log(f'  -> Title: "{_safe_for_console(title)}"', 'post')
    log(f'  -> Tags: {" ".join(tags)}', 'post')
    return title, tags


def _get_youtube_client():
    if not os.path.exists(_CLIENT_SECRET_FILE):
        raise RuntimeError(
            f'YouTube not configured — download an OAuth client secret (Desktop app type) '
            f'from Google Cloud Console and save it as {_CLIENT_SECRET_FILE}'
        )

    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = None
    if os.path.exists(_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(_TOKEN_FILE, _SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(_CLIENT_SECRET_FILE, _SCOPES)
            creds = flow.run_local_server(port=0)
        with open(_TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())

    return build('youtube', 'v3', credentials=creds)


def _post_youtube(video_path: str, title: str, hashtags: list, log) -> None:
    log('  -> Authenticating with YouTube...', 'post')
    try:
        youtube = _get_youtube_client()
    except Exception as exc:
        raise RuntimeError(f'YouTube auth failed: {exc}')

    # #Shorts in the title is the strongest, most reliable signal for Shorts-shelf
    # classification — don't rely solely on aspect ratio/duration auto-detection.
    title_with_tag = title if '#shorts' in title.lower() else f'{title} #Shorts'

    description = ' '.join(hashtags)
    body = {
        'snippet': {
            'title':       title_with_tag[:100],
            'description': description[:5000],
            'tags':        [h.lstrip('#') for h in hashtags],
            'categoryId':  '24',  # Entertainment
        },
        'status': {
            'privacyStatus':           _PRIVACY_STATUS,
            'selfDeclaredMadeForKids': False,
        },
    }

    from googleapiclient.http import MediaFileUpload
    media = MediaFileUpload(video_path, mimetype='video/mp4', resumable=True)

    log(f'  -> Uploading "{_safe_for_console(title)}" to YouTube ({_PRIVACY_STATUS})...', 'post')
    try:
        request  = youtube.videos().insert(part='snippet,status', body=body, media_body=media)
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                log(f'  -> Upload progress: {int(status.progress() * 100)}%', 'post')
    except Exception as exc:
        raise RuntimeError(f'YouTube upload failed: {exc}')

    video_id = response.get('id')
    log(f'  -> Published: https://youtube.com/shorts/{video_id}', 'post')


def _post_tiktok(video_path: str, title: str, hashtags: list, log) -> None:
    from . import tiktok_poster
    caption = f'{title} {" ".join(hashtags)}'
    tiktok_poster.post(video_path, caption, log)
