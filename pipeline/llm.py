"""Multi-provider LLM abstraction with automatic fallback.

Tries providers in priority order — Claude (best quality, paid) -> Groq
(free, generous daily limits, solid quality) -> Gemini (free, but a tiny
20-requests/day cap) — falling through on any failure so one provider's
outage or rate/quota limit doesn't block generation.
"""
from config import (
    ANTHROPIC_API_KEY, CLAUDE_MODEL,
    GROQ_API_KEY, GROQ_MODEL,
    GEMINI_API_KEY, GEMINI_MODEL,
)

_PROVIDERS = ['claude', 'groq', 'gemini']

_claude_client = None
_groq_client   = None
_gemini_client = None


def complete(system: str, prompt: str, max_tokens: int = 1200, temperature: float = 0.8, log=None) -> str:
    errors = []
    for provider in _PROVIDERS:
        try:
            text = _dispatch(provider, system, prompt, max_tokens, temperature)
            if log:
                log(f'  -> LLM: {provider}', 'script')
            return text
        except Exception as exc:
            errors.append(f'{provider}: {exc}')
            if log:
                log(f'  -> {provider} unavailable ({str(exc)[:80]}), trying next...', 'script')

    raise RuntimeError('All LLM providers failed:\n' + '\n'.join(errors))


def _dispatch(provider: str, system: str, prompt: str, max_tokens: int, temperature: float) -> str:
    if provider == 'claude':
        return _claude_complete(system, prompt, max_tokens, temperature)
    if provider == 'groq':
        return _groq_complete(system, prompt, max_tokens, temperature)
    if provider == 'gemini':
        return _gemini_complete(system, prompt, max_tokens, temperature)
    raise ValueError(f'Unknown provider: {provider}')


def _claude_complete(system: str, prompt: str, max_tokens: int, temperature: float) -> str:
    global _claude_client
    if not ANTHROPIC_API_KEY:
        raise RuntimeError('ANTHROPIC_API_KEY not set')
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


def _groq_complete(system: str, prompt: str, max_tokens: int, temperature: float) -> str:
    global _groq_client
    if not GROQ_API_KEY:
        raise RuntimeError('GROQ_API_KEY not set')
    if _groq_client is None:
        from groq import Groq
        _groq_client = Groq(api_key=GROQ_API_KEY)

    resp = _groq_client.chat.completions.create(
        model=GROQ_MODEL,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': prompt},
        ],
    )
    return resp.choices[0].message.content or ''


def _gemini_complete(system: str, prompt: str, max_tokens: int, temperature: float) -> str:
    global _gemini_client
    if not GEMINI_API_KEY:
        raise RuntimeError('GEMINI_API_KEY not set')
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
        ),
    )
    return resp.text or ''
