import os, json, shutil
from datetime import datetime

_READY_DIR = 'ready_to_post'


def run(config: dict, q) -> None:
    from . import script_gen, tts, footage, subtitles, render, posting, sourcing, curation

    os.makedirs('output', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    os.makedirs(_READY_DIR, exist_ok=True)

    def ts():
        return datetime.now().strftime('%H:%M:%S')

    def log(msg, step=None, status='running'):
        q.put({'type': 'log', 'message': msg, 'step': step, 'status': status, 'time': ts()})

    def err(msg):
        q.put({'type': 'error', 'message': msg, 'time': ts()})

    try:
        log('Pipeline started', 'init', 'done')

        niche = config.get('niche', 'science-facts')
        topic = config.get('topic', '').strip()

        log('Generating script...', 'script', 'running')

        if topic:
            story = {
                'title': topic, 'summary': topic,
                'hook_angles': [], 'source_name': 'User-specified topic',
            }
        else:
            if sourcing.is_stale(niche):
                log(f'Sourcing stories for {niche}...', 'script', 'running')
                sourcing.refresh(niche, log)
                picks = curation.curate(niche, log)
            else:
                picks = curation.load_latest(niche) or curation.curate(niche, log)

            if not picks:
                raise RuntimeError(f'No stories survived curation for "{niche}" — try again shortly')

            story = picks[0]
            log(f'  -> Selected: "{story.get("title", "")}" [{story.get("bucket", "")}]', 'script')

        script = script_gen.generate_from_story(story, niche, config, log)
        log(f'Script ready — {len(script.split())} words', 'script', 'done')

        log('Synthesising voiceover with edge-tts...', 'tts', 'running')
        audio_path = tts.generate(script, config, log)
        log(f'Voiceover: {audio_path}', 'tts', 'done')

        log('Fetching background footage...', 'footage', 'running')
        video_path = footage.fetch(config, log)
        log(f'Footage: {video_path}', 'footage', 'done')

        log('Transcribing with Whisper...', 'subtitles', 'running')
        srt_path = subtitles.generate(audio_path, config, log)
        log(f'Subtitles: {srt_path}', 'subtitles', 'done')

        log('Rendering with FFmpeg...', 'render', 'running')
        output_path = render.render(video_path, audio_path, srt_path, config, log)
        log(f'Video: {output_path}', 'render', 'done')

        ready_path = _copy_to_ready(output_path, niche)
        log(f'  -> Copied for manual upload: {ready_path}', 'render')

        platforms = config.get('platforms', [])
        if platforms:
            log(f'Posting to {", ".join(platforms)}...', 'post', 'running')
            posting.post(output_path, config, log)
            log('Posted successfully', 'post', 'done')
        else:
            log('No platforms selected — skipping post', 'post', 'done')

        _save_history(config, output_path)
        q.put({'type': 'done', 'output': output_path, 'time': ts()})

    except Exception as exc:
        err(f'Pipeline failed: {exc}')


def _copy_to_ready(output_path: str, niche: str) -> str:
    """Copies the finished reel into a clutter-free folder for manual TikTok/IG upload."""
    os.makedirs(_READY_DIR, exist_ok=True)
    fname = f'{niche}_{os.path.basename(output_path)}'
    dest  = os.path.join(_READY_DIR, fname)
    shutil.copy(output_path, dest)
    return dest


def _save_history(config: dict, output_path: str) -> None:
    history_file = 'data/history.json'
    history = []
    if os.path.exists(history_file):
        with open(history_file) as f:
            try:
                history = json.load(f)
            except json.JSONDecodeError:
                history = []
    history.insert(0, {
        'date': datetime.now().isoformat(),
        'niche': config.get('niche', ''),
        'tone': config.get('tone', ''),
        'duration': config.get('duration', 60),
        'platforms': config.get('platforms', []),
        'output': output_path,
    })
    with open(history_file, 'w') as f:
        json.dump(history[:50], f, indent=2)
