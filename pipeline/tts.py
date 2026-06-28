import asyncio
import os
from datetime import datetime


# Voices with a naturally deep/gravelly timbre get a pitch-down nudge for a
# raspier, more ominous narrator feel — useful for horror/true-crime content.
_PITCH_OFFSET = {
    'en-US-ChristopherNeural': -20,
    'en-GB-ThomasNeural':      -15,
    'en-US-EricNeural':        -15,
}


def generate(script: str, config: dict, log) -> str:
    """Calls edge-tts (Microsoft Edge TTS, free) to synthesise speech."""
    try:
        import edge_tts
    except ImportError:
        raise RuntimeError('edge-tts not installed — run: pip install edge-tts')

    voice = config.get('voice', 'en-US-GuyNeural')
    speed = float(config.get('speed', 1.0))

    # edge-tts rate is a signed percentage string: +10%, -20%, etc.
    rate_pct = int((speed - 1.0) * 100)
    rate = f'+{rate_pct}%' if rate_pct >= 0 else f'{rate_pct}%'

    pitch_hz = _PITCH_OFFSET.get(voice, 0)
    pitch    = f'+{pitch_hz}Hz' if pitch_hz >= 0 else f'{pitch_hz}Hz'

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = os.path.join('output', f'voiceover_{ts}.mp3')

    log(f'  -> Voice: {voice} | Rate: {rate} | Pitch: {pitch}', 'tts')
    log(f'  -> {len(script.split())} words | {len(script)} chars', 'tts')

    async def _synth():
        communicate = edge_tts.Communicate(script, voice, rate=rate, pitch=pitch)
        await communicate.save(output_path)

    try:
        asyncio.run(_synth())
    except Exception as exc:
        raise RuntimeError(f'edge-tts failed: {exc}')

    size_kb = os.path.getsize(output_path) / 1024
    log(f'  -> Saved: {output_path} ({size_kb:.0f} KB)', 'tts')

    return output_path
