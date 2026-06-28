import os
import re

from . import llm

_REFERENCE_DIR = os.path.join('data', 'reference_scripts')

# Narrative niches build dread toward an unresolved cliffhanger.
# Everything else delivers information fast with a CTA.
_NARRATIVE_NICHES = {'scary-stories', 'scp-stories', 'mythology', 'true-crime'}

_POWER_UPS = [
    "Authority bump — cite the source institution/company by name for credibility",
    "Stat escalation — open with a smaller number, build up to a bigger, more shocking one",
    "Zoom-out line — end with a broader implication beyond just this story",
    "Direct address — speak straight to the viewer ('you need to know this')",
    "Contrarian framing — 'everyone thinks X, but actually...'",
]

_NEWS_SYSTEM = (
    "You are a viral scriptwriter for a fast-paced Shorts channel. {persona}"
    "You write tight, punchy 50-60 second scripts that hook viewers instantly and "
    "deliver real information fast."
)

_SUSPENSE_SYSTEM = (
    "You are an elite scriptwriter for viral TikTok/Instagram/YouTube Shorts. {persona}"
    "Your scripts stop scrollers in the first 3 seconds and keep them hooked until the end. "
    "RULES: "
    "1. Open with a powerful hook — first 8 words must create immediate curiosity or shock. "
    "2. Use short punchy sentences — never more than 15 words each. "
    "3. Build tension progressively, reveal information in layers. "
    "4. Never describe visuals, screens, or camera direction (no 'the screen fades', "
    "no 'picture this') — only words a narrator would actually speak. "
    "5. NEVER resolve the story. End mid-tension on an unresolved cliffhanger — a sudden "
    "interruption, an unanswered question, or a final detail that implies something worse "
    "is still happening. "
    "OUTPUT: No titles, no stage directions, no brackets, no markdown, no section labels. "
    "This text is read by TTS directly."
)

_NICHE_GUIDANCE = {
    'scp-stories': (
        "Write in SCP Foundation style: a secretive organization documenting and containing "
        "anomalous entities/objects/phenomena. Invent a specific designation number, e.g. "
        "'SCP-3008' or 'SCP-241' — never use XXXX or a placeholder. Reference an object "
        "classification (Safe, Euclid, or Keter), hint at containment procedures or Foundation "
        "personnel/researchers, and describe the anomaly's unsettling behavior. Blend a "
        "clinical, documented tone with genuine dread."
    ),
}


