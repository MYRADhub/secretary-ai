from openai import AsyncOpenAI
import config

# Gemini client via OpenAI-compatible endpoint
_gemini_client: AsyncOpenAI | None = None

# OpenAI client — used only for Whisper transcription
_openai_client: AsyncOpenAI | None = None


def get_gemini_client() -> AsyncOpenAI:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = AsyncOpenAI(
            api_key=config.GEMINI_API_KEY,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
    return _gemini_client


def get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    return _openai_client


async def chat(messages: list[dict], model: str | None = None, temperature: float = 0.3) -> str:
    client = get_gemini_client()
    response = await client.chat.completions.create(
        model=model or config.GEMINI_MODEL,
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()


async def transcribe(file_path: str) -> str:
    client = get_openai_client()
    with open(file_path, "rb") as f:
        response = await client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
        )
    return response.text.strip()
