import os
import shutil
import subprocess
from datetime import datetime


def render(video_path: str, audio_path: str, srt_path: str, config: dict, log) -> str:
    """Composites background video + voiceover + subtitles into portrait MP4 via FFmpeg."""
    if not shutil.which('ffmpeg'):
        raise RuntimeError('FFmpeg not in PATH — install from ffmpeg.org')

    style    = config.get('subtitleStyle', 'bottom-strip')
    music    = config.get('music', True)

    ts          = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = os.path.join('output', f'reel_{ts}.mp4')

    # Scale any source to portrait 1080x1920, maintaining aspect ratio + center crop
    vf_base = 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920'

    if style != 'none':
        srt_esc  = _escape_path(srt_path)
        force_st = _sub_style(style)
        vf_subs  = f",subtitles='{srt_esc}':force_style='{force_st}'"
    else:
        vf_subs = ''

    log(f'  -> Portrait 1080x1920 | subtitles: {style}', 'render')

    use_bg_audio = music and _has_audio(video_path)

    if use_bg_audio:
        filter_complex = (
            f"[0:v]{vf_base}{vf_subs}[v];"
            "[0:a]volume=0.08[bga];"
            "[1:a][bga]amix=inputs=2:duration=first:dropout_transition=1[a]"
        )
        cmd = [
            'ffmpeg', '-y',
            '-stream_loop', '-1', '-i', video_path,
            '-i', audio_path,
            '-filter_complex', filter_complex,
            '-map', '[v]', '-map', '[a]',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
            '-c:a', 'aac', '-b:a', '192k',
            '-shortest', '-movflags', '+faststart',
            output_path,
        ]
    else:
        vf = vf_base + vf_subs
        cmd = [
            'ffmpeg', '-y',
            '-stream_loop', '-1', '-i', video_path,
            '-i', audio_path,
            '-vf', vf,
            '-map', '0:v', '-map', '1:a',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
            '-c:a', 'aac', '-b:a', '192k',
            '-shortest', '-movflags', '+faststart',
            output_path,
        ]

    log('  -> Running FFmpeg...', 'render')
    proc = subprocess.run(
        cmd, capture_output=True,
        encoding='utf-8', errors='replace',
    )

    if proc.returncode != 0:
        # Surface the last 800 chars of stderr for diagnosis
        raise RuntimeError(f'FFmpeg failed:\n{proc.stderr[-800:]}')

    size_mb = os.path.getsize(output_path) / 1024 / 1024
    log(f'  -> Saved: {output_path} ({size_mb:.1f} MB)', 'render')
    return output_path


def _escape_path(path: str) -> str:
    """Escape path for FFmpeg subtitles filter."""
    path = os.path.abspath(path).replace('\\', '/')
    # Windows drive letter colon must be escaped in FFmpeg filter syntax
    if len(path) >= 2 and path[1] == ':':
        path = path[0] + '\\:' + path[2:]
    path = path.replace("'", "\\'")
    return path


def _sub_style(style: str) -> str:
    # Bold white letters only — no background box, outline for readability over any footage.
    return 'FontSize=18,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,BorderStyle=1,Alignment=2,MarginV=70'


def _has_audio(video_path: str) -> bool:
    """Returns True if video file has at least one audio stream."""
    result = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-select_streams', 'a',
         '-show_entries', 'stream=codec_type',
         '-of', 'default=noprint_wrappers=1:nokey=1', video_path],
        capture_output=True, text=True,
    )
    return bool(result.stdout.strip())