def generate_from_story(story: dict, niche: str, config: dict, log) -> str:
    """Single script-generation entry point for every niche.

    Hook-brainstorm-then-filter: silently generate 5 candidate hooks, pick the
    best 2, only fully write scripts for those 2 winners. Works identically
    whether the story came from sourced/curated RSS or a user-typed topic.
    """
    persona      = config.get('persona', '').strip()
    persona_line = f'Persona: {persona}. ' if persona else ''
    narrative    = niche in _NARRATIVE_NICHES

    references = _load_references(niche)
    ref_block  = ''
    if references:
        examples = '\n\n---\n\n'.join(references[:3])
        ref_block = (
            f'\nHere are past scripts that performed well — match this style, pacing, '
            f'and structure closely:\n\n{examples}\n\n---\n'
        )

    guidance      = _NICHE_GUIDANCE.get(niche, '')
    guidance_line = f'{guidance}\n' if guidance else ''

    if narrative:
        system         = _SUSPENSE_SYSTEM.format(persona=persona_line)
        structure_line = (
            "an opening hook, rising tension, a climax, then cut off before resolving — "
            "an unresolved cliffhanger."
        )
        extra = ''
        anti_hallucination = (
            "You may creatively adapt and condense this premise in your own words, but "
            "keep its core twist or scare intact.\n\n"
        )
    else:
        system         = _NEWS_SYSTEM.format(persona=persona_line)
        structure_line = (
            "hook -> one-line explainer -> 5 to 7 rapid facts -> why it matters or the "
            "risk -> a single call to action."
        )
        powerups = '\n'.join(f'- {p}' for p in _POWER_UPS)
        extra = f"Optionally sprinkle in 1-2 of these devices (not all, don't force it):\n{powerups}\n\n"
        anti_hallucination = (
            "Anti-hallucination rule: only state facts present in the summary/source above. "
            "Do not invent statistics, quotes, or details not given to you.\n\n"
        )

    prompt = (
        f"Story title: {story.get('title', '')}\n"
        f"Summary: {story.get('summary', '')}\n"
        f"Suggested hook angles: {', '.join(story.get('hook_angles', []))}\n"
        f"Source: {story.get('source_name', '')}\n"
        f"{guidance_line}"
        f"{ref_block}\n"
        f"STEP 1: Silently brainstorm 5 different hook openings for this story.\n"
        f"STEP 2: Silently evaluate all 5 and pick the best 2.\n"
        f"STEP 3: Write 2 full scripts, one for each of your top 2 hooks, best first.\n\n"
        f"Each script MUST follow this structure: {structure_line}\n"
        f"Each script: 140-160 words, natural spoken pacing for 50-60 seconds.\n"
        f"{extra}"
        f"{anti_hallucination}"
        f"Do not include a title, do not label any section, do not write section names — "
        f"each script must read as one continuous spoken narration with no headers.\n\n"
        f"Output ONLY strict JSON, no markdown fences, no commentary, schema:\n"
        f'{{"scripts": [{{"hook": "...", "script": "..."}}, {{"hook": "...", "script": "..."}}]}}'
    )

    log(f'  ->{llm.current_model()} | niche: {niche} | mode: {"suspense" if narrative else "news"}', 'script')
    log('  -> Brainstorming 5 hooks, writing top 2 scripts...', 'script')

    try:
        text = llm.complete(system, prompt, max_tokens=1500, temperature=0.8)
    except Exception as exc:
        raise RuntimeError(f'Script generation failed: {exc}')

    data    = _parse_json_block(text)
    scripts = data.get('scripts', [])
    if not scripts:
        raise RuntimeError('LLM returned no usable scripts — try again')

    log(f'  -> {len(scripts)} candidate script(s) written, using top pick', 'script')
    for i, s in enumerate(scripts):
        log(f'  -> Candidate {i + 1} hook: "{s.get("hook", "")[:60]}"', 'script')

    return _clean(scripts[0].get('script', ''))


def _parse_json_block(raw: str) -> dict:
    import json
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


def _load_references(niche: str) -> list:
    niche_specific = _read_txts(os.path.join(_REFERENCE_DIR, niche))
    if niche_specific:
        return niche_specific
    return _read_txts(_REFERENCE_DIR)


def _read_txts(d: str) -> list:
    if not os.path.exists(d):
        return []
    out = []
    for fname in sorted(os.listdir(d)):
        path = os.path.join(d, fname)
        if fname.endswith('.txt') and os.path.isfile(path):
            with open(path, encoding='utf-8') as f:
                out.append(f.read().strip())
    return out


_LABEL_RE = re.compile(
    r'^\s*(script|voiceover|narration|hook|build[ -]?up|build tension|tension|'
    r'rising tension|climax|closure|conclusion|cliffhanger|ending)\s*:\s*',
    re.IGNORECASE,
)


def _clean(text: str) -> str:
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\[.*?\]', '', text)

    lines = [_LABEL_RE.sub('', ln) for ln in text.strip().splitlines()]
    # Drop a leading title line: short, no terminal punctuation, blank line right after.
    if len(lines) >= 2 and lines[0].strip() and not lines[1].strip():
        first = lines[0].strip()
        if not re.search(r'[.!?]\s*$', first) and len(first.split()) <= 12:
            lines = lines[2:]

    text = '\n'.join(lines)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()
