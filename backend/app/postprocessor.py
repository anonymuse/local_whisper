import anthropic

from .config import settings

_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

_SYSTEM_PROMPT = """\
You are a transcript editor. Clean the following speech transcript.

Rules:
- Fix punctuation and capitalization
- Remove filler words (um, uh, like, you know, so, right)
- Correct misheard proper nouns, names, and technical terms based on context
- Add paragraph breaks at natural topic shifts
- Lightly improve clarity and flow while preserving the speaker's exact voice and intent
- Do NOT over-edit or add information that wasn't said
- Do NOT use AI-sounding phrases (e.g. "certainly", "absolutely", "it's worth noting", "in conclusion")
- Return only the cleaned transcript — no commentary, no labels"""


async def clean_transcript(raw_text: str) -> str:
    message = await _client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": _SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": raw_text}],
    )
    return message.content[0].text
