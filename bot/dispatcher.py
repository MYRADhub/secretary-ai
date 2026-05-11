import json
import re
from collections import deque
from datetime import datetime, timedelta
from llm.client import chat
from handlers import todo, reminder, memory

HISTORY_MAX = 20

_history: deque = deque(maxlen=HISTORY_MAX)

INTENT_SYSTEM = """You are an intent classifier for a personal secretary bot. Classify the user's message and extract clean parameters.

Intents:
- add_todo: adding a task. Extract ONLY the task itself, strip phrases like "add", "put", "remind me to", "to my list", etc.
  e.g. "add buy milk to my list" → text: "buy milk"
  e.g. "I need to call the dentist" → text: "call the dentist"
- list_todos: user wants to see their task list
- complete_todo: mark a task done. Extract id if mentioned, else null.
- complete_all_todos: mark ALL tasks done
- delete_todo: delete a specific task. Extract id.
- clear_all_todos: delete ALL pending tasks (triggered by "clear all", "delete everything", "wipe my list", etc.)
- add_reminder: set a reminder. Extract "text" (what to remind) and "remind_at" as ISO datetime string.
- list_reminders: list pending reminders
- store_memory: store a behavioral rule. Triggered by "remember that..."
- list_memories: list stored memories
- delete_memory: delete a memory by id
- get_news: user wants tech news
- general: anything else, conversation, questions

Return JSON only: {"intent": "<intent>", "params": {}}

For add_reminder params must include "text" and "remind_at" as ISO datetime.
Current datetime: """


async def parse_intent(message: str) -> dict:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    system = INTENT_SYSTEM + now

    messages = [{"role": "system", "content": system}]
    messages += list(_history)
    messages.append({"role": "user", "content": message})

    response = await chat(messages=messages)

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
            return f"Added: '{result['text']}'"

    parsed = await parse_intent(message)
    intent = parsed.get("intent", "general")
    params = parsed.get("params", {})

    if intent == "add_todo":
        text = params.get("text", message)
        result = todo.add_todo(text)
        reply = f"Added: '{result['text']}'"

    elif intent == "list_todos":
        todos = todo.list_todos()
        reply = todo.format_todo_list(todos)

    elif intent == "complete_todo":
        todo_id = params.get("id")
        if todo_id:
            success = todo.complete_todo(int(todo_id))
            reply = "Done." if success else f"No task with id {todo_id}."
        else:
            todos = todo.list_todos()
            reply = "Which task?\n" + todo.format_todo_list(todos)

    elif intent == "complete_all_todos":
        count = todo.complete_all_todos()
        reply = f"Marked {count} task(s) as done."

    elif intent == "delete_todo":
        todo_id = params.get("id")
        if todo_id:
            success = todo.delete_todo(int(todo_id))
            reply = "Deleted." if success else f"No task with id {todo_id}."
        else:
            todos = todo.list_todos()
            reply = "Which task?\n" + todo.format_todo_list(todos)

    elif intent == "clear_all_todos":
        count = todo.clear_all_todos()
        reply = f"Cleared {count} task(s)."

    elif intent == "add_reminder":
        text = params.get("text", message)
        remind_at_str = params.get("remind_at")
        if remind_at_str:
            try:
                remind_dt = datetime.fromisoformat(remind_at_str)
                result = reminder.add_reminder(text, remind_dt)
                reply = f"Reminder set: '{result['text']}' at {remind_dt.strftime('%Y-%m-%d %H:%M')}"
            except ValueError:
                reply = "Couldn't parse that time. Try 'remind me at 3pm tomorrow to call John'."
        else:
            reply = "When should I remind you?"

    elif intent == "list_reminders":
        reminders = reminder.list_pending_reminders()
        reply = reminder.format_reminders(reminders)

    elif intent == "store_memory":
        result = await memory.store_memory(message)
        reply = f"Stored: trigger on '{result['trigger_pattern']}' → {result['action_type']}"

    elif intent == "list_memories":
        memories = memory.get_all_memories()
        reply = memory.format_memories(memories)

    elif intent == "delete_memory":
        mem_id = params.get("id")
        if mem_id:
            success = memory.delete_memory(int(mem_id))
            reply = "Deleted." if success else f"No memory with id {mem_id}."
        else:
            reply = "Which memory id?"

    elif intent == "get_news":
        reply = await send_news_fn() if send_news_fn else "News unavailable."

    else:
        system = "You are a helpful personal secretary. Be concise and direct."
        messages = [{"role": "system", "content": system}]
        messages += list(_history)
        messages.append({"role": "user", "content": message})
        reply = await chat(messages=messages)

    _history.append({"role": "user", "content": message})
    _history.append({"role": "assistant", "content": reply})

    return reply
