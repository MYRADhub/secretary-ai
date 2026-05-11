from openai import AsyncOpenAI
import config

_client: AsyncOpenAI | None = None

def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    return _client

async def chat(messages: list[dict], model: str | None = None, temperature: float = 0.3) -> str:
    client = get_client()
    response = await client.chat.completions.create(
        model=model or config.OPENAI_MODEL,
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()
