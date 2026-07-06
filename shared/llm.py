"""
Life OS · shared/llm.py
The single wrapper around LLM provider SDKs. Modules import from here,
never from the SDKs directly (see CLAUDE.md architecture rules).

Today: Anthropic only, including classification (Claude Haiku) — see
PLAN.md Phase 4 for why this deviates from the original
GPT-4o-mini/Gemini classification plan.
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


def generate_json(prompt: str, model: str, schema: dict, max_tokens: int = 300) -> dict:
    """
    Structured extraction: forces the model to call a synthetic tool whose
    input matches `schema`, so the result is reliably-shaped JSON instead of
    free text we'd have to hope parses correctly.
    """
    response = _client().messages.create(
        model=model,
        max_tokens=max_tokens,
        tools=[{
            "name": "extract",
            "description": "Return the extracted data.",
            "input_schema": schema,
        }],
        tool_choice={"type": "tool", "name": "extract"},
        messages=[{"role": "user", "content": prompt}],
    )
    for block in response.content:
        if block.type == "tool_use":
            return block.input
    raise RuntimeError("Model did not return a tool_use block")
