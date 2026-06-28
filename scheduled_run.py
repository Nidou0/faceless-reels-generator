"""Standalone entry point for Windows Task Scheduler — generates one video,
rotating through all niches across calls. No Flask/UI needed.

Run manually to test: python scheduled_run.py
"""
import json
import os
import sys

from pipeline import runner

_NICHES = [
    'scary-stories', 'scp-stories', 'history-facts', 'mythology',
    'true-crime', 'life-advice', 'science-facts', 'trending-news',
]
_STATE_FILE = os.path.join('data', 'schedule_state.json')

_PLATFORMS: list[str] = ['youtube']


def _next_niche() -> str:
    state = {'index': 0}
    if os.path.exists(_STATE_FILE):
        try:
            with open(_STATE_FILE) as f:
                state = json.load(f)
        except json.JSONDecodeError:
            pass
    niche = _NICHES[state.get('index', 0) % len(_NICHES)]
    state['index'] = state.get('index', 0) + 1
    os.makedirs('data', exist_ok=True)
    with open(_STATE_FILE, 'w') as f:
        json.dump(state, f)
    return niche


class _PrintQueue:
    """Mimics the Queue interface runner.run() expects, prints live instead of buffering."""
    def __init__(self):
        self.failed = False

    def put(self, msg: dict) -> None:
        text = msg.get('message') or msg.get('type', '')
        print(f"[{msg.get('time', '')}] {text}")
        if msg.get('type') == 'error':
            self.failed = True


def main() -> int:
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
        'platforms':     _PLATFORMS,
        'autoTitle':     True,
        'autoHashtags':  True,
    }

    print(f'=== Scheduled run: niche={niche} ===')
    q = _PrintQueue()
    runner.run(config, q)
    print('=== Failed ===' if q.failed else '=== Done ===')
    return 1 if q.failed else 0


if __name__ == '__main__':
    sys.exit(main())
