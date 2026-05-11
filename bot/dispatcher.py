import json
import re
from datetime import datetime, timedelta
from llm.client import chat
from handlers import todo, reminder, memory


INTENT_SYSTEM = """You are an intent classifier for a personal secretary bot. Classify the user's message into one of these intents and extract parameters.

Intents:
- add_todo: user wants to add a task
- list_todos: user wants to see their task list
- complete_todo: user wants to mark a task done (extract id if mentioned)
- delete_todo: user wants to delete a task (extract id)
- add_reminder: user wants a reminder (extract text and datetime)
- list_reminders: user wants to see pending reminders
- store_memory: user wants to store a behavioral rule (starts with "remember that")
- list_memories: user wants to see stored memories
- delete_memory: user wants to delete a memory (extract id)
- get_news: user wants tech news now
- general: general question or conversation

Return JSON only:
{"intent": "<intent>", "params": {<relevant params>}}

For add_reminder, params must include "text" and "remind_at" as ISO datetime string.
Current datetime: {now}"""


async def parse_intent(message: str) -> dict:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    system = INTENT_SYSTEM.format(now=now)

    response = await chat(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": message},
        ]
    )

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", response, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"intent": "general", "params": {}}


async def dispatch(message: str, send_news_fn=None) -> str:
    matched_memories = memory.match_memories(message)
    if matched_memories:
        mem = matched_memories[0]
        action = mem["action_type"]
        params = mem["action_params"]

        if action == "set_reminder":
            time_match = re.search(r"(\d{1,2})(?::(\d{2}))?", message)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2) or 0)
                offset = params.get("offset_minutes", 0)
                remind_dt = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
                remind_dt += timedelta(minutes=offset)
                label = params.get("label", message)
                result = reminder.add_reminder(label, remind_dt)
                return f"Reminder set: '{result['text']}' at {remind_dt.strftime('%H:%M')} (from memory rule)"

        elif action == "add_todo":
            prefix = params.get("prefix", "")
            result = todo.add_todo(f"{prefix}{message}")
            return f"Added to todos: '{result['text']}'"

    parsed = await parse_intent(message)
    intent = parsed.get("intent", "general")
    params = parsed.get("params", {})

    if intent == "add_todo":
        text = params.get("text", message)
        result = todo.add_todo(text)
        return f"Added: '{result['text']}'"

    elif intent == "list_todos":
        todos = todo.list_todos()
        return todo.format_todo_list(todos)

    elif intent == "complete_todo":
        todo_id = params.get("id")
        if todo_id:
            success = todo.complete_todo(int(todo_id))
            return f"Marked done." if success else f"No task with id {todo_id}."
        todos = todo.list_todos()
        return "Which task? Here's your list:\n" + todo.format_todo_list(todos)

    elif intent == "delete_todo":
        todo_id = params.get("id")
        if todo_id:
            success = todo.delete_todo(int(todo_id))
            return f"Deleted." if success else f"No task with id {todo_id}."
        return "Which task id should I delete?"

    elif intent == "add_reminder":
        text = params.get("text", message)
        remind_at_str = params.get("remind_at")
        if remind_at_str:
            try:
                remind_dt = datetime.fromisoformat(remind_at_str)
                result = reminder.add_reminder(text, remind_dt)
                return f"Reminder set: '{result['text']}' at {remind_dt.strftime('%Y-%m-%d %H:%M')}"
            except ValueError:
                return "I couldn't parse that time. Try something like 'remind me at 3pm tomorrow to call John'."
        return "When should I remind you?"

    elif intent == "list_reminders":
        reminders = reminder.list_pending_reminders()
        return reminder.format_reminders(reminders)

    elif intent == "store_memory":
        result = await memory.store_memory(message)
        return f"Got it. Stored rule: trigger on '{result['trigger_pattern']}' → {result['action_type']}"

    elif intent == "list_memories":
        memories = memory.get_all_memories()
        return memory.format_memories(memories)

    elif intent == "delete_memory":
        mem_id = params.get("id")
        if mem_id:
            success = memory.delete_memory(int(mem_id))
            return "Memory deleted." if success else f"No memory with id {mem_id}."
        return "Which memory id should I delete?"

    elif intent == "get_news":
        if send_news_fn:
            return await send_news_fn()
        return "News fetch not available right now."

    else:
        response = await chat(
            messages=[
                {"role": "system", "content": "You are a helpful personal secretary. Be concise and practical."},
                {"role": "user", "content": message},
            ]
        )
        return response
