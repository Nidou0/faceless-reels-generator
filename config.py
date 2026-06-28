import os


def _load_env() -> None:
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if not os.path.exists(env_file):
        return
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, _, v = line.partition('=')
                os.environ.setdefault(k.strip(), v.strip())


_load_env()

LLM_PROVIDER         = os.getenv('LLM_PROVIDER', 'claude')
ANTHROPIC_API_KEY    = os.getenv('ANTHROPIC_API_KEY', '')
CLAUDE_MODEL         = os.getenv('CLAUDE_MODEL', 'claude-haiku-4-5-20251001')
GEMINI_API_KEY       = os.getenv('GEMINI_API_KEY', '')
GEMINI_MODEL         = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
PEXELS_API_KEY       = os.getenv('PEXELS_API_KEY', '')
PIXABAY_API_KEY      = os.getenv('PIXABAY_API_KEY', '')
YOUTUBE_CLIENT_ID    = os.getenv('YOUTUBE_CLIENT_ID', '')
YOUTUBE_CLIENT_SECRET = os.getenv('YOUTUBE_CLIENT_SECRET', '')
OUTPUT_DIR           = 'output'
HISTORY_FILE         = 'data/history.json'
