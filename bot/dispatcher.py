import json
from collections import deque
from datetime import datetime
from zoneinfo import ZoneInfo

from llm.client import chat_with_tools
from handlers import memory
from bot.tools import get_tool_specs, call_tool

TZ = ZoneInfo("America/New_York")
HISTORY_MAX = 100
_history: deque = deque(maxlen=HISTORY_MAX)

MAX_TOOL_ITERATIONS = 6

SYSTEM_TEMPLATE = """You are a personal secretary bot. The user talks to you on Telegram in natural language.

You have tools to manage todos, reminders, calendar events, behavioral memory rules, news, web search, and a financial curriculum.

Rules:
- Use tools whenever the user wants to do or look up something concrete. Chain multiple tool calls in one turn when the request requires it (e.g. "delete tasks 2 and 5 and add buy milk").
- For pure conversation, advice, or explanation, just reply in text without calling a tool.
- Strip command verbs from task text before calling add_todo (e.g. "add buy milk" -> text "buy milk").
- When the user gives a vague time like "3pm tomorrow", convert it to an ISO datetime in America/New_York.
- After your tool calls complete, give a short final reply summarizing what happened. Keep it concise.
- If a tool returns an error, tell the user briefly and suggest the next step.

{memory_hint}
Current datetime: {now}"""


def _build_memory_hint(message: str, matched: list[dict]) -> str:
    if not matched:
        return ""
    m = matched[0]
    return (
        f"Memory rule matched for this message: trigger '{m['trigger_pattern']}', "
        f"action_type '{m['action_type']}', params {json.dumps(m['action_params'])}. "
        f"Apply this rule via the appropriate tool call.\n"
    )


def _message_to_dict(msg) -> dict:
    """Convert OpenAI ChatCompletionMessage to a plain dict for history/messages."""
    out: dict = {"role": "assistant", "content": msg.content or ""}
    if getattr(msg, "tool_calls", None):
        out["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in msg.tool_calls
        ]
    return out


async def dispatch(message: str, reply_context: str | None = None) -> str:
    matched_memories = await memory.match_memories(message)
    now = datetime.now(TZ).strftime("%Y-%m-%d %H:%M %Z")
    system = SYSTEM_TEMPLATE.format(
        memory_hint=_build_memory_hint(message, matched_memories),
        now=now,
    )

    messages: list[dict] = [{"role": "system", "content": system}]
    messages += list(_history)[-10:]
    if reply_context:
        messages.append({"role": "assistant", "content": reply_context})
    messages.append({"role": "user", "content": message})

    tools = get_tool_specs()

    final_text = ""
    for _ in range(MAX_TOOL_ITERATIONS):
        msg = await chat_with_tools(messages=messages, tools=tools)
        messages.append(_message_to_dict(msg))

        tool_calls = getattr(msg, "tool_calls", None)
        if not tool_calls:
            final_text = (msg.content or "").strip()
            break

        for tc in tool_calls:
            result = await call_tool(tc.function.name, tc.function.arguments)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })
    else:
        final_text = "Hit tool-iteration cap. Try simplifying the request."

    if not final_text:
        # Fall back to last tool result if model returned empty content.
        for m in reversed(messages):
            if m.get("role") == "tool" and m.get("content"):
                final_text = m["content"]
                break
        if not final_text:
            final_text = "Done."

    _history.append({"role": "user", "content": message})
    _history.append({"role": "assistant", "content": final_text})
    return final_text
