"""
Life OS · shared/llm.py
The single wrapper around LLM provider SDKs. Modules import from here,
never from the SDKs directly (see CLAUDE.md architecture rules).

Today: Anthropic only. Cheap classification models (OpenAI/Gemini) get
added here when the orchestrator is built.
"""

from anthropic import Anthropic

_anthropic_client = None


def _client() -> Anthropic:
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    return _anthropic_client


def generate(prompt: str, model: str, max_tokens: int = 3000) -> str:
    """One-shot text generation with Claude. Returns the response text."""
    response = _client().messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text")
