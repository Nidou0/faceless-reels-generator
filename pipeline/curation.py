"""Curation stage: dedupe, rank, and filter sourced stories into top picks per niche.

Local replacement for the n8n 7pm-trigger curation prompt — same two-stage
idea (broad curation prompt picks winners, separate from per-story script
prompt), running against an LLM instead of a hosted model + Slack review.
"""
import json
import os
import re

from . import sourcing, llm

_CURATED_DIR = os.path.join('data', 'curated')

# Fiction niches: source posts are creative writing, not facts to fact-check.
_NARRATIVE_NICHES = {'scary-stories', 'scp-stories', 'mythology'}

_NICHE_DESC = {
    'trending-news': 'breaking tech and AI news',
    'scary-stories': 'true-to-life horror and creepy real-experience stories',
    'scp-stories':   'SCP Foundation anomaly reports and creative fiction',
    'mythology':     'mythology, folklore, and legends',
    'true-crime':    'true crime cases and unsolved mysteries',
    'life-advice':   'practical life advice and self-improvement tips',
    'science-facts': 'science discoveries and facts',
    'history-facts': 'history facts and stories',
}

_SYSTEM_TEMPLATE = (
    "You are a senior content curator for a viral short-form video channel focused on "
    "{niche_desc}. You receive a batch of recent posts/articles wrapped in <story> XML tags. "
    "Your job: "
    "1. Merge/dedupe stories covering the same underlying premise or event. "
    "2. Hard-filter OUT: spam, low-effort posts, and anything without real substance. "
    "3. Rank each surviving story into exactly one bucket: Impactful, Practical, "
    "Provocative, or Astonishing. "
    "4. For each kept story, write a 1-2 sentence summary and 2-3 short hook_angles "
    "(different ways to open a video about it). "
    "{anti_hallucination_rule} "
    "OUTPUT: strict JSON only, no markdown fences, no commentary, matching this schema:\n"
    '{{"picks": [{{"title": "...", "summary": "...", "bucket": "Impactful", '
    '"hook_angles": ["...", "..."], "source_url": "...", "source_name": "..."}}]}}'
)

_FACTUAL_RULE = (
    "CRITICAL ANTI-HALLUCINATION RULE: 'source_url' must be copy-pasted EXACTLY from the "
    "<story url=\"...\"> attribute you were given. Never invent, modify, or guess a URL."
)
_NARRATIVE_RULE = (
    "These are creative-fiction source posts. 'source_url' must still be copy-pasted "
    "EXACTLY from the <story url=\"...\"> attribute — never invent a URL."
)


def curate(niche: str, log, max_stories: int = 30) -> list:
    entries = sourcing.recent(niche)[:max_stories]
    if not entries:
        return []

    log(f'  -> Curating {len(entries)} sourced stories for {niche}...', 'script')

    blocks = []
    for e in entries:
        md = sourcing.load_markdown(niche, e)[:1500]
        blocks.append(
            f'<story source="{_esc(e["source"])}" url="{_esc(e["url"])}" title="{_esc(e["title"])}">\n'
            f'{md}\n</story>'
        )
    bundle = '\n\n'.join(blocks)
    prompt = f'Curate the following stories:\n\n{bundle}'

    system = _SYSTEM_TEMPLATE.format(
        niche_desc=_NICHE_DESC.get(niche, niche.replace('-', ' ')),
        anti_hallucination_rule=_NARRATIVE_RULE if niche in _NARRATIVE_NICHES else _FACTUAL_RULE,
    )

    try:
        raw = llm.complete(system, prompt, max_tokens=4000, temperature=0.3, log=log)
    except Exception as exc:
        raise RuntimeError(f'Curation request failed: {exc}')

    picks = _parse_json(raw).get('picks', [])

    # Anti-hallucination guard: drop any pick whose URL wasn't actually in the source set
    valid_urls = {e['url'] for e in entries}
    picks = [p for p in picks if p.get('source_url') in valid_urls]

    log(f'  -> {len(picks)} stories survived curation', 'script')

    os.makedirs(_CURATED_DIR, exist_ok=True)
    with open(_curated_path(niche), 'w', encoding='utf-8') as f:
        json.dump(picks, f, indent=2)

    return picks


def load_latest(niche: str) -> list:
    path = _curated_path(niche)
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []


def _curated_path(niche: str) -> str:
    return os.path.join(_CURATED_DIR, f'{niche}.json')


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'```\s*$', '', raw)
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return {}


def _esc(s: str) -> str:
    return (s or '').replace('"', "'").replace('<', '').replace('>', '')
