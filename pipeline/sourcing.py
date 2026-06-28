"""Sourcing stage: pull per-niche RSS feeds, scrape posts/articles, cache as local markdown.

Local/free replacement for RSS.app + n8n scheduled scrape + S3 data lake. Every
niche gets its own source pool — news niches pull from tech/news feeds, fiction
niches pull real user-written stories from the relevant subreddits.
"""
import hashlib
import json
import os
import time
from datetime import datetime, timedelta

NICHE_SOURCES = {
    'trending-news': [
        ('Hacker News',            'https://news.ycombinator.com/rss'),
        ('Reddit Technology',      'https://www.reddit.com/r/technology/.rss'),
        ('Reddit Artificial',      'https://www.reddit.com/r/artificial/.rss'),
        ('Reddit MachineLearning', 'https://www.reddit.com/r/MachineLearning/.rss'),
        ('Reddit Futurology',      'https://www.reddit.com/r/Futurology/.rss'),
        ('Reddit News',            'https://www.reddit.com/r/news/.rss'),
        ('TechCrunch',             'https://techcrunch.com/feed'),
        ('The Verge',              'https://www.theverge.com/rss/index.xml'),
        ('Ars Technica',           'http://feeds.arstechnica.com/arstechnica/index/'),
        ('Wired',                  'https://www.wired.com/feed/rss'),
        ('VentureBeat AI',         'https://venturebeat.com/category/ai/feed/'),
        ('Google News AI',        'https://news.google.com/rss/search?q=artificial+intelligence+when:1d&hl=en-US&gl=US&ceid=US:en'),
        ('Google News Tech',      'https://news.google.com/rss/search?q=technology+when:1d&hl=en-US&gl=US&ceid=US:en'),
    ],
    'scary-stories': [
        ('Reddit NoSleep',           'https://www.reddit.com/r/nosleep/.rss'),
        ('Reddit ShortScaryStories', 'https://www.reddit.com/r/shortscarystories/.rss'),
        ('Reddit LetsNotMeet',       'https://www.reddit.com/r/LetsNotMeet/.rss'),
        ('Reddit TheTruthIsHere',    'https://www.reddit.com/r/Thetruthishere/.rss'),
    ],
    'scp-stories': [
        ('Reddit SCP',               'https://www.reddit.com/r/SCP/.rss'),
        ('Reddit SCPWritingWorkshop', 'https://www.reddit.com/r/SCPWritingWorkshop/.rss'),
    ],
    'mythology': [
        ('Reddit Mythology', 'https://www.reddit.com/r/mythology/.rss'),
        ('Reddit Folklore',  'https://www.reddit.com/r/Folklore/.rss'),
    ],
    'true-crime': [
        ('Reddit UnresolvedMysteries', 'https://www.reddit.com/r/UnresolvedMysteries/.rss'),
        ('Reddit TrueCrime',           'https://www.reddit.com/r/TrueCrime/.rss'),
        ('Google News True Crime',     'https://news.google.com/rss/search?q=true+crime+when:2d&hl=en-US&gl=US&ceid=US:en'),
    ],
    'life-advice': [
        ('Reddit LifeProTips',        'https://www.reddit.com/r/LifeProTips/.rss'),
        ('Reddit GetMotivated',       'https://www.reddit.com/r/GetMotivated/.rss'),
        ('Reddit DecidingToBeBetter', 'https://www.reddit.com/r/DecidingToBeBetter/.rss'),
    ],
    'science-facts': [
        ('Reddit Science',           'https://www.reddit.com/r/science/.rss'),
        ('Reddit EverythingScience', 'https://www.reddit.com/r/EverythingScience/.rss'),
        ('Reddit TodayILearned',     'https://www.reddit.com/r/todayilearned/.rss'),
    ],
    'history-facts': [
        ('Reddit History',       'https://www.reddit.com/r/history/.rss'),
        ('Reddit AskHistorians', 'https://www.reddit.com/r/AskHistorians/.rss'),
        ('Reddit TodayILearned', 'https://www.reddit.com/r/todayilearned/.rss'),
    ],
}

_DATA_DIR         = os.path.join('data', 'sourced')
_PER_SOURCE_LIMIT = 8
_WINDOW_HOURS     = 72


def _niche_dir(niche: str) -> str:
    return os.path.join(_DATA_DIR, niche)


def _index_path(niche: str) -> str:
    return os.path.join(_niche_dir(niche), 'index.json')


def is_stale(niche: str, max_age_hours: float = 4.0) -> bool:
    path = _index_path(niche)
    if not os.path.exists(path):
        return True
    age = time.time() - os.path.getmtime(path)
    return age > max_age_hours * 3600


def refresh(niche: str, log) -> int:
    """Pulls this niche's RSS sources, scrapes new posts, caches as markdown."""
    try:
        import feedparser
    except ImportError:
        raise RuntimeError('feedparser not installed — run: pip install feedparser')
    try:
        import trafilatura
    except ImportError:
        raise RuntimeError('trafilatura not installed — run: pip install trafilatura')

    # Reddit (and some others) reject the default feedparser/urllib user agent
    feedparser.USER_AGENT = (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/124.0 Safari/537.36'
    )

    sources = NICHE_SOURCES.get(niche, [])
    if not sources:
        log(f'  -> No sources configured for "{niche}"', 'script')
        return 0

    niche_dir = _niche_dir(niche)
    os.makedirs(niche_dir, exist_ok=True)
    index     = _load_index(niche)
    seen_urls = {e['url'] for e in index}
    new_count = 0
    cutoff    = datetime.now() - timedelta(hours=_WINDOW_HOURS)

    for source_name, feed_url in sources:
        log(f'  -> Fetching {source_name}...', 'script')
        try:
            feed = feedparser.parse(feed_url)
        except Exception as exc:
            log(f'  -> {source_name} failed: {exc}', 'script')
            continue

        for entry in feed.entries[:_PER_SOURCE_LIMIT]:
            url = entry.get('link', '')
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            title = entry.get('title', '').strip()
            if not title:
                continue

            markdown = None
            try:
                downloaded = trafilatura.fetch_url(url)
                if downloaded:
                    markdown = trafilatura.extract(downloaded, output_format='markdown')
            except Exception:
                pass

            content   = markdown or entry.get('summary', '') or title
            file_hash = hashlib.sha1(url.encode()).hexdigest()[:16]
            md_path   = os.path.join(niche_dir, f'{file_hash}.md')
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(content[:6000])

            index.append({
                'url':        url,
                'title':      title,
                'source':     source_name,
                'file':       f'{file_hash}.md',
                'fetched_at': datetime.now().isoformat(),
            })
            new_count += 1

    index = [e for e in index if datetime.fromisoformat(e['fetched_at']) > cutoff]
    _save_index(niche, index)

    log(f'  -> {new_count} new stories cached ({len(index)} total)', 'script')
    return new_count


def recent(niche: str, hours: float = _WINDOW_HOURS) -> list:
    index  = _load_index(niche)
    cutoff = datetime.now() - timedelta(hours=hours)
    return [e for e in index if datetime.fromisoformat(e['fetched_at']) > cutoff]


def load_markdown(niche: str, entry: dict) -> str:
    path = os.path.join(_niche_dir(niche), entry['file'])
    if not os.path.exists(path):
        return ''
    with open(path, encoding='utf-8') as f:
        return f.read()


def _load_index(niche: str) -> list:
    path = _index_path(niche)
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []


def _save_index(niche: str, index: list) -> None:
    with open(_index_path(niche), 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2)
