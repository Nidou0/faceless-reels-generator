"""One-off batch: generate N videos for manual TikTok upload (no auto-posting).

Run manually: python batch_tiktok.py [count]
"""
import sys

from pipeline import runner
from scheduled_run import _next_niche, _PrintQueue


def main(count: int) -> None:
    for i in range(count):
        niche = _next_niche()
        config = {
            'niche':         niche,
            'topic':         '',
            'persona':       '',
            'tone':          'dramatic',
            'voice':         'en-US-GuyNeural',
            'speed':         1.3,
            'duration':      60,
            'language':      'en',
            'background':    'minecraft-parkour',
            'subtitleStyle': 'bottom-strip',
            'music':         True,
            'platforms':     [],
            'autoTitle':     True,
            'autoHashtags':  True,
        }
        print(f'=== [{i + 1}/{count}] niche={niche} ===')
        runner.run(config, _PrintQueue())


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    main(n)
