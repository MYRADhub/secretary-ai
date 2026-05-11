from openai import AsyncOpenAI
import config

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    return _client


_NO_TEMPERATURE_MODELS = {"gpt-5-mini", "gpt-5-nano", "o1", "o1-mini", "o3", "o3-mini"}


async def chat(messages: list[dict], model: str | None = None, temperature: float = 0.3) -> str:
    client = get_client()
    resolved_model = model or config.OPENAI_MODEL
    kwargs = {"model": resolved_model, "messages": messages}
    if resolved_model not in _NO_TEMPERATURE_MODELS:
        kwargs["temperature"] = temperature
    response = await client.chat.completions.create(**kwargs)
    return response.choices[0].message.content.strip()


async def transcribe(file_path: str) -> str:
    client = get_client()
    with open(file_path, "rb") as f:
        response = await client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
        )
    return response.text.strip()
