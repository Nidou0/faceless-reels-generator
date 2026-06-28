"""Thin LLM provider abstraction — swap between Claude and Gemini via .env LLM_PROVIDER.

Lets script_gen.py and curation.py call one complete() function without caring
which backend is funded/active at any given time.
"""
from config import (
    LLM_PROVIDER, ANTHROPIC_API_KEY, CLAUDE_MODEL, GEMINI_API_KEY, GEMINI_MODEL,
)

_claude_client = None
_gemini_client = None


def current_model() -> str:
    return GEMINI_MODEL if LLM_PROVIDER == 'gemini' else CLAUDE_MODEL


def complete(system: str, prompt: str, max_tokens: int = 1200, temperature: float = 0.8) -> str:
    if LLM_PROVIDER == 'gemini':
        return _gemini_complete(system, prompt, max_tokens, temperature)
    return _claude_complete(system, prompt, max_tokens, temperature)


def _claude_complete(system: str, prompt: str, max_tokens: int, temperature: float) -> str:
    global _claude_client
    if not ANTHROPIC_API_KEY:
        raise RuntimeError('ANTHROPIC_API_KEY not set — add it to .env')
    if _claude_client is None:
        import anthropic
        _claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    resp = _claude_client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        messages=[{'role': 'user', 'content': prompt}],
    )
    return ''.join(b.text for b in resp.content if b.type == 'text')


def _gemini_complete(system: str, prompt: str, max_tokens: int, temperature: float) -> str:
    global _gemini_client
    if not GEMINI_API_KEY:
        raise RuntimeError('GEMINI_API_KEY not set — add it to .env')
    if _gemini_client is None:
        from google import genai
        _gemini_client = genai.Client(api_key=GEMINI_API_KEY)

    from google.genai import types
    resp = _gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens,
            temperature=temperature,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    return resp.text or ''
