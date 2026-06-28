import os
import shutil
from datetime import datetime

_MAX_WORDS = 4  # TikTok-style: short bursts


def generate(audio_path: str, config: dict, log) -> str:
    """Transcribes audio with Whisper word timestamps, writes 4-word-chunk SRT."""
    try:
        import whisper
    except ImportError:
        raise RuntimeError('openai-whisper not installed — run: pip install openai-whisper')

    if not shutil.which('ffmpeg'):
        raise RuntimeError('FFmpeg not in PATH')

    model_name = config.get('whisperModel', 'base.en')
    log(f'  -> Loading Whisper ({model_name})...', 'subtitles')
    model = whisper.load_model(model_name)

    log('  -> Transcribing with word timestamps...', 'subtitles')
    result = model.transcribe(audio_path, word_timestamps=True, verbose=False)

    # Extract word-level timing
    words = []
    for seg in result.get('segments', []):
        for w in seg.get('words', []):
            word = w.get('word', '').strip()
            if word:
                words.append({'word': word, 'start': w['start'], 'end': w['end']})

    if not words:
        log('  -> No word timestamps, falling back to segments', 'subtitles')
        words = _flatten_segments(result.get('segments', []))

    chunks = _chunk(words, _MAX_WORDS)
    log(f'  -> {len(words)} words -> {len(chunks)} subtitle entries', 'subtitles')

    ts       = datetime.now().strftime('%Y%m%d_%H%M%S')
    srt_path = os.path.join('output', f'subtitles_{ts}.srt')

    with open(srt_path, 'w', encoding='utf-8') as f:
        f.write(_to_srt(chunks))

    log(f'  -> Saved: {srt_path}', 'subtitles')
    return srt_path


def _chunk(words: list, size: int) -> list:
    out = []
    for i in range(0, len(words), size):
        g = words[i:i + size]
        out.append({
            'text':  ' '.join(w['word'] for w in g),
            'start': g[0]['start'],
            'end':   g[-1]['end'],
        })
    return out


def _flatten_segments(segments: list) -> list:
    """Distribute segment text evenly across its time range."""
    words = []
    for seg in segments:
        parts = seg['text'].strip().split()
        if not parts:
            continue
        dur = (seg['end'] - seg['start']) / len(parts)
        for i, w in enumerate(parts):
            words.append({
                'word':  w,
                'start': seg['start'] + i * dur,
                'end':   seg['start'] + (i + 1) * dur,
            })
    return words


def _to_srt(chunks: list) -> str:
    lines = []
    for i, c in enumerate(chunks, 1):
        text = c['text'].strip()
        if not text:
            continue
        lines.append(f"{i}\n{_fmt(c['start'])} --> {_fmt(c['end'])}\n{text}\n")
    return '\n'.join(lines)


def _fmt(s: float) -> str:
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f'{int(h):02d}:{int(m):02d}:{int(sec):02d},{int((s % 1) * 1000):03d}'
